"""Collect and reconcile a redacted Google Cloud closure evidence summary."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .task_store import validate_task_id


ARTIFACT_NAMES = (
    "planner_receipt.json",
    "agent_run.json",
    "tool_receipts.jsonl",
    "manifest.json",
    "proofbid_bundle.zip",
)


def _run_json(arguments: list[str]) -> Any:
    completed = subprocess.run(
        arguments,
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    return json.loads(completed.stdout)


def _run_bytes(arguments: list[str]) -> bytes:
    completed = subprocess.run(
        arguments,
        check=True,
        capture_output=True,
        timeout=90,
    )
    return completed.stdout


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _nested(payload: dict[str, Any], *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _service_image(service: dict[str, Any]) -> str | None:
    containers = (
        _nested(service, "spec", "containers")
        or _nested(service, "spec", "template", "spec", "containers")
        or []
    )
    return str(containers[0].get("image")) if containers else None


def _service_environment(service: dict[str, Any]) -> dict[str, str]:
    containers = _nested(service, "spec", "template", "spec", "containers") or []
    rows = containers[0].get("env", []) if containers else []
    return {
        str(row.get("name")): str(row.get("value"))
        for row in rows
        if isinstance(row, dict) and row.get("name") and row.get("value") is not None
    }


def _execution_environment(execution: dict[str, Any]) -> dict[str, str]:
    containers = _nested(execution, "spec", "template", "spec", "containers") or []
    rows = containers[0].get("env", []) if containers else []
    return {
        str(row.get("name")): str(row.get("value"))
        for row in rows
        if isinstance(row, dict) and row.get("name") and row.get("value") is not None
    }


def _sanitized_logs(rows: list[Any]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        payload = row.get("jsonPayload") if isinstance(row.get("jsonPayload"), dict) else {}
        if not payload.get("event") and not payload.get("task_id"):
            continue
        sanitized.append(
            {
                "timestamp": row.get("timestamp"),
                "severity": row.get("severity"),
                "event": payload.get("event"),
                "task_id": payload.get("task_id"),
                "status": payload.get("status"),
                "reason_code": payload.get("reason_code"),
                "invocation_id": payload.get("invocation_id"),
            }
        )
    return sanitized


def _task_url(service_url: str, task_id: str) -> str:
    return f"{service_url.rstrip('/')}/api/v1/tasks/{task_id}"


def _fetch_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.loads(response.read())
    if not isinstance(payload, dict):
        raise RuntimeError("Task endpoint did not return an object")
    return payload


def _fetch_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def collect(args: argparse.Namespace) -> dict[str, Any]:
    task_id = validate_task_id(args.task_id)
    raw_dir = Path(args.raw_dir).expanduser().resolve() / task_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    service = _run_json(
        [
            "gcloud", "run", "services", "describe", args.service,
            "--project", args.project, "--region", args.region, "--format=json",
        ]
    )
    service_url = str(_nested(service, "status", "url") or "")
    revision = str(_nested(service, "status", "latestReadyRevisionName") or "")
    image = _service_image(service)
    revision_payload = _run_json(
        [
            "gcloud", "run", "revisions", "describe", revision,
            "--project", args.project, "--region", args.region, "--format=json",
        ]
    )
    image_digest = _service_image(revision_payload)
    service_environment = _service_environment(service)
    execution_id = args.execution.rsplit("/", 1)[-1]
    execution = _run_json(
        [
            "gcloud", "run", "jobs", "executions", "describe", execution_id,
            "--project", args.project, "--region", args.region, "--format=json",
        ]
    )
    execution_environment = _execution_environment(execution)
    task_state = _fetch_json(_task_url(service_url, task_id))
    bundle_url = str(
        task_state.get("bundle_url")
        or f"{_task_url(service_url, task_id)}/bundle"
    )
    service_bundle = _fetch_bytes(bundle_url)

    raw_payloads: dict[str, bytes] = {}
    metadata: dict[str, Any] = {}
    for name in ARTIFACT_NAMES:
        uri = f"gs://{args.bucket}/tasks/{task_id}/artifacts/{name}"
        raw_payloads[name] = _run_bytes(["gcloud", "storage", "cat", uri])
        metadata[name] = _run_json(
            ["gcloud", "storage", "objects", "describe", uri, "--format=json"]
        )
        (raw_dir / name).write_bytes(raw_payloads[name])

    provider = json.loads(raw_payloads["planner_receipt.json"])
    agent_run = json.loads(raw_payloads["agent_run.json"])
    tool_receipts = [
        json.loads(line)
        for line in raw_payloads["tool_receipts.jsonl"].decode("utf-8").splitlines()
        if line.strip()
    ]
    manifest = json.loads(raw_payloads["manifest.json"])
    log_query = (
        f'jsonPayload.task_id="{task_id}" OR textPayload:"{task_id}"'
    )
    logs = _run_json(
        [
            "gcloud", "logging", "read", log_query,
            "--project", args.project, "--limit", "200", "--format=json",
        ]
    )
    (raw_dir / "service.json").write_text(json.dumps(service, indent=2), encoding="utf-8")
    (raw_dir / "revision.json").write_text(
        json.dumps(revision_payload, indent=2), encoding="utf-8"
    )
    (raw_dir / "execution.json").write_text(json.dumps(execution, indent=2), encoding="utf-8")
    (raw_dir / "task-state.json").write_text(json.dumps(task_state, indent=2), encoding="utf-8")
    (raw_dir / "logs.json").write_text(json.dumps(logs, indent=2), encoding="utf-8")
    (raw_dir / "service-download.zip").write_bytes(service_bundle)

    manifest_files = {
        row.get("path"): row for row in manifest.get("files", []) if isinstance(row, dict)
    }
    provider_manifest = manifest_files.get("planner_receipt.json", {})
    zip_sha = _sha256(raw_payloads["proofbid_bundle.zip"])
    provider_sha = _sha256(raw_payloads["planner_receipt.json"])
    function_call_ids = [row.get("function_call_id") for row in tool_receipts]
    task_build_version = (
        task_state.get("build_version")
        or execution_environment.get("PROOFBID_BUILD_VERSION")
    )
    recovery_receipts = [
        {
            key: row.get(key)
            for key in ("sequence", "tool", "status", "reason_code", "retry_of")
        }
        for row in tool_receipts
        if row.get("status") != "completed" or row.get("tool") == "retry_render"
    ]
    summary = {
        "schema_version": "proofbid.cloud-evidence/v1",
        "collected_at": datetime.now(UTC).isoformat(),
        "project": args.project,
        "region": args.region,
        "service": {
            "name": args.service,
            "url": service_url,
            "revision": revision,
            "image": image,
            "image_digest": image_digest,
            "build_version": service_environment.get("PROOFBID_BUILD_VERSION"),
        },
        "job": {
            "name": args.job,
            "execution": args.execution,
            "observed_name": _nested(execution, "metadata", "name"),
            "completion_time": _nested(execution, "status", "completionTime"),
            "fixture_id": execution_environment.get("PROOFBID_FIXTURE_ID"),
            "render_failure_injected":
                execution_environment.get("PROOFBID_INJECT_RENDER_FAILURE") == "1",
        },
        "task": {
            "task_id": task_id,
            "status": task_state.get("status"),
            "build_version": task_build_version,
            "artifact_integrity_passed": task_state.get("artifact_integrity_passed"),
            "missing_item_count": task_state.get("missing_item_count"),
            "blocking_reason_codes": task_state.get("blocking_reason_codes"),
        },
        "provider": provider,
        "agent": {
            "status": agent_run.get("status"),
            "tool_call_count": agent_run.get("tool_call_count"),
            "tool_receipts_digest": agent_run.get("tool_receipts_digest"),
            "function_call_ids": function_call_ids,
            "recovery_receipts": recovery_receipts,
        },
        "gcs": {
            name: {
                "generation": value.get("generation"),
                "size": value.get("size"),
                "md5_hash": value.get("md5Hash"),
                "crc32c": value.get("crc32c"),
                "sha256": _sha256(raw_payloads[name]),
            }
            for name, value in metadata.items()
        },
        "reconciliation": {
            "provider_manifest_sha256": provider_manifest.get("sha256"),
            "provider_download_sha256": provider_sha,
            "provider_hash_matches_manifest": provider_manifest.get("sha256") == provider_sha,
            "zip_sha256": zip_sha,
            "service_zip_sha256": _sha256(service_bundle),
            "service_zip_matches_gcs": _sha256(service_bundle) == zip_sha,
            "all_function_call_ids_present": bool(function_call_ids) and all(function_call_ids),
            "build_matches_revision_source": bool(task_build_version)
            and task_build_version == service_environment.get("PROOFBID_BUILD_VERSION")
            and task_build_version
            == execution_environment.get("PROOFBID_BUILD_VERSION"),
            "revision_image_is_digest_pinned": bool(image_digest)
            and "@sha256:" in str(image_digest),
        },
        "logs": {
            "query": log_query,
            "events": _sanitized_logs(logs if isinstance(logs, list) else []),
        },
    }
    if task_state.get("status") not in {"completed", "blocked"}:
        raise RuntimeError("Task is not in a valid terminal state")
    required_checks = (
        summary["task"]["artifact_integrity_passed"] is True,
        summary["reconciliation"]["provider_hash_matches_manifest"] is True,
        summary["reconciliation"]["service_zip_matches_gcs"] is True,
        summary["reconciliation"]["all_function_call_ids_present"] is True,
        summary["reconciliation"]["build_matches_revision_source"] is True,
        summary["reconciliation"]["revision_image_is_digest_pinned"] is True,
    )
    if not all(required_checks):
        raise RuntimeError("Cloud evidence reconciliation failed")
    return summary


def _markdown(summary: dict[str, Any]) -> str:
    provider = summary["provider"]
    task = summary["task"]
    service = summary["service"]
    job = summary["job"]
    reconcile = summary["reconciliation"]
    lines = [
            f"# ProofBid Google Cloud evidence — {task['task_id']}",
            "",
            f"- Service URL: `{service['url']}`",
            f"- Revision: `{service['revision']}`",
            f"- Image: `{service['image']}`",
            f"- Image digest: `{service['image_digest']}`",
            f"- Job execution: `{job['execution']}`",
            f"- Task status: `{task['status']}`",
            f"- Build version: `{task['build_version']}`",
            f"- Provider/model: `{provider.get('provider')}` / `{provider.get('model_version')}`",
            f"- Invocation ID: `{provider.get('invocation_id')}`",
            f"- Usage: prompt `{provider.get('prompt_tokens')}`, output `{provider.get('output_tokens')}`, total `{provider.get('total_tokens')}`",
            f"- ZIP SHA-256: `{reconcile['zip_sha256']}`",
            f"- Service ZIP matches GCS: `{reconcile['service_zip_matches_gcs']}`",
            f"- Provider manifest hash reconciled: `{reconcile['provider_hash_matches_manifest']}`",
            f"- All FunctionTool call IDs present: `{reconcile['all_function_call_ids_present']}`",
    ]
    if job.get("render_failure_injected"):
        lines.extend(
            (
                "- Administrator renderer failure injected: `True`",
                f"- Recovery receipts: `{json.dumps(summary['agent']['recovery_receipts'], ensure_ascii=False)}`",
            )
        )
    lines.extend(("", f"Cloud Logging query: `{summary['logs']['query']}`", ""))
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--execution", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--raw-dir", default=".proofbid/evidence-raw")
    return parser


def main() -> int:
    args = _parser().parse_args()
    summary = collect(args)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(_markdown(summary), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["collect", "main"]
