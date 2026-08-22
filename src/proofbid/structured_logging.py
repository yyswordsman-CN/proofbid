"""Privacy-minimized JSON events for Cloud Run stdout collection."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


def emit_event(event: str, **fields: Any) -> None:
    payload = {
        "schema_version": "proofbid.cloud-event/v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "event": event,
        **{
            key: value
            for key, value in fields.items()
            if value is None or isinstance(value, (str, int, float, bool))
        },
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)


__all__ = ["emit_event"]
