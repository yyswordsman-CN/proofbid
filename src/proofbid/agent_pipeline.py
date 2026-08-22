"""Plan-gated entrypoint for the Google ADK ProofBid workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .intake import scan_workspace
from .pipeline import (
    REQUIRED_INPUTS,
    assert_output_target_available,
    new_task_id,
    run_pipeline,
)
from .planning import Planner, build_task_spec, validate_execution_plan


def run_agentic_pipeline(
    workspace: str | Path,
    output_dir: str | Path,
    *,
    planner: Planner,
) -> dict[str, Any]:
    """Plan first, fail closed, then execute the existing deterministic chain.

    Planning occurs before the output directory is created.  The deterministic
    intake scans the inputs again and rejects any drift from the planned source
    manifest before extracting facts or rendering artifacts.
    """

    assert_output_target_available(output_dir)
    task_id = new_task_id()
    documents = scan_workspace(Path(workspace), REQUIRED_INPUTS)
    task_spec = build_task_spec(task_id, documents)
    planning_result = planner.create_plan(task_spec)
    validate_execution_plan(planning_result.plan, task_spec)
    return run_pipeline(
        workspace=workspace,
        output_dir=output_dir,
        task_id=task_id,
        task_spec=task_spec,
        planning_result=planning_result,
    )


def run_google_pipeline(
    workspace: str | Path,
    output_dir: str | Path,
    *,
    model: str | None = None,
) -> dict[str, Any]:
    """Run one real Gemini-planned task through Google ADK.

    This is intentionally opt-in and never used by the baseline ``run``
    command or ordinary tests.
    """

    from .adapters.google.gemini import (
        GeminiProviderAdapter,
        GeminiProviderConfig,
        ProviderDependencyError,
    )

    config = GeminiProviderConfig.from_env(model=model)
    try:
        from .adapters.google.adk_planner import AdkPlanner
    except ImportError as exc:
        raise ProviderDependencyError(
            "Install the ProofBid google extra before using google-run."
        ) from exc
    provider = GeminiProviderAdapter(config)
    planner = AdkPlanner(provider)
    return run_agentic_pipeline(
        workspace=workspace,
        output_dir=output_dir,
        planner=planner,
    )


__all__ = ["run_agentic_pipeline", "run_google_pipeline"]
