"""FastAPI task service and same-origin React host for ProofBid."""

from __future__ import annotations

import os
import threading
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from .cloud_run import execute_cloud_run_job
from .pipeline import new_task_id
from .task_store import LocalTaskStore, TaskStore, task_store_from_env
from .task_worker import FIXTURE_WORKSPACES, execute_task


BUILD_VERSION = os.getenv("PROOFBID_BUILD_VERSION", "dev")
TERMINAL_STATUSES = {"completed", "blocked", "failed"}


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_id: str


class DemoQuota:
    def __init__(self, maximum: int) -> None:
        self.maximum = maximum
        self._lock = threading.Lock()
        self._day = date.today()
        self._count = 0

    def consume(self) -> bool:
        today = datetime.now(UTC).date()
        with self._lock:
            if today != self._day:
                self._day = today
                self._count = 0
            if self._count >= self.maximum:
                return False
            self._count += 1
            return True


def _public_state(state_payload: dict[str, Any], request: Request) -> dict[str, Any]:
    task_id = str(state_payload["task_id"])
    payload = dict(state_payload)
    payload["status_url"] = str(request.url_for("get_task", task_id=task_id))
    payload["bundle_url"] = (
        str(request.url_for("get_bundle", task_id=task_id))
        if state_payload.get("bundle_ready")
        else None
    )
    return payload


def create_app(store: TaskStore | None = None) -> FastAPI:
    selected_store = store or task_store_from_env()
    app = FastAPI(
        title="ProofBid Taskmaster API",
        version="1.0.0",
        docs_url=None if os.getenv("PROOFBID_PUBLIC_DEMO") == "1" else "/docs",
        redoc_url=None,
    )
    worker_lock = threading.Lock()
    quota = DemoQuota(maximum=int(os.getenv("PROOFBID_DAILY_DEMO_QUOTA", "40")))
    cloud_backend = os.getenv("PROOFBID_STORAGE_BACKEND", "local").casefold() == "gcs"

    def run_local_task(task_id: str, fixture_id: str) -> None:
        with worker_lock:
            execute_task(
                task_id,
                fixture_id,
                selected_store,
                google_agent=os.getenv("PROOFBID_LOCAL_AGENT_MODE", "scripted") == "google",
            )

    @app.get("/healthz", name="healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "build_version": BUILD_VERSION}

    @app.post("/api/v1/tasks", status_code=status.HTTP_202_ACCEPTED, name="create_task")
    def create_task(
        request_body: TaskCreateRequest,
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        fixture_id = request_body.fixture_id
        if fixture_id not in FIXTURE_WORKSPACES:
            raise HTTPException(status_code=422, detail="Unknown fixture_id")
        if not quota.consume():
            raise HTTPException(status_code=429, detail="Daily demo quota exceeded")
        task_id = new_task_id()
        accepted = {
            "task_id": task_id,
            "fixture_id": fixture_id,
            "status": "accepted",
            "current_step": "event_received",
            "bundle_ready": False,
            "cloud_execution_id": None,
            "build_version": BUILD_VERSION,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        selected_store.write_state(task_id, accepted)
        if cloud_backend:
            try:
                execution_id = execute_cloud_run_job(task_id, fixture_id)
            except Exception as exc:
                failed = {
                    **accepted,
                    "status": "failed",
                    "current_step": "job_trigger_failed",
                    "reason_code": "CLOUD_JOB_TRIGGER_FAILED",
                    "error_type": type(exc).__name__,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                selected_store.write_state(task_id, failed)
                raise HTTPException(status_code=503, detail="Cloud task dispatch failed") from exc
            accepted.update(
                status="queued",
                current_step="cloud_job_queued",
                cloud_execution_id=execution_id,
                updated_at=datetime.now(UTC).isoformat(),
            )
            selected_store.write_state(task_id, accepted)
        else:
            accepted.update(status="queued", current_step="local_worker_queued")
            selected_store.write_state(task_id, accepted)
            background_tasks.add_task(run_local_task, task_id, fixture_id)
        return {
            "task_id": task_id,
            "status_url": str(request.url_for("get_task", task_id=task_id)),
        }

    @app.get("/api/v1/tasks/{task_id}", name="get_task")
    def get_task(task_id: str, request: Request) -> dict[str, Any]:
        try:
            state_payload = selected_store.read_state(task_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Task not found") from exc
        if state_payload is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return _public_state(state_payload, request)

    @app.get("/api/v1/tasks/{task_id}/bundle", name="get_bundle")
    def get_bundle(task_id: str) -> Response:
        try:
            state_payload = selected_store.read_state(task_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Task not found") from exc
        if state_payload is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if state_payload.get("status") not in {"completed", "blocked"}:
            raise HTTPException(status_code=409, detail="Delivery is not ready")
        if not state_payload.get("bundle_ready") or not state_payload.get(
            "artifact_integrity_passed"
        ):
            raise HTTPException(status_code=409, detail="Delivery validation has not passed")
        bundle = selected_store.artifact_bytes(task_id, "proofbid_bundle.zip")
        if bundle is None:
            raise HTTPException(status_code=404, detail="Bundle artifact not found")
        return Response(
            content=bundle,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="proofbid-{task_id}.zip"',
                "Cache-Control": "private, max-age=60",
            },
        )

    web_dist = Path(
        os.getenv(
            "PROOFBID_WEB_DIST",
            str(Path(__file__).resolve().parents[2] / "apps" / "web" / "dist"),
        )
    ).resolve()
    if web_dist.is_dir():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    return app


app = create_app()


__all__ = ["app", "create_app"]
