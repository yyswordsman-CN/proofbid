from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest


jsonschema = pytest.importorskip("jsonschema")

from proofbid import scan_workspace  # noqa: E402
from proofbid.planning import (  # noqa: E402
    ExecutionPlan,
    PlanStep,
    PlanningResult,
    ProviderReceipt,
    REQUIRED_TOOL_DEPENDENCIES,
    build_task_spec,
)


PROJECT_ROOT = Path(__file__).parents[1]
FIXTURE = PROJECT_ROOT / "examples" / "synthetic_tender"


def _load_schema(name: str) -> dict:
    return json.loads((PROJECT_ROOT / "contracts" / name).read_text(encoding="utf-8"))


def test_planning_contracts_match_versioned_json_schemas() -> None:
    documents = scan_workspace(
        FIXTURE,
        ("tender.md", "bidder_profile.json", "catalog.csv"),
    )
    task_spec = build_task_spec("task-schema-test", documents)
    step_id_by_tool = {
        tool: tool.value.removeprefix("proofbid.") for tool in task_spec.allowed_tools
    }
    plan = ExecutionPlan(
        task_spec_digest=task_spec.digest,
        steps=tuple(
            PlanStep(
                step_id=step_id_by_tool[tool],
                tool=tool,
                depends_on=tuple(
                    step_id_by_tool[dependency]
                    for dependency in REQUIRED_TOOL_DEPENDENCIES[tool]
                ),
                completion_criterion=f"{tool.value} returns typed output.",
            )
            for tool in task_spec.allowed_tools
        ),
        summary="Validate every deterministic stage before delivery.",
    )
    receipt = ProviderReceipt(
        provider="test.schema",
        configured_model="test-model",
        model_version="test-model-v1",
        auth_mode="test",
        adk_version="2.7.1-test",
        genai_version="2.18.1-test",
        started_at=datetime.now(UTC).isoformat(),
        duration_ms=1,
        event_count=1,
        invocation_id="inv-test",
        interaction_id=None,
        finish_reason="STOP",
        prompt_tokens=1,
        output_tokens=1,
        total_tokens=2,
        request_digest="a" * 64,
        response_digest="b" * 64,
        plan_digest=plan.digest,
        schema_validated=True,
        policy_validated=True,
    )
    PlanningResult(plan=plan, receipt=receipt)

    jsonschema.validate(task_spec.to_dict(), _load_schema("task-spec.v1.schema.json"))
    jsonschema.validate(plan.to_dict(), _load_schema("execution-plan.v1.schema.json"))
    jsonschema.validate(
        receipt.to_dict(),
        _load_schema("provider-receipt.v1.schema.json"),
        format_checker=jsonschema.FormatChecker(),
    )
