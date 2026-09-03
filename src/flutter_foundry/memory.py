from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def record_learning(root: Path, kind: str, title: str, evidence: str, action: str, tags: list[str] | None = None) -> dict[str, Any]:
    allowed = {"pattern","false_positive","successful_strategy","failed_strategy","threat","policy_change","benchmark"}
    if kind not in allowed:
        raise ValueError(f"kind must be one of {sorted(allowed)}")
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "title": title,
        "evidence": evidence,
        "action": action,
        "tags": tags or [],
    }
    path = root / ".factory" / "memory" / "learnings.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def query_learnings(root: Path, terms: list[str], limit: int = 8) -> list[dict[str, Any]]:
    path = root / ".factory" / "memory" / "learnings.jsonl"
    if not path.exists():
        return []
    wanted = {t.lower() for t in terms}
    scored = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        hay = json.dumps(e).lower()
        score = sum(1 for t in wanted if t in hay)
        if score:
            scored.append((score, e))
    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:limit]]
