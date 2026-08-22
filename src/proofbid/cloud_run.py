"""Minimal authenticated Cloud Run Jobs v2 execution client."""

from __future__ import annotations

import os
from typing import Any


def execute_cloud_run_job(task_id: str, fixture_id: str) -> str:
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.getenv("PROOFBID_CLOUD_RUN_LOCATION", "us-central1")
    job = os.environ["PROOFBID_CLOUD_RUN_JOB"]
    url = (
        f"https://run.googleapis.com/v2/projects/{project}/locations/{location}"
        f"/jobs/{job}:run"
    )
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
    except ImportError as exc:
        raise RuntimeError("Install the service extra for Cloud Run execution") from exc
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    response = AuthorizedSession(credentials).post(
        url,
        json={
            "overrides": {
                "containerOverrides": [
                    {
                        "env": [
                            {"name": "PROOFBID_TASK_ID", "value": task_id},
                            {"name": "PROOFBID_FIXTURE_ID", "value": fixture_id},
                        ]
                    }
                ],
                "taskCount": 1,
                "timeout": "600s",
            }
        },
        timeout=30,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    execution_name = str(payload.get("metadata", {}).get("name") or payload.get("name") or "")
    if not execution_name:
        raise RuntimeError("Cloud Run Jobs API returned no execution name")
    return execution_name


__all__ = ["execute_cloud_run_job"]
