"""Bounded, tool-calling ProofBid agent runtime.

The model may choose registered tool order, a single bounded recovery branch,
and the correct terminal action. All paths, business facts, rendering, and
readiness decisions remain bound to deterministic server-side state.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from .artifacts import ArtifactSet, render_bundle
from .extraction import ExtractionResult, extract_requirements
from .intake import scan_workspace
from .matching import build_analysis, load_bidder_profile, load_catalog
from .pipeline import (
    REQUIRED_INPUTS,
    _artifact_paths,
    _documents_by_name,
    _prepare_output,
    _write_planning_payloads,
    assert_output_target_available,
    new_task_id,
)
from .planning import (
    CANONICAL_TOOL_ORDER,
    ExecutionPlan,
    PlanStep,
    PlanningResult,
    ProviderReceipt,
    REQUIRED_TOOL_DEPENDENCIES,
    TaskSpec,
    build_task_spec,
)
from .safe_io import secure_staging_path
from .tracing import TraceRecorder
from .validators import (
    ValidationReport,
    build_readiness_decision,
    validate_artifacts,
    validate_bundle,
)


AGENT_RUN_NAME = "agent_run.json"
TOOL_RECEIPTS_NAME = "tool_receipts.jsonl"
AGENT_RUN_SCHEMA_VERSION = "proofbid.agent-run/v2"
TOOL_RECEIPT_SCHEMA_VERSION = "proofbid.tool-receipt/v2"


class RuntimeTool(str, Enum):
    DECLARE_PLAN = "declare_execution_plan"
    SCAN_INPUTS = "scan_inputs"
    EXTRACT_REQUIREMENTS = "extract_requirements"
    LOAD_BIDDER_EVIDENCE = "load_bidder_evidence"
    LOAD_PRODUCT_CATALOG = "load_product_catalog"
    BUILD_ANALYSIS = "build_analysis"
    VALIDATE_DOMAIN = "validate_domain"
    RENDER_DELIVERY = "render_delivery"
    RETRY_RENDER = "retry_render"
    VALIDATE_DELIVERY = "validate_delivery"
    FINALIZE_COMPLETE = "finalize_complete"
    FINALIZE_BLOCKED = "finalize_blocked"


CORE_ROUTE = (
    RuntimeTool.SCAN_INPUTS,
    RuntimeTool.EXTRACT_REQUIREMENTS,
    RuntimeTool.LOAD_BIDDER_EVIDENCE,
    RuntimeTool.LOAD_PRODUCT_CATALOG,
    RuntimeTool.BUILD_ANALYSIS,
    RuntimeTool.VALIDATE_DOMAIN,
    RuntimeTool.RENDER_DELIVERY,
    RuntimeTool.VALIDATE_DELIVERY,
)


class AgentRuntimeError(RuntimeError):
    reason_code = "AGENT_RUNTIME_FAILED"


class ToolPolicyError(AgentRuntimeError):
    reason_code = "AGENT_TOOL_POLICY_REJECTED"


class RecoverableRenderError(AgentRuntimeError):
    reason_code = "RENDER_TRANSIENT"


@dataclass(frozen=True, slots=True)
class ToolCallReceipt:
    sequence: int
    tool: str
    status: str
    reason_code: str
    started_at: str
    duration_ms: float
    input_digest: str
    result_digest: str
    retry_of: int | None = None
    schema_version: str = TOOL_RECEIPT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    with secure_staging_path(path) as staging:
        staging.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    content = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    )
    with secure_staging_path(path) as staging:
        staging.write_text(content, encoding="utf-8")


def _local_planning_result(task_spec: TaskSpec) -> PlanningResult:
    step_ids = {tool: tool.value.removeprefix("proofbid.") for tool in CANONICAL_TOOL_ORDER}
    plan = ExecutionPlan(
        task_spec_digest=task_spec.digest,
        steps=tuple(
            PlanStep(
                step_id=step_ids[tool],
                tool=tool,
                depends_on=tuple(step_ids[item] for item in REQUIRED_TOOL_DEPENDENCIES[tool]),
                completion_criterion=f"{tool.value} returns a typed deterministic result.",
            )
            for tool in CANONICAL_TOOL_ORDER
        ),
        summary="Authorize the bounded ProofBid tool runtime; actual calls are recorded in v2 receipts.",
    )
    now = datetime.now(UTC).isoformat()
    receipt = ProviderReceipt(
        provider="proofbid.scripted-policy",
        configured_model="deterministic-route-policy",
        model_version="deterministic-route-policy/v2",
        auth_mode="test",
        adk_version="local-scripted",
        genai_version="not-used",
        started_at=now,
        duration_ms=0.0,
        event_count=1,
        invocation_id=f"local-{task_spec.task_id}",
        interaction_id=None,
        finish_reason="STOP",
        prompt_tokens=0,
        output_tokens=0,
        total_tokens=0,
        request_digest=_digest(task_spec.to_dict()),
        response_digest=_digest(plan.to_dict()),
        plan_digest=plan.digest,
        schema_validated=True,
        policy_validated=True,
    )
    return PlanningResult(plan=plan, receipt=receipt)


class TaskRuntime:
    """Stateful deterministic executor behind the ADK FunctionTools."""

    def __init__(
        self,
        *,
        workspace: str | Path,
        output_dir: str | Path,
        task_spec: TaskSpec,
        planning_result: PlanningResult,
        inject_render_failure: bool = False,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.output_dir = _prepare_output(output_dir)
        self.task_spec = task_spec
        self.planning_result = planning_result
        self.inject_render_failure = inject_render_failure
        self.trace = TraceRecorder(self.output_dir / "trace.jsonl", task_spec.task_id)
        self.receipts: list[ToolCallReceipt] = []
        self.selected_tools: tuple[RuntimeTool, ...] = ()
        self.parser_strategy: str | None = None
        self.failure_policy: str | None = None
        self.documents = None
        self.by_name = None
        self.extraction: ExtractionResult | None = None
        self.profile = None
        self.catalog = None
        self.bundle = None
        self.domain_report: ValidationReport | None = None
        self.artifacts: ArtifactSet | None = None
        self.delivery_report: ValidationReport | None = None
        self.terminal_status: str | None = None
        self.render_attempts = 0
        self.provider_evidence: dict[str, Any] = {
            "provider": planning_result.receipt.provider,
            "configured_model": planning_result.receipt.configured_model,
            "model_version": planning_result.receipt.model_version,
            "finish_reason": planning_result.receipt.finish_reason,
            "invocation_id": planning_result.receipt.invocation_id,
            "prompt_tokens": planning_result.receipt.prompt_tokens,
            "output_tokens": planning_result.receipt.output_tokens,
            "total_tokens": planning_result.receipt.total_tokens,
        }
        self._planning_payloads = _write_planning_payloads(
            self.output_dir,
            task_spec,
            planning_result,
        )
        self.agent_run_path = self.output_dir / AGENT_RUN_NAME
        self.tool_receipts_path = self.output_dir / TOOL_RECEIPTS_NAME
        self.trace.emit(
            step="planning",
            status="started",
            actor=planning_result.receipt.provider,
            details={
                "task_spec_digest": task_spec.digest,
                "provider_started_at": planning_result.receipt.started_at,
            },
        )
        self.trace.emit(
            step="planning",
            status="completed",
            actor=planning_result.receipt.provider,
            details={
                "configured_model": planning_result.receipt.configured_model,
                "model_version": planning_result.receipt.model_version,
                "auth_mode": planning_result.receipt.auth_mode,
                "adk_version": planning_result.receipt.adk_version,
                "genai_version": planning_result.receipt.genai_version,
                "event_count": planning_result.receipt.event_count,
                "invocation_id": planning_result.receipt.invocation_id,
                "interaction_id": planning_result.receipt.interaction_id,
                "finish_reason": planning_result.receipt.finish_reason,
                "request_digest": planning_result.receipt.request_digest,
                "response_digest": planning_result.receipt.response_digest,
                "plan_digest": planning_result.receipt.plan_digest,
                "schema_validated": planning_result.receipt.schema_validated,
                "policy_validated": planning_result.receipt.policy_validated,
                "prompt_tokens": planning_result.receipt.prompt_tokens,
                "output_tokens": planning_result.receipt.output_tokens,
                "total_tokens": planning_result.receipt.total_tokens,
            },
            duration_ms=planning_result.receipt.duration_ms,
        )
        self._persist_agent_evidence()

    @property
    def supplemental_payloads(self) -> tuple[Path, ...]:
        return (*self._planning_payloads, self.agent_run_path, self.tool_receipts_path)

    def set_provider_evidence(self, evidence: dict[str, Any]) -> None:
        self.provider_evidence = dict(evidence)
        self._persist_agent_evidence()

    def _agent_run_payload(self) -> dict[str, Any]:
        readiness = (
            build_readiness_decision(self.bundle, self.domain_report)
            if self.bundle is not None and self.domain_report is not None
            else None
        )
        receipts_payload = [receipt.to_dict() for receipt in self.receipts]
        return {
            "schema_version": AGENT_RUN_SCHEMA_VERSION,
            "task_id": self.task_spec.task_id,
            "task_spec_digest": self.task_spec.digest,
            "execution_mode": "agentic",
            "status": self.terminal_status or "running",
            "parser_strategy": self.parser_strategy,
            "failure_policy": self.failure_policy,
            "selected_tools": [tool.value for tool in self.selected_tools],
            "tool_call_count": len(self.receipts),
            "tool_receipts_digest": _digest(receipts_payload),
            "provider": self.provider_evidence,
            "readiness": asdict(readiness) if readiness is not None else None,
            "high_risk_actions": {
                "freeze_pricing": "locked",
                "sign_documents": "locked",
                "send_or_submit_bid": "locked",
            },
        }

    def _persist_agent_evidence(self) -> None:
        _write_jsonl(
            self.tool_receipts_path,
            (receipt.to_dict() for receipt in self.receipts),
        )
        _write_json(self.agent_run_path, self._agent_run_payload())

    def _require(self, condition: bool, message: str) -> None:
        if not condition:
            raise ToolPolicyError(message)

    def _dependencies_satisfied(self, tool: RuntimeTool) -> None:
        completed = {
            RuntimeTool(receipt.tool)
            for receipt in self.receipts
            if receipt.status == "completed"
        }
        rules: dict[RuntimeTool, set[RuntimeTool]] = {
            RuntimeTool.SCAN_INPUTS: {RuntimeTool.DECLARE_PLAN},
            RuntimeTool.EXTRACT_REQUIREMENTS: {RuntimeTool.SCAN_INPUTS},
            RuntimeTool.LOAD_BIDDER_EVIDENCE: {RuntimeTool.SCAN_INPUTS},
            RuntimeTool.LOAD_PRODUCT_CATALOG: {RuntimeTool.SCAN_INPUTS},
            RuntimeTool.BUILD_ANALYSIS: {
                RuntimeTool.EXTRACT_REQUIREMENTS,
                RuntimeTool.LOAD_BIDDER_EVIDENCE,
                RuntimeTool.LOAD_PRODUCT_CATALOG,
            },
            RuntimeTool.VALIDATE_DOMAIN: {RuntimeTool.BUILD_ANALYSIS},
            RuntimeTool.RENDER_DELIVERY: {RuntimeTool.VALIDATE_DOMAIN},
            RuntimeTool.RETRY_RENDER: {RuntimeTool.VALIDATE_DOMAIN},
            RuntimeTool.VALIDATE_DELIVERY: {
                RuntimeTool.RENDER_DELIVERY,
            },
            RuntimeTool.FINALIZE_COMPLETE: {RuntimeTool.VALIDATE_DELIVERY},
            RuntimeTool.FINALIZE_BLOCKED: {RuntimeTool.VALIDATE_DELIVERY},
        }
        required = rules.get(tool, set())
        if tool is RuntimeTool.RETRY_RENDER:
            recoverable = any(
                receipt.tool == RuntimeTool.RENDER_DELIVERY.value
                and receipt.status == "recoverable_error"
                for receipt in self.receipts
            )
            self._require(recoverable, "retry_render requires a recoverable render failure")
            return
        if tool is RuntimeTool.VALIDATE_DELIVERY and RuntimeTool.RENDER_DELIVERY not in completed:
            required = {RuntimeTool.RETRY_RENDER}
        self._require(required <= completed, f"Dependencies are not satisfied for {tool.value}")

    def invoke(self, tool: RuntimeTool | str, **arguments: Any) -> dict[str, Any]:
        resolved = RuntimeTool(tool)
        self._require(self.terminal_status is None, "The task is already terminal")
        self._require(len(self.receipts) < 14, "The maximum tool-call budget was exceeded")
        if resolved is not RuntimeTool.DECLARE_PLAN:
            self._require(bool(self.selected_tools), "declare_execution_plan must run first")
            self._require(
                resolved in self.selected_tools,
                f"{resolved.value} was not selected in the declared plan",
            )
            self._dependencies_satisfied(resolved)
        self._require(
            not any(
                receipt.tool == resolved.value and receipt.status == "completed"
                for receipt in self.receipts
            ),
            f"{resolved.value} cannot be completed twice",
        )

        started_at = datetime.now(UTC).isoformat()
        started = time.perf_counter()
        sequence = len(self.receipts) + 1
        retry_of = None
        if resolved is RuntimeTool.RETRY_RENDER:
            retry_of = next(
                receipt.sequence
                for receipt in reversed(self.receipts)
                if receipt.tool == RuntimeTool.RENDER_DELIVERY.value
            )
        input_digest = _digest(
            {
                "task_spec_digest": self.task_spec.digest,
                "tool": resolved.value,
                "arguments": arguments,
                "prior_receipts": [receipt.result_digest for receipt in self.receipts],
            }
        )
        try:
            result = self._execute(resolved, arguments)
            status = "completed"
            reason_code = "OK"
        except RecoverableRenderError as exc:
            result = {"status": "recoverable_error", "reason_code": exc.reason_code}
            status = "recoverable_error"
            reason_code = exc.reason_code
        except Exception as exc:
            result = {
                "status": "failed",
                "reason_code": getattr(exc, "reason_code", "TOOL_EXECUTION_FAILED"),
            }
            receipt = ToolCallReceipt(
                sequence=sequence,
                tool=resolved.value,
                status="failed",
                reason_code=result["reason_code"],
                started_at=started_at,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                input_digest=input_digest,
                result_digest=_digest(result),
                retry_of=retry_of,
            )
            self.receipts.append(receipt)
            self.trace.emit(
                step="agent_tool",
                status="failed",
                actor="proofbid.tool-runtime",
                details={"tool": resolved.value, "reason_code": result["reason_code"]},
                duration_ms=receipt.duration_ms,
            )
            self._persist_agent_evidence()
            raise

        receipt = ToolCallReceipt(
            sequence=sequence,
            tool=resolved.value,
            status=status,
            reason_code=reason_code,
            started_at=started_at,
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
            input_digest=input_digest,
            result_digest=_digest(result),
            retry_of=retry_of,
        )
        self.receipts.append(receipt)
        self.trace.emit(
            step="agent_tool",
            status=status,
            actor="proofbid.tool-runtime",
            details={"tool": resolved.value, "reason_code": reason_code},
            duration_ms=receipt.duration_ms,
        )
        self._persist_agent_evidence()
        if status == "completed" and resolved in {
            RuntimeTool.RENDER_DELIVERY,
            RuntimeTool.RETRY_RENDER,
        }:
            # Bind the render tool receipt and its trace event into the delivery
            # manifest before the independent delivery validator runs.
            self.artifacts = render_bundle(
                output_dir=self.output_dir,
                bundle=self.bundle,
                validations=self.domain_report,
                trace_path=self.trace.path,
                supplemental_payloads=self.supplemental_payloads,
                execution_mode="agentic",
            )
        return result

    def _execute(self, tool: RuntimeTool, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool is RuntimeTool.DECLARE_PLAN:
            raw_tools = arguments.get("selected_tools")
            self._require(isinstance(raw_tools, list), "selected_tools must be an array")
            selected = tuple(RuntimeTool(item) for item in raw_tools)
            self._require(len(selected) == len(set(selected)), "selected_tools must be unique")
            self._require(set(CORE_ROUTE) <= set(selected), "The declared plan omitted a core tool")
            self._require(
                {RuntimeTool.FINALIZE_COMPLETE, RuntimeTool.FINALIZE_BLOCKED} <= set(selected),
                "The declared plan must preserve both deterministic terminal branches",
            )
            parser_strategy = arguments.get("parser_strategy")
            failure_policy = arguments.get("failure_policy")
            self._require(parser_strategy == "typed_manifest", "Unsupported parser strategy")
            self._require(
                failure_policy == "bounded_retry_then_block",
                "Unsupported failure policy",
            )
            self.selected_tools = selected
            self.parser_strategy = parser_strategy
            self.failure_policy = failure_policy
            return {"status": "planned", "selected_tool_count": len(selected)}

        if tool is RuntimeTool.SCAN_INPUTS:
            documents, by_name = _documents_by_name(self.workspace)
            observed = build_task_spec(self.task_spec.task_id, documents)
            self._require(observed.inputs == self.task_spec.inputs, "TASK_INPUT_DRIFT")
            self.documents, self.by_name = documents, by_name
            return {
                "document_count": len(documents),
                "document_types": sorted(document.document_type.value for document in documents),
            }

        self._require(self.by_name is not None, "Inputs have not been scanned")
        if tool is RuntimeTool.EXTRACT_REQUIREMENTS:
            self.extraction = extract_requirements((self.by_name["tender.md"],))
            return {
                "requirement_count": len(self.extraction.requirements),
                "evidence_count": len(self.extraction.evidence),
            }
        if tool is RuntimeTool.LOAD_BIDDER_EVIDENCE:
            self.profile = load_bidder_profile(self.by_name["bidder_profile.json"])
            return {"fact_count": len(self.profile.facts), "evidence_count": len(self.profile.evidence)}
        if tool is RuntimeTool.LOAD_PRODUCT_CATALOG:
            self.catalog = load_catalog(self.by_name["catalog.csv"])
            return {"catalog_item_count": len(self.catalog)}
        if tool is RuntimeTool.BUILD_ANALYSIS:
            self._require(self.extraction is not None, "Requirements are unavailable")
            self._require(self.profile is not None, "Bidder evidence is unavailable")
            self._require(self.catalog is not None, "Catalog is unavailable")
            self.bundle = build_analysis(
                self.task_spec.task_id,
                self.extraction,
                self.profile,
                self.catalog,
            )
            return {
                "match_count": len(self.bundle.matches),
                "bom_line_count": len(self.bundle.bom),
                "missing_item_count": len(self.bundle.missing_items),
            }
        if tool is RuntimeTool.VALIDATE_DOMAIN:
            self._require(self.bundle is not None, "Analysis is unavailable")
            self.domain_report = validate_bundle(self.bundle)
            readiness = build_readiness_decision(self.bundle, self.domain_report)
            return {
                "domain_validation_passed": self.domain_report.passed,
                "ready_for_submission": readiness.ready_for_submission,
                "blocking_reason_codes": list(readiness.blocking_reason_codes),
            }
        if tool in {RuntimeTool.RENDER_DELIVERY, RuntimeTool.RETRY_RENDER}:
            self._require(self.bundle is not None and self.domain_report is not None, "Domain state is unavailable")
            self.render_attempts += 1
            if (
                tool is RuntimeTool.RENDER_DELIVERY
                and self.inject_render_failure
                and self.render_attempts == 1
            ):
                raise RecoverableRenderError("Injected transient renderer failure")
            self._persist_agent_evidence()
            self.artifacts = render_bundle(
                output_dir=self.output_dir,
                bundle=self.bundle,
                validations=self.domain_report,
                trace_path=self.trace.path,
                supplemental_payloads=self.supplemental_payloads,
                execution_mode="agentic",
            )
            return {"artifact_count": len(self.artifacts.payload_files), "render_attempt": self.render_attempts}
        if tool is RuntimeTool.VALIDATE_DELIVERY:
            self._require(self.artifacts is not None and self.bundle is not None, "Artifacts are unavailable")
            self.delivery_report = validate_artifacts(
                self.bundle,
                self.artifacts,
                require_planning=True,
            )
            fatal = [
                finding.code
                for finding in self.delivery_report.failures
                if finding.severity.casefold() in {"error", "critical", "blocker"}
                and finding.code != "MANDATORY_REQUIREMENT_RESOLVED"
            ]
            self._require(not fatal, "Delivery integrity validation failed: " + ", ".join(fatal[:8]))
            return {"artifact_integrity_passed": True, "finding_count": len(self.delivery_report.findings)}
        if tool in {RuntimeTool.FINALIZE_COMPLETE, RuntimeTool.FINALIZE_BLOCKED}:
            self._require(self.bundle is not None and self.domain_report is not None, "Readiness is unavailable")
            self._require(self.delivery_report is not None, "Delivery was not validated")
            readiness = build_readiness_decision(self.bundle, self.domain_report)
            if tool is RuntimeTool.FINALIZE_COMPLETE:
                self._require(readiness.ready_for_submission, "A blocked package cannot finalize complete")
                self.terminal_status = "completed"
            else:
                self._require(not readiness.ready_for_submission, "A ready package cannot finalize blocked")
                self.terminal_status = "blocked"
            return {"status": self.terminal_status, "readiness": asdict(readiness)}
        raise ToolPolicyError(f"Unhandled runtime tool: {tool.value}")

    def freeze_delivery(self) -> dict[str, Any]:
        self._require(self.terminal_status in {"completed", "blocked"}, "Task has no valid terminal state")
        self._persist_agent_evidence()
        self.artifacts = render_bundle(
            output_dir=self.output_dir,
            bundle=self.bundle,
            validations=self.domain_report,
            trace_path=self.trace.path,
            supplemental_payloads=self.supplemental_payloads,
            execution_mode="agentic",
        )
        final_report = validate_artifacts(self.bundle, self.artifacts, require_planning=True)
        fatal = [
            finding.code
            for finding in final_report.failures
            if finding.severity.casefold() in {"error", "critical", "blocker"}
            and finding.code != "MANDATORY_REQUIREMENT_RESOLVED"
        ]
        self._require(not fatal, "Final delivery validation failed: " + ", ".join(fatal[:8]))
        readiness = build_readiness_decision(self.bundle, self.domain_report)
        subtotal = sum(
            (line.qty or 0.0) * (line.unit_price or 0.0)
            for line in self.bundle.bom
            if line.item_id is not None
        )
        return {
            "task_id": self.task_spec.task_id,
            "status": self.terminal_status,
            "execution_mode": "agentic",
            **asdict(readiness),
            "requirement_count": len(self.bundle.requirements),
            "evidence_count": len(self.bundle.evidence),
            "bom_line_count": len(self.bundle.bom),
            "catalog_subtotal": subtotal,
            "missing_item_count": len(self.bundle.missing_items),
            "artifact_integrity_passed": True,
            "render_attempts": self.render_attempts,
            "tool_call_count": len(self.receipts),
            "artifacts": _artifact_paths(self.artifacts),
            "provider": self.provider_evidence,
        }


def _declared_tools() -> list[str]:
    return [tool.value for tool in RuntimeTool if tool is not RuntimeTool.DECLARE_PLAN]


def run_scripted_agent_pipeline(
    workspace: str | Path,
    output_dir: str | Path,
    *,
    inject_render_failure: bool = False,
) -> dict[str, Any]:
    """Run the same bounded tool runtime with a deterministic local route policy."""

    assert_output_target_available(output_dir)
    task_id = new_task_id()
    documents = scan_workspace(Path(workspace), REQUIRED_INPUTS)
    task_spec = build_task_spec(task_id, documents)
    planning_result = _local_planning_result(task_spec)
    runtime = TaskRuntime(
        workspace=workspace,
        output_dir=output_dir,
        task_spec=task_spec,
        planning_result=planning_result,
        inject_render_failure=inject_render_failure,
    )
    runtime.invoke(
        RuntimeTool.DECLARE_PLAN,
        selected_tools=_declared_tools(),
        parser_strategy="typed_manifest",
        failure_policy="bounded_retry_then_block",
    )
    runtime.invoke(RuntimeTool.SCAN_INPUTS)
    runtime.invoke(RuntimeTool.EXTRACT_REQUIREMENTS)
    runtime.invoke(RuntimeTool.LOAD_BIDDER_EVIDENCE)
    runtime.invoke(RuntimeTool.LOAD_PRODUCT_CATALOG)
    runtime.invoke(RuntimeTool.BUILD_ANALYSIS)
    domain = runtime.invoke(RuntimeTool.VALIDATE_DOMAIN)
    rendered = runtime.invoke(RuntimeTool.RENDER_DELIVERY)
    if rendered.get("status") == "recoverable_error":
        runtime.invoke(RuntimeTool.RETRY_RENDER)
    runtime.invoke(RuntimeTool.VALIDATE_DELIVERY)
    runtime.invoke(
        RuntimeTool.FINALIZE_COMPLETE
        if domain["ready_for_submission"]
        else RuntimeTool.FINALIZE_BLOCKED
    )
    return runtime.freeze_delivery()


def build_adk_function_tools(runtime: TaskRuntime) -> list[Any]:
    """Create the real ADK FunctionTools bound to one server-side task runtime."""

    try:
        from google.adk.tools import FunctionTool
    except ImportError as exc:
        raise AgentRuntimeError("Install the ProofBid google extra for ADK tools") from exc

    async def declare_execution_plan(
        selected_tools: list[str],
        parser_strategy: str,
        failure_policy: str,
        tool_context=None,
    ) -> dict[str, Any]:
        """Declare the bounded tools, typed parser strategy, and failure policy for this task."""

        return runtime.invoke(
            RuntimeTool.DECLARE_PLAN,
            selected_tools=selected_tools,
            parser_strategy=parser_strategy,
            failure_policy=failure_policy,
        )

    async def scan_inputs(tool_context=None) -> dict[str, Any]:
        """Scan the pre-bound task workspace and verify its immutable manifest."""

        return runtime.invoke(RuntimeTool.SCAN_INPUTS)

    async def extract_requirements(tool_context=None) -> dict[str, Any]:
        """Extract evidence-bound tender requirements with the declared typed parser."""

        return runtime.invoke(RuntimeTool.EXTRACT_REQUIREMENTS)

    async def load_bidder_evidence(tool_context=None) -> dict[str, Any]:
        """Load the pre-bound bidder evidence without accepting paths or facts from the model."""

        return runtime.invoke(RuntimeTool.LOAD_BIDDER_EVIDENCE)

    async def load_product_catalog(tool_context=None) -> dict[str, Any]:
        """Load the pre-bound product catalog without accepting model-selected paths."""

        return runtime.invoke(RuntimeTool.LOAD_PRODUCT_CATALOG)

    async def build_analysis(tool_context=None) -> dict[str, Any]:
        """Build matches, BOM, deviations, and missing items deterministically."""

        return runtime.invoke(RuntimeTool.BUILD_ANALYSIS)

    async def validate_domain(tool_context=None) -> dict[str, Any]:
        """Run deterministic evidence and business-readiness gates."""

        return runtime.invoke(RuntimeTool.VALIDATE_DOMAIN)

    async def render_delivery(tool_context=None) -> dict[str, Any]:
        """Render the controlled Word, Excel, JSON, Trace, manifest, and ZIP delivery."""

        return runtime.invoke(RuntimeTool.RENDER_DELIVERY)

    async def retry_render(tool_context=None) -> dict[str, Any]:
        """Retry rendering once, only after a recoverable renderer failure receipt."""

        return runtime.invoke(RuntimeTool.RETRY_RENDER)

    async def validate_delivery(tool_context=None) -> dict[str, Any]:
        """Validate cross-artifact content, hashes, archive membership, and planning evidence."""

        return runtime.invoke(RuntimeTool.VALIDATE_DELIVERY)

    async def finalize_complete(tool_context=None) -> dict[str, Any]:
        """Finish only when deterministic readiness and artifact gates both pass."""

        return runtime.invoke(RuntimeTool.FINALIZE_COMPLETE)

    async def finalize_blocked(tool_context=None) -> dict[str, Any]:
        """Finish with a reviewable missing-item package when business evidence is incomplete."""

        return runtime.invoke(RuntimeTool.FINALIZE_BLOCKED)

    return [
        FunctionTool(function)
        for function in (
            declare_execution_plan,
            scan_inputs,
            extract_requirements,
            load_bidder_evidence,
            load_product_catalog,
            build_analysis,
            validate_domain,
            render_delivery,
            retry_render,
            validate_delivery,
            finalize_complete,
            finalize_blocked,
        )
    ]


__all__ = [
    "AGENT_RUN_NAME",
    "TOOL_RECEIPTS_NAME",
    "AgentRuntimeError",
    "RuntimeTool",
    "TaskRuntime",
    "ToolCallReceipt",
    "ToolPolicyError",
    "build_adk_function_tools",
    "run_scripted_agent_pipeline",
]
