from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .safe_paths import safe_identifier

STATES = {
    "PREPARED": {"STAGING", "CANCELLED"},
    "STAGING": {"CANARY", "FAILED", "CANCELLED"},
    "CANARY": {"PRODUCTION", "ROLLING_BACK", "FAILED", "CANCELLED"},
    "PRODUCTION": {"VERIFIED", "ROLLING_BACK", "FAILED"},
    "ROLLING_BACK": {"ROLLED_BACK", "FAILED"},
    "VERIFIED": set(),
    "ROLLED_BACK": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class HealthPolicy:
    max_error_rate: float = 0.01
    min_crash_free_sessions: float = 0.995
    max_p95_latency_ms: float = 1000.0
    min_sample_count: int = 100
    required_consecutive_windows: int = 3

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_health(policy: HealthPolicy, windows: list[dict[str, Any]]) -> dict[str, Any]:
    checked = []
    for idx, sample in enumerate(windows):
        reasons = []
        count = int(sample.get("sample_count", 0) or 0)
        error_rate = float(sample.get("error_rate", 1.0) or 0)
        crash_free = float(sample.get("crash_free_sessions", 0.0) or 0)
        latency = float(sample.get("p95_latency_ms", float("inf")) or 0)
        if count < policy.min_sample_count:
            reasons.append("insufficient sample_count")
        if error_rate > policy.max_error_rate:
            reasons.append("error_rate above threshold")
        if crash_free < policy.min_crash_free_sessions:
            reasons.append("crash_free_sessions below threshold")
        if latency > policy.max_p95_latency_ms:
            reasons.append("p95 latency above threshold")
        checked.append({"window": idx, "pass": not reasons, "reasons": reasons, "sample": sample})
    consecutive = 0
    for row in reversed(checked):
        if row["pass"]:
            consecutive += 1
        else:
            break
    ok = consecutive >= policy.required_consecutive_windows
    return {
        "status": "pass" if ok else "fail",
        "policy": policy.to_dict(),
        "windows": checked,
        "consecutive_passing_windows": consecutive,
        "required_consecutive_windows": policy.required_consecutive_windows,
    }


class ReleaseController:
    """Durable release state machine with health-gated rollout and rollback.

    This controller never deploys by itself. It governs privileged executors and
    records enough state that a CI/CLI runtime can resume after process failure.
    """

    def __init__(self, root: Path, release_id: str):
        self.root = root.resolve()
        self.release_id = safe_identifier(release_id, label="release_id")
        self.path = self.root / ".factory" / "production" / "runs" / f"{self.release_id}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({
                "schema": "nakeuri/release-control/v1",
                "release_id": self.release_id,
                "state": "PREPARED",
                "created_at": _iso(),
                "updated_at": _iso(),
                "history": [{"at": _iso(), "state": "PREPARED", "event": "created"}],
                "proof_status": None,
                "human_production_approval": False,
                "health": {},
            })

    def _read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, Any]) -> None:
        fd, tmp = tempfile.mkstemp(prefix="release-", suffix=".json", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(tmp, self.path)
        finally:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass

    def status(self) -> dict[str, Any]:
        data = self._read()
        return {"status": "pass", **data, "path": str(self.path)}

    def set_proof(self, proof_status: str) -> dict[str, Any]:
        data = self._read()
        data["proof_status"] = proof_status
        data["updated_at"] = _iso()
        data["history"].append({"at": _iso(), "state": data["state"], "event": "proof", "proof_status": proof_status})
        self._write(data)
        return self.status()

    def approve_production(self, *, approved: bool, actor: str) -> dict[str, Any]:
        if not actor.strip():
            raise ValueError("approval actor required")
        data = self._read()
        data["human_production_approval"] = bool(approved)
        data["updated_at"] = _iso()
        data["history"].append({"at": _iso(), "state": data["state"], "event": "production_approval", "approved": bool(approved), "actor": actor})
        self._write(data)
        return self.status()

    def record_health(self, stage: str, evaluation: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        data.setdefault("health", {})[stage] = evaluation
        data["updated_at"] = _iso()
        data["history"].append({"at": _iso(), "state": data["state"], "event": "health", "stage": stage, "status": evaluation.get("status")})
        self._write(data)
        return self.status()

    def transition(self, target: str, *, reason: str = "") -> dict[str, Any]:
        target = target.upper()
        data = self._read()
        state = data["state"]
        if target not in STATES.get(state, set()):
            return {"status": "blocked", "reason": f"illegal release transition {state}->{target}", "state": state, "target": target}
        if target in {"STAGING", "CANARY", "PRODUCTION", "VERIFIED"} and data.get("proof_status") != "PASS":
            return {"status": "blocked", "reason": "PASS proof required before rollout progression", "state": state, "target": target}
        if target == "PRODUCTION":
            if not data.get("human_production_approval"):
                return {"status": "blocked", "reason": "explicit human production approval required", "state": state, "target": target}
            canary = data.get("health", {}).get("canary")
            if not isinstance(canary, dict) or canary.get("status") != "pass":
                return {"status": "blocked", "reason": "passing canary health evidence required", "state": state, "target": target}
        if target == "VERIFIED":
            production = data.get("health", {}).get("production")
            if not isinstance(production, dict) or production.get("status") != "pass":
                return {"status": "blocked", "reason": "passing production health evidence required", "state": state, "target": target}
        data["state"] = target
        data["updated_at"] = _iso()
        data["history"].append({"at": _iso(), "state": target, "event": "transition", "reason": reason})
        self._write(data)
        return self.status()
