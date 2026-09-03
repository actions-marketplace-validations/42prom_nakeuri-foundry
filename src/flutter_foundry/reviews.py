from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .safe_paths import resolve_inside, safe_identifier


def _git(root: Path, *args: str) -> str | None:
    try:
        p = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=5)
        return p.stdout.strip() if p.returncode == 0 else None
    except Exception:
        return None


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_review(
    root: Path,
    task_id: str,
    reviewer: str,
    writer: str,
    status: str,
    findings: list[dict[str, Any]] | None = None,
    commit: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if not reviewer or not writer:
        raise ValueError("reviewer and writer identities are required")
    if reviewer == writer:
        raise ValueError("writer cannot independently review their own work")
    status = status.upper()
    if status not in {"PASS", "FAIL", "WARN"}:
        raise ValueError("invalid review status")
    commit = commit or _git(root, "rev-parse", "HEAD")
    if not commit:
        raise ValueError("review must be bound to a git commit")
    payload = {
        "schema": "foundry/review/v1",
        "task_id": task_id,
        "reviewer": reviewer,
        "writer": writer,
        "independent": True,
        "commit": commit,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "findings": findings or [],
    }
    task_id = safe_identifier(task_id, label="task_id")
    reviewer_file = safe_identifier(reviewer, label="reviewer")
    base = root / ".factory" / "reviews" / task_id
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{reviewer_file}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**payload, "artifact": str(path.relative_to(root)), "sha256": _sha(path)}


def validate_review(root: Path, review: dict[str, Any], expected_commit: str | None = None) -> tuple[bool, str]:
    required = {"schema", "task_id", "reviewer", "writer", "independent", "commit", "status", "artifact", "sha256"}
    missing = required - set(review)
    if missing:
        return False, f"missing fields: {sorted(missing)}"
    if review["schema"] != "foundry/review/v1":
        return False, "unsupported schema"
    if not review.get("independent") or review.get("reviewer") == review.get("writer"):
        return False, "review is not independent"
    if review.get("status") not in {"PASS", "FAIL", "WARN"}:
        return False, "invalid status"
    if expected_commit and review.get("commit") != expected_commit:
        return False, "review is bound to the wrong commit"
    try:
        path = resolve_inside(root, str(review["artifact"]), must_exist=True)
    except ValueError as exc:
        return False, f"unsafe review artifact path: {exc}"
    if not path.is_file():
        return False, "review artifact is not a file"
    if _sha(path) != review["sha256"]:
        return False, "review artifact hash mismatch"
    try:
        on_disk = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False, "review artifact is invalid JSON"
    for key in ["task_id", "reviewer", "writer", "independent", "commit", "status"]:
        if on_disk.get(key) != review.get(key):
            return False, f"review artifact mismatch: {key}"
    return True, "ok"
