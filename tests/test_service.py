from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from proofbid.service import create_app
from proofbid.task_store import LocalTaskStore


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(LocalTaskStore(tmp_path / "tasks")))


def test_task_api_accepts_polls_and_downloads_validated_bundle(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        created = client.post(
            "/api/v1/tasks",
            json={"fixture_id": "complete_tender"},
        )
        assert created.status_code == 202
        payload = created.json()
        assert payload["task_id"].startswith("task-")
        assert payload["status_url"].endswith(payload["task_id"])

        task = client.get(f"/api/v1/tasks/{payload['task_id']}")
        assert task.status_code == 200
        state = task.json()
        assert state["status"] == "completed"
        assert state["ready_for_submission"] is True
        assert state["bundle_url"]

        bundle = client.get(f"/api/v1/tasks/{payload['task_id']}/bundle")
        assert bundle.status_code == 200
        assert bundle.headers["content-type"] == "application/zip"
        assert bundle.content.startswith(b"PK")


def test_task_api_rejects_unknown_fixture(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        response = client.post("/api/v1/tasks", json={"fixture_id": "arbitrary_upload"})
    assert response.status_code == 422


def test_bundle_gate_rejects_nonterminal_task(tmp_path: Path) -> None:
    store = LocalTaskStore(tmp_path / "tasks")
    task_id = "task-1234567890abcdef1234"
    store.write_state(
        task_id,
        {
            "task_id": task_id,
            "fixture_id": "complete_tender",
            "status": "running",
            "bundle_ready": False,
        },
    )
    with TestClient(create_app(store)) as client:
        response = client.get(f"/api/v1/tasks/{task_id}/bundle")
    assert response.status_code == 409


def test_health_does_not_run_agent(tmp_path: Path) -> None:
    store = LocalTaskStore(tmp_path / "tasks")
    with TestClient(create_app(store)) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert list((tmp_path / "tasks").iterdir()) == []
