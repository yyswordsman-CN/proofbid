"""Local and Google Cloud Storage task state adapters."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Protocol


TASK_ID_RE = re.compile(r"^task-[0-9a-f]{20}$")


def validate_task_id(task_id: str) -> str:
    if not TASK_ID_RE.fullmatch(task_id):
        raise ValueError("Invalid task id")
    return task_id


class TaskStore(Protocol):
    def write_state(self, task_id: str, state: dict[str, Any]) -> None: ...

    def read_state(self, task_id: str) -> dict[str, Any] | None: ...

    def put_artifact(self, task_id: str, name: str, source: Path) -> None: ...

    def artifact_bytes(self, task_id: str, name: str) -> bytes | None: ...


class LocalTaskStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def task_dir(self, task_id: str) -> Path:
        return self.root / validate_task_id(task_id)

    def write_state(self, task_id: str, state: dict[str, Any]) -> None:
        task_dir = self.task_dir(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        target = task_dir / "state.json"
        staging = task_dir / ".state.json.tmp"
        staging.write_text(
            json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.replace(target)

    def read_state(self, task_id: str) -> dict[str, Any] | None:
        target = self.task_dir(task_id) / "state.json"
        if not target.is_file():
            return None
        payload = json.loads(target.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None

    def put_artifact(self, task_id: str, name: str, source: Path) -> None:
        destination = self.task_dir(task_id) / "artifacts" / Path(name).name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    def artifact_bytes(self, task_id: str, name: str) -> bytes | None:
        path = self.task_dir(task_id) / "artifacts" / Path(name).name
        return path.read_bytes() if path.is_file() else None


class GcsTaskStore:
    def __init__(self, bucket_name: str) -> None:
        if not bucket_name.strip():
            raise ValueError("PROOFBID_TASK_BUCKET is required")
        try:
            from google.cloud import storage
        except ImportError as exc:
            raise RuntimeError("Install the service extra for Google Cloud Storage") from exc
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    @staticmethod
    def _prefix(task_id: str) -> str:
        return f"tasks/{validate_task_id(task_id)}"

    def write_state(self, task_id: str, state: dict[str, Any]) -> None:
        self.bucket.blob(f"{self._prefix(task_id)}/state.json").upload_from_string(
            json.dumps(state, ensure_ascii=False, sort_keys=True),
            content_type="application/json",
        )

    def read_state(self, task_id: str) -> dict[str, Any] | None:
        blob = self.bucket.blob(f"{self._prefix(task_id)}/state.json")
        if not blob.exists(self.client):
            return None
        payload = json.loads(blob.download_as_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None

    def put_artifact(self, task_id: str, name: str, source: Path) -> None:
        self.bucket.blob(f"{self._prefix(task_id)}/artifacts/{Path(name).name}").upload_from_filename(
            str(source)
        )

    def artifact_bytes(self, task_id: str, name: str) -> bytes | None:
        blob = self.bucket.blob(f"{self._prefix(task_id)}/artifacts/{Path(name).name}")
        if not blob.exists(self.client):
            return None
        return blob.download_as_bytes()


def task_store_from_env() -> TaskStore:
    backend = os.getenv("PROOFBID_STORAGE_BACKEND", "local").strip().casefold()
    if backend == "gcs":
        return GcsTaskStore(os.getenv("PROOFBID_TASK_BUCKET", ""))
    if backend != "local":
        raise ValueError("PROOFBID_STORAGE_BACKEND must be local or gcs")
    return LocalTaskStore(os.getenv("PROOFBID_TASK_ROOT", "/tmp/proofbid-tasks"))


__all__ = [
    "GcsTaskStore",
    "LocalTaskStore",
    "TaskStore",
    "task_store_from_env",
    "validate_task_id",
]
