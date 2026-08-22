from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from proofbid.agent_runtime_v2 import (
    RuntimeTool,
    TaskRuntime,
    ToolPolicyError,
    _local_planning_result,
    run_scripted_agent_pipeline,
)
from proofbid.intake import scan_workspace
from proofbid.pipeline import REQUIRED_INPUTS, new_task_id
from proofbid.planning import build_task_spec


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPLETE = PROJECT_ROOT / "examples" / "complete_tender"
BLOCKED = PROJECT_ROOT / "examples" / "blocked_missing_authorization"


def _runtime(tmp_path: Path) -> TaskRuntime:
    workspace = tmp_path / "workspace"
    shutil.copytree(COMPLETE, workspace)
    task_spec = build_task_spec(new_task_id(), scan_workspace(workspace, REQUIRED_INPUTS))
    return TaskRuntime(
        workspace=workspace,
        output_dir=tmp_path / "delivery",
        task_spec=task_spec,
        planning_result=_local_planning_result(task_spec),
    )


def _declare(runtime: TaskRuntime) -> None:
    runtime.invoke(
        RuntimeTool.DECLARE_PLAN,
        selected_tools=[
            tool.value for tool in RuntimeTool if tool is not RuntimeTool.DECLARE_PLAN
        ],
        parser_strategy="typed_manifest",
        failure_policy="bounded_retry_then_block",
    )


def test_agent_v2_green_route_finishes_with_locked_high_risk_actions(
    tmp_path: Path,
) -> None:
    output = tmp_path / "green"
    result = run_scripted_agent_pipeline(COMPLETE, output)

    assert result["status"] == "completed"
    assert result["ready_for_human_review"] is True
    assert result["ready_for_submission"] is True
    assert result["submission_executed"] is False
    assert result["high_risk_actions_locked"] is True
    assert result["render_attempts"] == 1
    assert result["artifact_integrity_passed"] is True

    agent_run = json.loads((output / "agent_run.json").read_text(encoding="utf-8"))
    assert agent_run["schema_version"] == "proofbid.agent-run/v2"
    assert agent_run["status"] == "completed"
    assert agent_run["readiness"]["ready_for_submission"] is True


def test_agent_v2_blocked_route_delivers_missing_item_package(tmp_path: Path) -> None:
    output = tmp_path / "blocked"
    result = run_scripted_agent_pipeline(BLOCKED, output)

    assert result["status"] == "blocked"
    assert result["ready_for_human_review"] is False
    assert result["ready_for_submission"] is False
    assert result["blocking_reason_codes"]
    assert result["artifact_integrity_passed"] is True


def test_agent_v2_uses_one_bounded_renderer_recovery(tmp_path: Path) -> None:
    output = tmp_path / "recovery"
    result = run_scripted_agent_pipeline(
        COMPLETE,
        output,
        inject_render_failure=True,
    )

    assert result["status"] == "completed"
    assert result["render_attempts"] == 2
    receipts = [
        json.loads(line)
        for line in (output / "tool_receipts.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    failed_render = next(row for row in receipts if row["tool"] == "render_delivery")
    retry = next(row for row in receipts if row["tool"] == "retry_render")
    assert failed_render["status"] == "recoverable_error"
    assert failed_render["reason_code"] == "RENDER_TRANSIENT"
    assert retry["status"] == "completed"
    assert retry["retry_of"] == failed_render["sequence"]


def test_runtime_tool_enum_rejects_unknown_tool() -> None:
    with pytest.raises(ValueError):
        RuntimeTool("shell")


def test_tool_policy_error_is_fail_closed() -> None:
    assert ToolPolicyError.reason_code == "AGENT_TOOL_POLICY_REJECTED"


def test_agent_v2_rejects_undeclared_out_of_order_and_duplicate_calls(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    with pytest.raises(ToolPolicyError, match="declare_execution_plan"):
        runtime.invoke(RuntimeTool.SCAN_INPUTS)

    _declare(runtime)
    with pytest.raises(ToolPolicyError, match="Dependencies"):
        runtime.invoke(RuntimeTool.EXTRACT_REQUIREMENTS)

    runtime.invoke(RuntimeTool.SCAN_INPUTS)
    with pytest.raises(ToolPolicyError, match="cannot be completed twice"):
        runtime.invoke(RuntimeTool.SCAN_INPUTS)


def test_agent_v2_rejects_input_drift_before_extraction(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    tender = runtime.workspace / "tender.md"
    tender.write_text(tender.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
    _declare(runtime)

    with pytest.raises(ToolPolicyError, match="TASK_INPUT_DRIFT"):
        runtime.invoke(RuntimeTool.SCAN_INPUTS)


def test_agent_v2_rejects_wrong_terminal_branch(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _declare(runtime)
    for tool in (
        RuntimeTool.SCAN_INPUTS,
        RuntimeTool.EXTRACT_REQUIREMENTS,
        RuntimeTool.LOAD_BIDDER_EVIDENCE,
        RuntimeTool.LOAD_PRODUCT_CATALOG,
        RuntimeTool.BUILD_ANALYSIS,
        RuntimeTool.VALIDATE_DOMAIN,
        RuntimeTool.RENDER_DELIVERY,
        RuntimeTool.VALIDATE_DELIVERY,
    ):
        runtime.invoke(tool)

    with pytest.raises(ToolPolicyError, match="ready package"):
        runtime.invoke(RuntimeTool.FINALIZE_BLOCKED)
