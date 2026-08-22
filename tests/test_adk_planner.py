from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


pytest.importorskip("google.adk")

from google.adk.models import BaseLlm, LlmResponse  # noqa: E402
from google.genai import types  # noqa: E402
from pydantic import PrivateAttr  # noqa: E402

from proofbid import scan_workspace  # noqa: E402
from proofbid.adapters.google.adk_planner import (  # noqa: E402
    AdkPlanner,
    PlannerResponseError,
)
from proofbid.adapters.google.gemini import (  # noqa: E402
    GeminiAuthMode,
    GeminiProviderAdapter,
    GeminiProviderConfig,
)
from proofbid.planning import (  # noqa: E402
    EXECUTION_PLAN_SCHEMA_VERSION,
    PlanTool,
    REQUIRED_TOOL_DEPENDENCIES,
    build_task_spec,
)


FIXTURE = Path(__file__).parents[1] / "examples" / "synthetic_tender"


def _task_spec():
    documents = scan_workspace(
        FIXTURE,
        ("tender.md", "bidder_profile.json", "catalog.csv"),
    )
    return build_task_spec("task-adk-test", documents)


def _payload(task_spec) -> dict:
    step_id_by_tool = {
        tool: tool.value.removeprefix("proofbid.") for tool in task_spec.allowed_tools
    }
    return {
        "schema_version": EXECUTION_PLAN_SCHEMA_VERSION,
        "task_spec_digest": task_spec.digest,
        "steps": [
            {
                "step_id": step_id_by_tool[tool],
                "tool": tool.value,
                "depends_on": [
                    step_id_by_tool[dependency]
                    for dependency in REQUIRED_TOOL_DEPENDENCIES[tool]
                ],
                "completion_criterion": f"{tool.value} returns typed output.",
            }
            for tool in task_spec.allowed_tools
        ],
        "summary": "Complete the bounded deterministic DAG without inventing facts.",
    }


class _FakeLlm(BaseLlm):
    response_payload: dict | None
    response_finish_reason: types.FinishReason = types.FinishReason.STOP
    _seen_request: Any = PrivateAttr(default=None)

    def __init__(
        self,
        payload: dict | None,
        *,
        finish_reason: types.FinishReason = types.FinishReason.STOP,
    ) -> None:
        super().__init__(
            model="fake-gemini",
            response_payload=payload,
            response_finish_reason=finish_reason,
        )

    async def generate_content_async(self, llm_request, stream: bool = False):
        self._seen_request = llm_request
        text = (
            json.dumps(self.response_payload)
            if self.response_payload is not None
            else "not-json"
        )
        yield LlmResponse(
            model_version="fake-gemini-v1",
            content=types.Content(role="model", parts=[types.Part(text=text)]),
            finish_reason=self.response_finish_reason,
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=100,
                candidates_token_count=50,
                total_token_count=150,
            ),
        )


class _FakeProvider:
    provider_name = "test.adk"
    configured_model = "fake-gemini"
    auth_mode = "test"
    timeout_seconds = 5.0

    def __init__(self, model: _FakeLlm) -> None:
        self.model = model

    def package_versions(self) -> tuple[str, str]:
        return "2.7.1-test", "2.18.1-test"

    def build_model(self):
        return self.model


def test_adk_runner_returns_schema_and_policy_validated_plan() -> None:
    task_spec = _task_spec()
    model = _FakeLlm(_payload(task_spec))
    result = AdkPlanner(_FakeProvider(model)).create_plan(task_spec)

    assert result.receipt.schema_validated is True
    assert result.receipt.policy_validated is True
    assert result.receipt.model_version == "fake-gemini-v1"
    assert result.receipt.total_tokens == 150
    assert {step.tool for step in result.plan.steps} == set(PlanTool)
    assert model._seen_request is not None
    assert model._seen_request.tools_dict == {}
    request_text = "\n".join(
        part.text or ""
        for content in model._seen_request.contents
        for part in content.parts or ()
    )
    assert "制造商针对本项目" not in request_text
    assert "source_hash" in request_text


def test_adk_runner_rejects_malformed_or_unknown_tool_output() -> None:
    task_spec = _task_spec()
    malformed = _FakeLlm(None)
    with pytest.raises(PlannerResponseError):
        AdkPlanner(_FakeProvider(malformed)).create_plan(task_spec)

    unknown = _payload(task_spec)
    unknown["steps"][0]["tool"] = "shell.exec"
    with pytest.raises(PlannerResponseError):
        AdkPlanner(_FakeProvider(_FakeLlm(unknown))).create_plan(task_spec)


def test_adk_runner_rejects_non_success_finish_reason() -> None:
    task_spec = _task_spec()
    model = _FakeLlm(
        _payload(task_spec),
        finish_reason=types.FinishReason.MAX_TOKENS,
    )

    with pytest.raises(PlannerResponseError, match="finish successfully"):
        AdkPlanner(_FakeProvider(model)).create_plan(task_spec)


def test_pinned_gemini_adapter_constructs_exact_model_without_network() -> None:
    adapter = GeminiProviderAdapter(
        GeminiProviderConfig(
            model="gemini-3.5-flash",
            auth_mode=GeminiAuthMode.API_KEY,
            timeout_seconds=30,
            max_attempts=2,
        )
    )

    model = adapter.build_model()
    assert type(model).__name__ == "Gemini"
    assert model.model == "gemini-3.5-flash"
    assert adapter.package_versions() == ("2.7.1", "2.18.1")


def test_gemini_adapter_pins_selected_backend(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_USE_ENTERPRISE", "true")
    monkeypatch.setenv("GOOGLE_API_KEY", "synthetic")
    api_model = GeminiProviderAdapter(
        GeminiProviderConfig(
            model="gemini-3.5-flash",
            auth_mode=GeminiAuthMode.API_KEY,
        )
    ).build_model()
    assert api_model.api_client.vertexai is False

    monkeypatch.setenv("GOOGLE_GENAI_USE_ENTERPRISE", "false")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "synthetic-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    vertex_model = GeminiProviderAdapter(
        GeminiProviderConfig(
            model="gemini-3.5-flash",
            auth_mode=GeminiAuthMode.VERTEX_AI,
        )
    ).build_model()
    assert vertex_model.api_client.vertexai is True
