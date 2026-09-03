from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def foundry_event(name: str, *, service: str = "nakeuri-foundry", attributes: dict[str, Any] | None = None, trace_id: str | None = None) -> dict[str, Any]:
    if not name or len(name) > 160:
        raise ValueError("invalid event name")
    attrs = {"service.name": service, **(attributes or {})}
    return {
        "schema": "nakeuri/telemetry-event/v1",
        "timestamp": _now(),
        "trace_id": trace_id or secrets.token_hex(16),
        "name": name,
        "attributes": attrs,
    }


def append_event(root: Path, event: dict[str, Any]) -> Path:
    p = root.resolve() / ".factory" / "telemetry" / "events.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
    return p
