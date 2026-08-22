from __future__ import annotations

import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from proofbid.agent_pipeline import run_agentic_pipeline
from proofbid.pipeline import PipelineError
from proofbid.planning import (
    EXECUTION_PLAN_NAME,
    PROVIDER_RECEIPT_NAME,
    TASK_SPEC_NAME,
    ExecutionPlan,
    PlanStep,
    PlanningError,
    PlanningResult,
    ProviderReceipt,
    REQUIRED_TOOL_DEPENDENCIES,
)


FIXTURE = Path(__file__).parents[1] / "examples" / "synthetic_tender"


def _plan(task_spec) -> ExecutionPlan:
    step_id_by_tool = {
        tool: tool.value.removeprefix("proofbid.") for tool in task_spec.allowed_tools
    }
    return ExecutionPlan(
        task_spec_digest=task_spec.digest,
        steps=tuple(
            PlanStep(
                step_id=step_id_by_tool[tool],
                tool=tool,
                depends_on=tuple(
                    step_id_by_tool[dependency]
                    for dependency in REQUIRED_TOOL_DEPENDENCIES[tool]
                ),
                completion_criterion=f"{tool.value} returns a typed result.",
            )
            for tool in task_spec.allowed_tools
        ),
        summary="Synthetic test plan for the bounded deterministic pipeline.",
    )


class _StaticPlanner:
    def __init__(self) -> None:
        self.calls = 0

    def create_plan(self, task_spec) -> PlanningResult:
        self.calls += 1
        plan = _plan(task_spec)
        receipt = ProviderReceipt(
            provider="test.static",
            configured_model="test-model",
            model_version="test-model-v1",
            auth_mode="test",
            adk_version="2.7.1-test",
            genai_version="2.18.1-test",
            started_at=datetime.now(UTC).isoformat(),
            duration_ms=1.25,
            event_count=1,
            invocation_id="inv-test",
            interaction_id=None,
            finish_reason="STOP",
            prompt_tokens=10,
            output_tokens=20,
            total_tokens=30,
            request_digest="a" * 64,
            response_digest="b" * 64,
            plan_digest=plan.digest,
            schema_validated=True,
            policy_validated=True,
        )
        return PlanningResult(plan=plan, receipt=receipt)


class _FailingPlanner:
    def create_plan(self, task_spec):
        raise PlanningError("synthetic planner failure")


class _DriftingPlanner(_StaticPlanner):
    def __init__(self, workspace: Path) -> None:
        super().__init__()
        self.workspace = workspace

    def create_plan(self, task_spec) -> PlanningResult:
        result = super().create_plan(task_spec)
        tender = self.workspace / "tender.md"
        tender.write_text(tender.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        return result


def test_agentic_pipeline_packages_plan_receipt_and_redacted_trace(tmp_path: Path) -> None:
    output = tmp_path / "delivery"
    summary = run_agentic_pipeline(FIXTURE, output, planner=_StaticPlanner())

    assert summary["status"] == "completed_with_blockers"
    planning = summary["planning"]
    assert planning["provider"] == "test.static"
    assert planning["configured_model"] == "test-model"
    assert planning["model_version"] == "test-model-v1"
    assert planning["policy_validated"] is True
    assert len(planning["plan_digest"]) == 64
    for name in (TASK_SPEC_NAME, EXECUTION_PLAN_NAME, PROVIDER_RECEIPT_NAME):
        assert (output / name).is_file()

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    declared = {item["path"] for item in manifest["files"]}
    assert {TASK_SPEC_NAME, EXECUTION_PLAN_NAME, PROVIDER_RECEIPT_NAME} <= declared
    with zipfile.ZipFile(output / "proofbid_bundle.zip") as archive:
        assert {TASK_SPEC_NAME, EXECUTION_PLAN_NAME, PROVIDER_RECEIPT_NAME} <= set(
            archive.namelist()
        )

    trace_text = (output / "trace.jsonl").read_text(encoding="utf-8")
    events = [json.loads(line) for line in trace_text.splitlines()]
    assert {event["status"] for event in events if event["step"] == "planning"} == {
        "started",
        "completed",
    }
    assert "GEMINI_API_KEY" not in trace_text
    planning_details = next(
        event
        for event in events
        if event["step"] == "planning" and event["status"] == "completed"
    )["details"]
    assert "tender.md" not in json.dumps(planning_details)


def test_planner_failure_has_no_pipeline_side_effect(tmp_path: Path) -> None:
    output = tmp_path / "delivery"

    with pytest.raises(PlanningError, match="synthetic planner failure"):
        run_agentic_pipeline(FIXTURE, output, planner=_FailingPlanner())

    assert not output.exists()


def test_nonempty_output_is_rejected_before_planner_call(tmp_path: Path) -> None:
    output = tmp_path / "delivery"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("user-owned", encoding="utf-8")
    planner = _StaticPlanner()

    with pytest.raises(PipelineError, match="new or empty"):
        run_agentic_pipeline(FIXTURE, output, planner=planner)

    assert planner.calls == 0
    assert sentinel.read_text(encoding="utf-8") == "user-owned"


def test_invalid_output_parent_is_rejected_before_planner_call(tmp_path: Path) -> None:
    parent_file = tmp_path / "not-a-directory"
    parent_file.write_text("user-owned", encoding="utf-8")
    planner = _StaticPlanner()

    with pytest.raises(PipelineError, match="not writable"):
        run_agentic_pipeline(FIXTURE, parent_file / "delivery", planner=planner)

    assert planner.calls == 0
    assert parent_file.read_text(encoding="utf-8") == "user-owned"


def test_input_drift_after_planning_is_blocked(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(FIXTURE, workspace)
    output = tmp_path / "delivery"

    with pytest.raises(PipelineError, match="Inputs changed after the plan was approved"):
        run_agentic_pipeline(workspace, output, planner=_DriftingPlanner(workspace))

    assert not output.exists()
