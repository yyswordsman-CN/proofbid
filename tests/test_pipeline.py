from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from proofbid.pipeline import PipelineError, run_pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_WORKSPACE = PROJECT_ROOT / "examples" / "synthetic_tender"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_synthetic_workspace_runs_end_to_end(tmp_path: Path) -> None:
    output = tmp_path / "delivery"
    summary = run_pipeline(SYNTHETIC_WORKSPACE, output)

    assert summary["status"] == "completed_with_blockers"
    assert summary["ready_for_submission"] is False
    assert summary["requirement_count"] == 12
    assert summary["bom_line_count"] == 2
    assert summary["catalog_subtotal"] == 274_000
    assert summary["blocking_missing_item_count"] >= 1
    assert summary["artifact_integrity_passed"] is True

    expected = {
        "requirements.json",
        "evidence.json",
        "result.json",
        "proofbid.xlsx",
        "proofbid_report.docx",
        "trace.jsonl",
        "manifest.json",
        "proofbid_bundle.zip",
    }
    assert {path.name for path in output.iterdir()} == expected

    result = json.loads((output / "result.json").read_text(encoding="utf-8"))
    assert result["ready_for_human_review"] is False
    assert result["summary"]["requirements"] == 12
    assert result["summary"]["bom_lines"] == 2
    analysis = result["analysis"]
    assert [line["item_id"] for line in analysis["bom"]] == [
        "DISPLAY-98",
        "CONTROL-16",
    ]
    assert any(
        "授权书" in item["description"] and item["blocks_completion"]
        for item in analysis["missing_items"]
    )

    events = [
        json.loads(line)
        for line in (output / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    for step in (
        "intake",
        "extraction",
        "matching",
        "domain_validation",
        "render",
        "artifact_validation",
    ):
        statuses = {event["status"] for event in events if event["step"] == step}
        assert statuses == {"started", "completed"}
    artifact_validation = next(
        event
        for event in events
        if event["step"] == "artifact_validation" and event["status"] == "completed"
    )
    assert artifact_validation["details"]["artifact_integrity_passed"] is True
    assert artifact_validation["details"]["delivery_report_passed"] is False
    assert artifact_validation["details"]["fatal_count"] == 0
    domain_validation = next(
        event
        for event in events
        if event["step"] == "domain_validation" and event["status"] == "completed"
    )
    assert domain_validation["details"]["integrity_passed"] is True
    assert domain_validation["details"]["domain_report_passed"] is False
    assert domain_validation["details"]["ready_for_submission"] is False

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    declared = {entry["path"]: entry for entry in manifest["files"]}
    assert declared["trace.jsonl"]["sha256"] == _sha256(output / "trace.jsonl")
    with zipfile.ZipFile(output / "proofbid_bundle.zip") as archive:
        assert archive.testzip() is None
        assert "proofbid_bundle.zip" not in archive.namelist()
        assert set(archive.namelist()) == set(declared) | {"manifest.json"}


def test_pipeline_refuses_nonempty_output_without_overwriting(tmp_path: Path) -> None:
    output = tmp_path / "delivery"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("user-owned", encoding="utf-8")

    with pytest.raises(PipelineError, match="new or empty"):
        run_pipeline(SYNTHETIC_WORKSPACE, output)

    assert sentinel.read_text(encoding="utf-8") == "user-owned"
    assert set(output.iterdir()) == {sentinel}
