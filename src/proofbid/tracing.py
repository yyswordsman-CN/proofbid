"""Append-only, privacy-minimized trace events for the local ProofBid baseline."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _json_safe(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "value"):
        return _json_safe(value.value)
    return value


class TraceRecorder:
    """Write structured events without storing source document bodies."""

    def __init__(self, path: Path, task_id: str) -> None:
        self.path = path
        self.task_id = task_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise ValueError("Trace path must not be a symlink")
        self._sequence = 0

    def emit(
        self,
        *,
        step: str,
        status: str,
        actor: str = "proofbid.local",
        details: dict[str, Any] | None = None,
        duration_ms: float | None = None,
    ) -> dict[str, Any]:
        self._sequence += 1
        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:16]}",
            "task_id": self.task_id,
            "sequence": self._sequence,
            "timestamp": datetime.now(UTC).isoformat(),
            "step": step,
            "actor": actor,
            "status": status,
            "duration_ms": round(duration_ms, 3) if duration_ms is not None else None,
            "details": _json_safe(details or {}),
        }
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(self.path, flags, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event

    def stage(self, step: str) -> "_TraceStage":
        return _TraceStage(self, step)


class _TraceStage:
    def __init__(self, recorder: TraceRecorder, step: str) -> None:
        self.recorder = recorder
        self.step = step
        self.started_at = 0.0

    def __enter__(self) -> "_TraceStage":
        self.started_at = time.perf_counter()
        self.recorder.emit(step=self.step, status="started")
        return self

    def complete(self, **details: Any) -> None:
        elapsed = (time.perf_counter() - self.started_at) * 1000
        self.recorder.emit(
            step=self.step,
            status="completed",
            details=details,
            duration_ms=elapsed,
        )

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any) -> bool:
        if exc is not None:
            elapsed = (time.perf_counter() - self.started_at) * 1000
            self.recorder.emit(
                step=self.step,
                status="failed",
                details={"error_type": type(exc).__name__, "message": str(exc)[:500]},
                duration_ms=elapsed,
            )
        return False
