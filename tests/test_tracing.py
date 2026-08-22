from __future__ import annotations

import json

import pytest

from proofbid.tracing import TraceRecorder


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_trace_records_started_and_completed_without_source_body(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    recorder = TraceRecorder(trace_path, task_id="task_demo")

    with recorder.stage("extract") as stage:
        stage.complete(requirement_count=12, source_hash="abc123")

    events = _events(trace_path)
    assert [event["status"] for event in events] == ["started", "completed"]
    assert events[1]["details"]["requirement_count"] == 12
    assert "source_body" not in trace_path.read_text(encoding="utf-8")


def test_trace_records_failure_and_does_not_swallow_error(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    recorder = TraceRecorder(trace_path, task_id="task_failure")

    with pytest.raises(RuntimeError, match="synthetic failure"):
        with recorder.stage("render"):
            raise RuntimeError("synthetic failure")

    events = _events(trace_path)
    assert [event["status"] for event in events] == ["started", "failed"]
    assert events[-1]["details"]["error_type"] == "RuntimeError"
    outside = tmp_path / "outside.txt"
    outside.write_text("SENTINEL_SECRET\n", encoding="utf-8")
    trace_path = tmp_path / "symlink_trace.jsonl"
    trace_path.symlink_to(outside)

    with pytest.raises(ValueError, match="must not be a symlink"):
        TraceRecorder(trace_path, task_id="task_symlink")

    assert outside.read_text(encoding="utf-8") == "SENTINEL_SECRET\n"
