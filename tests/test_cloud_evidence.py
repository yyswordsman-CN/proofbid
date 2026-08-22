from __future__ import annotations

from proofbid.cloud_evidence import _sanitized_logs, _service_environment, _service_image
from proofbid.task_worker import allowed_fixture_ids


def test_allowed_fixture_ids_defaults_to_both_and_validates_override() -> None:
    assert allowed_fixture_ids({}) == (
        "complete_tender",
        "blocked_missing_authorization",
    )
    assert allowed_fixture_ids({"PROOFBID_ALLOWED_FIXTURES": "complete_tender"}) == (
        "complete_tender",
    )


def test_cloud_evidence_helpers_extract_revision_binding_and_redact_logs() -> None:
    service = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "image": "us-docker.pkg.dev/example/proofbid@sha256:abc",
                            "env": [
                                {"name": "PROOFBID_BUILD_VERSION", "value": "a" * 40},
                                {"name": "SECRET", "value": "must-not-enter-summary"},
                            ],
                        }
                    ]
                }
            }
        }
    }
    assert _service_image(service).endswith("@sha256:abc")
    assert _service_environment(service)["PROOFBID_BUILD_VERSION"] == "a" * 40

    sanitized = _sanitized_logs(
        [
            {
                "timestamp": "2026-08-22T00:00:00Z",
                "severity": "INFO",
                "jsonPayload": {
                    "event": "provider_completed",
                    "task_id": "task-1234567890abcdef1234",
                    "invocation_id": "inv-1",
                    "source_text": "must-not-enter-summary",
                },
            }
        ]
    )
    assert sanitized[0]["event"] == "provider_completed"
    assert "source_text" not in sanitized[0]
