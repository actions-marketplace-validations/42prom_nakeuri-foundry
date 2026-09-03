from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .compatibility import compatibility_status
from .environment import environment_status
from .evidence_ledger import EvidenceLedger
from .scheduler import Scheduler


def deep_doctor(root: Path, probe_docker: bool = False) -> dict[str, Any]:
    root = root.resolve()
    scheduler = Scheduler(root)
    ledger = EvidenceLedger(root)
    checks = {
        "environment": environment_status(root, probe_docker=probe_docker),
        "compatibility": compatibility_status(root),
        "scheduler_schema": scheduler.schema_status(),
        "scheduler_integrity": scheduler.integrity_check(),
        "evidence_ledger": ledger.verify(),
    }
    blockers = []
    if checks["scheduler_schema"].get("status") != "pass": blockers.append("scheduler_schema")
    if checks["scheduler_integrity"].get("status") != "pass": blockers.append("scheduler_integrity")
    if checks["evidence_ledger"].get("status") != "pass": blockers.append("evidence_ledger")
    if checks["compatibility"].get("status") == "unsupported": blockers.append("compatibility")
    return {
        "schema": "nakeuri/deep-doctor/v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "fail" if blockers else "pass_with_gaps" if checks["environment"].get("status") != "ready" or checks["compatibility"].get("status") != "supported" else "pass",
        "blocking": blockers,
        "checks": checks,
    }


def backup_runtime(root: Path) -> dict[str, Any]:
    root = root.resolve(); stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = root / ".factory" / "backups" / f"runtime-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    copied = []
    scheduler = Scheduler(root).backup(out / "scheduler.db")
    copied.append("scheduler.db")
    for rel in [".factory/evidence", ".factory/proofs", ".factory/reviews", ".factory/assurance"]:
        src = root / rel
        if src.exists():
            dst = out / Path(rel).name
            if dst.exists(): shutil.rmtree(dst)
            shutil.copytree(src, dst)
            copied.append(Path(rel).name)
    manifest = {"schema": "nakeuri/runtime-backup/v1", "created_at": stamp, "copied": copied, "scheduler": scheduler}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "pass", "path": str(out), "manifest": manifest}


def repair_runtime(root: Path) -> dict[str, Any]:
    root = root.resolve()
    before = deep_doctor(root)
    scheduler = Scheduler(root).repair(backup_first=True)
    after = deep_doctor(root)
    return {"status": "pass" if not after.get("blocking") else "fail", "before": before, "scheduler_repair": scheduler, "after": after}
