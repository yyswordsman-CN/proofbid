from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from proofbid import scan_workspace
from proofbid.planning import (
    ExecutionPlan,
    PlanStep,
    PlanTool,
    PlanValidationError,
    REQUIRED_TOOL_DEPENDENCIES,
    TaskInputRef,
    build_task_spec,
    validate_execution_plan,
)


FIXTURE = Path(__file__).parents[1] / "examples" / "synthetic_tender"


def _task_spec():
    documents = scan_workspace(
        FIXTURE,
        ("tender.md", "bidder_profile.json", "catalog.csv"),
    )
    return build_task_spec("task-planning-test", documents)


def _valid_plan(task_spec) -> ExecutionPlan:
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
                completion_criterion=f"{tool.value} completes with typed output.",
            )
            for tool in task_spec.allowed_tools
        ),
        summary="Run the complete bounded ProofBid DAG and preserve all unknowns.",
    )


def test_task_spec_is_manifest_only_and_digest_is_stable() -> None:
    task_spec = _task_spec()
    duplicate = _task_spec()

    assert task_spec.digest == duplicate.digest
    payload = task_spec.to_dict()
    assert [item["relative_path"] for item in payload["inputs"]] == sorted(
        item["relative_path"] for item in payload["inputs"]
    )
    assert all("content" not in item and "excerpt" not in item for item in payload["inputs"])
    assert len(task_spec.allowed_tools) == 8


def test_complete_topological_plan_passes_policy() -> None:
    task_spec = _task_spec()
    plan = _valid_plan(task_spec)

    validate_execution_plan(plan, task_spec)
    assert len(plan.digest) == 64


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    (
        (
            lambda plan: replace(plan, task_spec_digest="0" * 64),
            "TASK_SPEC_DIGEST_MISMATCH",
        ),
        (
            lambda plan: replace(plan, steps=plan.steps[:-1]),
            "PLAN_TOOL_SET_MISMATCH",
        ),
        (
            lambda plan: replace(
                plan,
                steps=(replace(plan.steps[1], depends_on=()),) + plan.steps[1:],
            ),
            "PLAN_TOOLS_NOT_UNIQUE",
        ),
        (
            lambda plan: replace(
                plan,
                steps=(
                    plan.steps[0],
                    replace(plan.steps[1], depends_on=(plan.steps[-1].step_id,)),
                    *plan.steps[2:],
                ),
            ),
            "PLAN_NOT_TOPOLOGICAL",
        ),
        (
            lambda plan: replace(
                plan,
                steps=(plan.steps[0], plan.steps[2], plan.steps[1], *plan.steps[3:]),
            ),
            "PLAN_TOOL_ORDER_MISMATCH",
        ),
    ),
)
def test_plan_policy_rejects_invalid_graphs(mutation, expected_code: str) -> None:
    task_spec = _task_spec()
    plan = mutation(_valid_plan(task_spec))

    with pytest.raises(PlanValidationError) as caught:
        validate_execution_plan(plan, task_spec)

    assert expected_code in caught.value.reason_codes


def test_contracts_reject_unknown_tool_and_unsafe_input_path() -> None:
    with pytest.raises(ValueError, match="safe relative path"):
        TaskInputRef(
            relative_path="../secret.txt",
            document_type="text",
            source_hash="a" * 64,
            size_bytes=10,
        )
    with pytest.raises(ValueError, match="PlanStep.tool"):
        PlanStep(
            step_id="shell",
            tool="shell.exec",  # type: ignore[arg-type]
            depends_on=(),
            completion_criterion="Run arbitrary shell.",
        )


def test_task_digest_changes_when_input_hash_changes() -> None:
    task_spec = _task_spec()
    changed_input = replace(task_spec.inputs[0], source_hash="f" * 64)
    changed = replace(task_spec, inputs=(changed_input, *task_spec.inputs[1:]))

    assert changed.digest != task_spec.digest
