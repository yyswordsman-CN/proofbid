"""Cloud Run Job and local background task entrypoint."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .agent_runtime_v2 import run_scripted_agent_pipeline
from .task_store import TaskStore, task_store_from_env, validate_task_id


FIXTURE_WORKSPACES = {
    "complete_tender": "complete_tender",
    "blocked_missing_authorization": "blocked_missing_authorization",
}


def project_root() -> Path:
    configured = os.getenv("PROOFBID_PROJECT_ROOT")
    return Path(configured).resolve() if configured else Path(__file__).resolve().parents[2]


def fixture_workspace(fixture_id: str) -> Path:
    relative = FIXTURE_WORKSPACES.get(fixture_id)
    if relative is None:
        raise ValueError("Unknown fixture id")
    workspace = project_root() / "examples" / relative
    if not workspace.is_dir():
        raise RuntimeError(f"Built-in fixture is unavailable: {fixture_id}")
    return workspace


def _now() -> str:
    return datetime.now(UTC).isoformat()


def execute_task(
    task_id: str,
    fixture_id: str,
    store: TaskStore,
    *,
    google_agent: bool,
    inject_render_failure: bool = False,
) -> dict[str, Any]:
    validate_task_id(task_id)
    prior = store.read_state(task_id) or {}
    running = {
        **prior,
        "task_id": task_id,
        "fixture_id": fixture_id,
        "status": "running",
        "current_step": "agent_routing",
        "updated_at": _now(),
    }
    store.write_state(task_id, running)
    try:
        with tempfile.TemporaryDirectory(prefix="proofbid-task-") as temp:
            output = Path(temp) / "delivery"
            if google_agent:
                from .adapters.google.adk_tool_agent import run_google_tool_agent_pipeline

                result = run_google_tool_agent_pipeline(
                    fixture_workspace(fixture_id),
                    output,
                    inject_render_failure=inject_render_failure,
                )
            else:
                result = run_scripted_agent_pipeline(
                    fixture_workspace(fixture_id),
                    output,
                    inject_render_failure=inject_render_failure,
                )
            for path in output.iterdir():
                if path.is_file():
                    store.put_artifact(task_id, path.name, path)
            result_payload = json.loads((output / "result.json").read_text(encoding="utf-8"))
            receipt_rows = [
                json.loads(line)
                for line in (output / "tool_receipts.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            findings = result_payload.get("validations", [])
            analysis = result_payload.get("analysis", {})
            public_result = {
                key: value
                for key, value in result.items()
                if key not in {"artifacts"}
            }
            terminal = {
                **running,
                **public_result,
                "status": result["status"],
                "current_step": "delivery_ready",
                "bundle_ready": True,
                "tool_receipts": [
                    {
                        key: row.get(key)
                        for key in (
                            "sequence",
                            "tool",
                            "status",
                            "reason_code",
                            "duration_ms",
                            "retry_of",
                        )
                    }
                    for row in receipt_rows
                ],
                "evidence_summary": {
                    "requirement_count": len(analysis.get("requirements", [])),
                    "evidence_count": len(analysis.get("evidence", [])),
                    "matched_count": sum(
                        1
                        for row in analysis.get("matches", [])
                        if row.get("status") == "compliant"
                    ),
                    "missing_items": analysis.get("missing_items", []),
                },
                "validation_summary": {
                    "passed_count": sum(1 for row in findings if row.get("passed")),
                    "failed": [
                        {
                            "code": row.get("code"),
                            "severity": row.get("severity"),
                            "message": row.get("message"),
                        }
                        for row in findings
                        if not row.get("passed")
                    ],
                },
                "artifacts": sorted(path.name for path in output.iterdir() if path.is_file()),
                "updated_at": _now(),
            }
            store.write_state(task_id, terminal)
            return terminal
    except Exception as exc:
        failed = {
            **running,
            "status": "failed",
            "current_step": "failed_closed",
            "bundle_ready": False,
            "reason_code": getattr(exc, "reason_code", "TASK_EXECUTION_FAILED"),
            "error_type": type(exc).__name__,
            "updated_at": _now(),
        }
        store.write_state(task_id, failed)
        raise


def main() -> int:
    task_id = validate_task_id(os.environ["PROOFBID_TASK_ID"])
    fixture_id = os.environ["PROOFBID_FIXTURE_ID"]
    execute_task(
        task_id,
        fixture_id,
        task_store_from_env(),
        google_agent=os.getenv("PROOFBID_AGENT_MODE", "google") == "google",
        inject_render_failure=os.getenv("PROOFBID_INJECT_RENDER_FAILURE", "0") == "1",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FIXTURE_WORKSPACES", "execute_task", "fixture_workspace", "main"]
