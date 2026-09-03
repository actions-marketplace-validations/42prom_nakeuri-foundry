from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED = {
    "rollout": ["strategy", "initial_percentage", "health_window_minutes"],
    "health": ["crash_signal", "api_signal"],
    "rollback": ["strategy", "owner"],
    "incident": ["runbook", "escalation_owner"],
}
PLACEHOLDERS = {"", "FILL_ME", "TODO", "TBD", "OWNER_PLACEHOLDER", "https://example.invalid"}


def init_production_ops(root: Path, force: bool = False) -> Path:
    p = root.resolve() / ".factory" / "production.json"
    if p.exists() and not force: return p
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "foundry/production-ops/v1",
        "rollout": {"strategy": "staged", "initial_percentage": 5, "health_window_minutes": 60},
        "health": {"crash_signal": "FILL_ME", "api_signal": "FILL_ME"},
        "rollback": {"strategy": "FILL_ME", "owner": "FILL_ME", "kill_switch": "FILL_ME"},
        "incident": {"runbook": "FILL_ME", "escalation_owner": "FILL_ME"},
        "migration": {"backward_compatible": None, "rollback_tested": False},
    }
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def validate_production_ops(root: Path) -> dict[str, Any]:
    p = root.resolve() / ".factory" / "production.json"
    if not p.exists(): return {"status": "fail", "findings": ["production ops contract missing"]}
    try: data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e: return {"status": "fail", "findings": [f"invalid production contract: {e}"]}
    findings = []
    if data.get("schema") != "foundry/production-ops/v1": findings.append("unsupported production contract schema")
    for section, fields in REQUIRED.items():
        obj = data.get(section, {})
        for field in fields:
            value = obj.get(field)
            if value is None or str(value).strip() in PLACEHOLDERS: findings.append(f"{section}.{field} is not configured")
    migration = data.get("migration", {})
    if migration.get("backward_compatible") is None: findings.append("migration.backward_compatible is undecided")
    if migration.get("backward_compatible") is False and not migration.get("rollback_tested"): findings.append("non-backward-compatible migration requires tested rollback")
    return {"status": "fail" if findings else "pass", "findings": findings, "path": str(p)}
