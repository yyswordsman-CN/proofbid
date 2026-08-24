from __future__ import annotations

import asyncio
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from proofbid.agent_runtime_v2 import (
    RuntimeTool,
    TaskRuntime,
    ToolPolicyError,
    _local_planning_result,
    build_adk_function_tools,
    run_scripted_agent_pipeline,
)
from proofbid.adapters.google.adk_tool_agent import _prompt
from proofbid.intake import scan_workspace
from proofbid.pipeline import REQUIRED_INPUTS, new_task_id
from proofbid.planning import ProviderReceipt, build_task_spec


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


def _real_runtime(tmp_path: Path) -> TaskRuntime:
    workspace = tmp_path / "workspace-real"
    shutil.copytree(COMPLETE, workspace)
    task_spec = build_task_spec(new_task_id(), scan_workspace(workspace, REQUIRED_INPUTS))
    return TaskRuntime(
        workspace=workspace,
        output_dir=tmp_path / "delivery-real",
        task_spec=task_spec,
        planning_result=_local_planning_result(task_spec),
        require_real_provider_evidence=True,
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


def test_real_agent_prompt_serializes_task_inputs_from_task_spec_contract(
    tmp_path: Path,
) -> None:
    runtime = _real_runtime(tmp_path)

    prompt = _prompt(runtime)
    payload = json.loads(prompt.split("\n", 1)[1])

    assert payload["task_spec_digest"] == runtime.task_spec.digest
    assert payload["inputs"] == runtime.task_spec.to_dict()["inputs"]
    assert [item["relative_path"] for item in payload["inputs"]] == [
        "bidder_profile.json",
        "catalog.csv",
        "tender.md",
    ]


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
    assert "PROJECT_AUTHORIZATION_MISSING" in result["blocking_reason_codes"]
    assert not any(
        code.startswith("BLOCKING_MISSING_ITEM:")
        for code in result["blocking_reason_codes"]
    )
    assert result["artifact_integrity_passed"] is True

    analysis = json.loads((output / "result.json").read_text(encoding="utf-8"))["analysis"]
    assert len(analysis["missing_items"]) == 1
    assert analysis["missing_items"][0]["reason_code"] == "PROJECT_AUTHORIZATION_MISSING"


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


def test_adk_wrapper_records_function_call_id(tmp_path: Path) -> None:
    runtime = _real_runtime(tmp_path)
    tool = next(item for item in build_adk_function_tools(runtime) if item.name == "declare_execution_plan")
    context = type("FakeToolContext", (), {"function_call_id": "adk-call-declare"})()
    asyncio.run(
        tool.func(
            selected_tools=[
                item.value for item in RuntimeTool if item is not RuntimeTool.DECLARE_PLAN
            ],
            parser_strategy="typed_manifest",
            failure_policy="bounded_retry_then_block",
            tool_context=context,
        )
    )
    assert runtime.receipts[0].function_call_id == "adk-call-declare"


def test_real_runtime_rejects_tool_call_without_adk_call_id(tmp_path: Path) -> None:
    runtime = _real_runtime(tmp_path)
    with pytest.raises(ToolPolicyError, match="function_call_id"):
        runtime.invoke(
            RuntimeTool.DECLARE_PLAN,
            selected_tools=[
                item.value for item in RuntimeTool if item is not RuntimeTool.DECLARE_PLAN
            ],
            parser_strategy="typed_manifest",
            failure_policy="bounded_retry_then_block",
        )


def test_real_provider_binding_replaces_all_scripted_evidence(tmp_path: Path) -> None:
    runtime = _real_runtime(tmp_path)
    for index, (tool, arguments) in enumerate(
        (
            (RuntimeTool.DECLARE_PLAN, {
                "selected_tools": [
                    item.value for item in RuntimeTool if item is not RuntimeTool.DECLARE_PLAN
                ],
                "parser_strategy": "typed_manifest",
                "failure_policy": "bounded_retry_then_block",
            }),
            (RuntimeTool.SCAN_INPUTS, {}),
            (RuntimeTool.EXTRACT_REQUIREMENTS, {}),
            (RuntimeTool.LOAD_BIDDER_EVIDENCE, {}),
            (RuntimeTool.LOAD_PRODUCT_CATALOG, {}),
            (RuntimeTool.BUILD_ANALYSIS, {}),
            (RuntimeTool.VALIDATE_DOMAIN, {}),
            (RuntimeTool.RENDER_DELIVERY, {}),
            (RuntimeTool.VALIDATE_DELIVERY, {}),
            (RuntimeTool.FINALIZE_COMPLETE, {}),
        ),
        start=1,
    ):
        runtime.invoke(tool, function_call_id=f"adk-call-{index:02d}", **arguments)

    receipt = ProviderReceipt(
        provider="google.gemini",
        configured_model="gemini-3.5-flash",
        model_version="gemini-3.5-flash-202608",
        auth_mode="vertex_ai",
        adk_version="2.7.1",
        genai_version="2.18.1",
        started_at=datetime.now(UTC).isoformat(),
        duration_ms=1234.5,
        event_count=12,
        invocation_id="vertex-invocation-001",
        interaction_id="vertex-interaction-001",
        finish_reason="STOP",
        prompt_tokens=120,
        output_tokens=80,
        total_tokens=200,
        request_digest="a" * 64,
        response_digest="b" * 64,
        plan_digest=runtime.planning_result.plan.digest,
        schema_validated=True,
        policy_validated=True,
    )
    runtime.bind_real_provider_receipt(receipt)
    result = runtime.freeze_delivery()

    assert result["status"] == "completed"
    assert result["provider"]["provider"] == "google.gemini"
    for path in runtime.artifacts.payload_files:
        if path.suffix in {".json", ".jsonl"}:
            assert "scripted-policy" not in path.read_text(encoding="utf-8")
    rows = [
        json.loads(line)
        for line in runtime.tool_receipts_path.read_text(encoding="utf-8").splitlines()
    ]
    assert all(row["function_call_id"] for row in rows)


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
