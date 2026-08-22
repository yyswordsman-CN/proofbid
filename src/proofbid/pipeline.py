"""Fixed, local orchestration for the first ProofBid vertical slice.

This module intentionally contains no network, model, signing, submission, or
deployment capability.  It coordinates typed, deterministic tools and refuses
to mix a new run with an existing output directory.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from .artifacts import ArtifactSet, render_bundle
from .contracts import DocumentType
from .extraction import extract_requirements
from .intake import scan_workspace
from .matching import build_analysis, load_bidder_profile, load_catalog
from .planning import (
    EXECUTION_PLAN_NAME,
    PROVIDER_RECEIPT_NAME,
    TASK_SPEC_NAME,
    PlanningResult,
    PlanValidationError,
    TaskSpec,
    assert_task_inputs_unchanged,
    validate_execution_plan,
)
from .safe_io import secure_staging_path
from .tracing import TraceRecorder
from .validators import (
    ValidationReport,
    build_readiness_decision,
    validate_artifacts,
    validate_bundle,
)


REQUIRED_INPUTS: dict[str, DocumentType] = {
    "tender.md": DocumentType.MARKDOWN,
    "bidder_profile.json": DocumentType.JSON,
    "catalog.csv": DocumentType.CSV,
}

_BLOCKING_SEVERITIES = {"error", "critical", "blocker"}
# An unresolved mandatory requirement is a truthful business blocker, not an
# execution failure, when it is also represented by a blocking MissingItem.
_EXPECTED_BUSINESS_BLOCKERS = {"MANDATORY_REQUIREMENT_RESOLVED"}


class PipelineError(RuntimeError):
    """Raised when the local run cannot produce a structurally valid bundle."""


def assert_output_target_available(output_dir: str | Path) -> Path:
    """Validate an output target without creating or changing it."""

    destination = Path(output_dir).expanduser().resolve()
    if destination.exists():
        if not destination.is_dir():
            raise PipelineError(f"Output path is not a directory: {destination}")
        if any(destination.iterdir()):
            raise PipelineError(
                f"Output directory must be new or empty; refusing to mix runs: {destination}"
            )
        writable_parent = destination
    else:
        writable_parent = destination.parent
        while not writable_parent.exists() and writable_parent != writable_parent.parent:
            writable_parent = writable_parent.parent
    if not writable_parent.is_dir() or not os.access(
        writable_parent,
        os.W_OK | os.X_OK,
    ):
        raise PipelineError(f"Output target is not writable: {destination}")
    return destination


def _prepare_output(output_dir: str | Path) -> Path:
    destination = assert_output_target_available(output_dir)
    if not destination.exists():
        destination.mkdir(parents=True, exist_ok=False)
    return destination


def new_task_id() -> str:
    return f"task-{uuid.uuid4().hex[:20]}"


def _documents_by_name(workspace: Path):
    documents = scan_workspace(workspace, REQUIRED_INPUTS)
    by_name = {document.relative_path: document for document in documents}
    missing = sorted(set(REQUIRED_INPUTS) - set(by_name))
    if missing:
        raise PipelineError(f"Required input files are missing: {', '.join(missing)}")
    mismatched = [
        name
        for name, expected_type in REQUIRED_INPUTS.items()
        if by_name[name].document_type is not expected_type
    ]
    if mismatched:
        raise PipelineError(f"Required inputs have unexpected types: {', '.join(mismatched)}")
    return documents, by_name


def _blocking_failures(
    report: ValidationReport,
    *,
    allow_business_blockers: bool,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for finding in report.failures:
        if finding.severity.casefold() not in _BLOCKING_SEVERITIES:
            continue
        if allow_business_blockers and finding.code in _EXPECTED_BUSINESS_BLOCKERS:
            continue
        failures.append(finding.to_dict())
    return failures


def _artifact_paths(artifacts: ArtifactSet) -> dict[str, Any]:
    return {
        "requirements_json": str(artifacts.requirements_json),
        "evidence_json": str(artifacts.evidence_json),
        "result_json": str(artifacts.result_json),
        "workbook": str(artifacts.workbook),
        "report": str(artifacts.report),
        "trace": str(artifacts.trace) if artifacts.trace else None,
        "manifest": str(artifacts.manifest),
        "archive": str(artifacts.archive),
        "supplemental_payloads": [
            str(path) for path in artifacts.supplemental_payloads
        ],
        "execution_mode": artifacts.execution_mode,
    }


def _write_json(path: Path, payload: Any) -> None:
    with secure_staging_path(path) as staging:
        staging.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )


def _write_planning_payloads(
    destination: Path,
    task_spec: TaskSpec | None,
    planning_result: PlanningResult | None,
) -> tuple[Path, ...]:
    if task_spec is None and planning_result is None:
        return ()
    if task_spec is None or planning_result is None:
        raise PipelineError("TaskSpec and PlanningResult must be supplied together")
    validate_execution_plan(planning_result.plan, task_spec)
    if task_spec.task_id.strip() == "":
        raise PipelineError("Planned task id must not be empty")

    task_spec_path = destination / TASK_SPEC_NAME
    plan_path = destination / EXECUTION_PLAN_NAME
    receipt_path = destination / PROVIDER_RECEIPT_NAME
    _write_json(task_spec_path, task_spec.to_dict())
    _write_json(plan_path, planning_result.plan.to_dict())
    _write_json(receipt_path, planning_result.receipt.to_dict())
    return (task_spec_path, plan_path, receipt_path)


def _render_with_frozen_trace(
    *,
    output_dir: Path,
    bundle: Any,
    domain_report: ValidationReport,
    trace: TraceRecorder,
    supplemental_payloads: tuple[Path, ...] = (),
) -> tuple[ArtifactSet, ValidationReport]:
    """Render, record validation, then freeze the final trace into the package.

    Recording a post-render event changes ``trace.jsonl`` and therefore its
    manifest hash.  We deliberately re-render after the trace is complete and
    run one final read-only validation so the delivered manifest and ZIP cover
    the exact trace bytes on disk.
    """

    execution_mode = "agentic" if supplemental_payloads else "deterministic"
    with trace.stage("render") as stage:
        artifacts = render_bundle(
            output_dir=output_dir,
            bundle=bundle,
            validations=domain_report,
            trace_path=trace.path,
            supplemental_payloads=supplemental_payloads,
            execution_mode=execution_mode,
        )
        stage.complete(artifact_count=len(tuple(output_dir.iterdir())))

    # Refresh the package after the render completion event changed trace.jsonl.
    artifacts = render_bundle(
        output_dir=output_dir,
        bundle=bundle,
        validations=domain_report,
        trace_path=trace.path,
        supplemental_payloads=supplemental_payloads,
        execution_mode=execution_mode,
    )

    with trace.stage("artifact_validation") as stage:
        # The stage-start event changed the trace bytes.  Refresh before the
        # actual check so this validation covers the package it claims to
        # inspect, rather than reporting a self-induced hash mismatch.
        artifacts = render_bundle(
            output_dir=output_dir,
            bundle=bundle,
            validations=domain_report,
            trace_path=trace.path,
            supplemental_payloads=supplemental_payloads,
            execution_mode=execution_mode,
        )
        preview_report = validate_artifacts(
            bundle,
            artifacts,
            require_planning=execution_mode == "agentic",
        )
        preview_fatal = _blocking_failures(
            preview_report,
            allow_business_blockers=True,
        )
        stage.complete(
            artifact_integrity_passed=not preview_fatal,
            delivery_report_passed=preview_report.passed,
            finding_count=len(preview_report.findings),
            fatal_count=len(preview_fatal),
        )

    # Freeze the completed validation event into the final delivery, then run a
    # read-only validation.  Nothing may append to the packaged trace afterward.
    artifacts = render_bundle(
        output_dir=output_dir,
        bundle=bundle,
        validations=domain_report,
        trace_path=trace.path,
        supplemental_payloads=supplemental_payloads,
        execution_mode=execution_mode,
    )
    final_report = validate_artifacts(
        bundle,
        artifacts,
        require_planning=execution_mode == "agentic",
    )
    return artifacts, final_report


def run_pipeline(
    workspace: str | Path,
    output_dir: str | Path,
    *,
    task_id: str | None = None,
    task_spec: TaskSpec | None = None,
    planning_result: PlanningResult | None = None,
) -> dict[str, Any]:
    """Run the deterministic synthetic ProofBid workflow.

    Exit success means the preparation artifacts are structurally valid.  It
    does *not* mean the bid is ready to submit: unresolved mandatory facts are
    returned explicitly as ``completed_with_blockers``.
    """

    if (task_spec is None) != (planning_result is None):
        raise PipelineError("TaskSpec and PlanningResult must be supplied together")
    resolved_task_id = task_id or new_task_id()
    if task_spec is not None and task_spec.task_id != resolved_task_id:
        raise PipelineError("TaskSpec task id does not match the pipeline task id")
    planned_intake = None
    if task_spec is not None and planning_result is not None:
        validate_execution_plan(planning_result.plan, task_spec)
        documents, by_name = _documents_by_name(Path(workspace))
        try:
            assert_task_inputs_unchanged(task_spec, documents)
        except PlanValidationError as exc:
            raise PipelineError("Inputs changed after the plan was approved") from exc
        planned_intake = (documents, by_name)

    destination = _prepare_output(output_dir)
    supplemental_payloads = _write_planning_payloads(
        destination,
        task_spec,
        planning_result,
    )
    trace = TraceRecorder(destination / "trace.jsonl", resolved_task_id)

    try:
        if planning_result is not None and task_spec is not None:
            receipt = planning_result.receipt
            trace.emit(
                step="planning",
                status="started",
                actor=receipt.provider,
                details={
                    "task_spec_digest": task_spec.digest,
                    "provider_started_at": receipt.started_at,
                },
            )
            trace.emit(
                step="planning",
                status="completed",
                actor=receipt.provider,
                details={
                    "configured_model": receipt.configured_model,
                    "model_version": receipt.model_version,
                    "auth_mode": receipt.auth_mode,
                    "adk_version": receipt.adk_version,
                    "genai_version": receipt.genai_version,
                    "event_count": receipt.event_count,
                    "invocation_id": receipt.invocation_id,
                    "interaction_id": receipt.interaction_id,
                    "finish_reason": receipt.finish_reason,
                    "request_digest": receipt.request_digest,
                    "response_digest": receipt.response_digest,
                    "plan_digest": receipt.plan_digest,
                    "schema_validated": receipt.schema_validated,
                    "policy_validated": receipt.policy_validated,
                    "prompt_tokens": receipt.prompt_tokens,
                    "output_tokens": receipt.output_tokens,
                    "total_tokens": receipt.total_tokens,
                },
                duration_ms=receipt.duration_ms,
            )

        with trace.stage("intake") as stage:
            if planned_intake is None:
                documents, by_name = _documents_by_name(Path(workspace))
            else:
                documents, by_name = planned_intake
            stage.complete(
                document_count=len(documents),
                source_hashes={doc.relative_path: doc.source_hash for doc in documents},
            )

        with trace.stage("extraction") as stage:
            extraction = extract_requirements((by_name["tender.md"],))
            stage.complete(
                requirement_count=len(extraction.requirements),
                evidence_count=len(extraction.evidence),
            )

        with trace.stage("matching") as stage:
            profile = load_bidder_profile(by_name["bidder_profile.json"])
            catalog = load_catalog(by_name["catalog.csv"])
            bundle = build_analysis(resolved_task_id, extraction, profile, catalog)
            subtotal = sum(
                (line.qty or 0.0) * (line.unit_price or 0.0)
                for line in bundle.bom
                if line.item_id is not None
            )
            stage.complete(
                match_count=len(bundle.matches),
                bom_line_count=len(bundle.bom),
                missing_item_count=len(bundle.missing_items),
                catalog_subtotal=subtotal,
            )

        with trace.stage("domain_validation") as stage:
            domain_report = validate_bundle(bundle)
            fatal_domain = _blocking_failures(
                domain_report,
                allow_business_blockers=True,
            )
            stage.complete(
                integrity_passed=not fatal_domain,
                domain_report_passed=domain_report.passed,
                ready_for_submission=domain_report.passed,
                finding_count=len(domain_report.findings),
                fatal_count=len(fatal_domain),
            )
        if fatal_domain:
            codes = ", ".join(item["code"] for item in fatal_domain[:8])
            raise PipelineError(f"Domain integrity validation failed: {codes}")

        artifacts, artifact_report = _render_with_frozen_trace(
            output_dir=destination,
            bundle=bundle,
            domain_report=domain_report,
            trace=trace,
            supplemental_payloads=supplemental_payloads,
        )
        fatal_artifacts = _blocking_failures(
            artifact_report,
            allow_business_blockers=True,
        )
        if fatal_artifacts:
            codes = ", ".join(item["code"] for item in fatal_artifacts[:8])
            raise PipelineError(f"Artifact validation failed: {codes}")

        blockers = [
            item
            for item in bundle.missing_items
            if item.blocks_completion
        ]
        readiness = build_readiness_decision(bundle, domain_report)
        subtotal = sum(
            (line.qty or 0.0) * (line.unit_price or 0.0)
            for line in bundle.bom
            if line.item_id is not None
        )
        return {
            "task_id": resolved_task_id,
            "status": "completed_with_blockers" if blockers else "completed",
            "ready_for_human_review": readiness.ready_for_human_review,
            "ready_for_submission": readiness.ready_for_submission,
            "submission_executed": readiness.submission_executed,
            "high_risk_actions_locked": readiness.high_risk_actions_locked,
            "blocking_reason_codes": list(readiness.blocking_reason_codes),
            "requirement_count": len(bundle.requirements),
            "evidence_count": len(bundle.evidence),
            "bom_line_count": len(bundle.bom),
            "catalog_subtotal": subtotal,
            "missing_item_count": len(bundle.missing_items),
            "blocking_missing_item_count": len(blockers),
            "domain_validation_passed": domain_report.passed,
            "artifact_integrity_passed": True,
            "artifacts": _artifact_paths(artifacts),
            "planning": (
                {
                    "provider": planning_result.receipt.provider,
                    "configured_model": planning_result.receipt.configured_model,
                    "model_version": planning_result.receipt.model_version,
                    "plan_digest": planning_result.plan.digest,
                    "policy_validated": planning_result.receipt.policy_validated,
                }
                if planning_result is not None
                else None
            ),
        }
    except Exception:
        # Stages record their own failures.  Do not append after the final
        # package has been frozen; successful runs return before this handler.
        raise


__all__ = [
    "PipelineError",
    "REQUIRED_INPUTS",
    "assert_output_target_available",
    "new_task_id",
    "run_pipeline",
]
