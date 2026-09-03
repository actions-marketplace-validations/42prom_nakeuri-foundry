from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .environment import environment_status
from .hardening import adversarial_self_test
from .maturity import implementation_coverage
from .v3_maturity import v3_implementation_score
from .source_fingerprint import repository_fingerprint
from .polyglot_smoke import run_polyglot_smoke
from .reproducible_build import reproducible_build_check
from .scheduler import Scheduler
from .distributed_runtime import WorkerRegistry
from .benchmark_v3 import validate_target_corpus
from .security_posture import security_posture
from .v4_maturity import v4_hardening_score
from .v5_maturity import v5_flagship_score


def _run(root: Path, name: str, cmd: list[str], timeout: int = 180) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=timeout)
        return {"name": name, "status": "pass" if p.returncode == 0 else "fail", "returncode": p.returncode, "command": cmd, "output": ((p.stdout or "") + "\n" + (p.stderr or ""))[-6000:]}
    except Exception as exc:
        return {"name": name, "status": "fail", "command": cmd, "reason": str(exc)}


def certify_repository(
    root: Path,
    include_tests: bool = True,
    probe_docker: bool = False,
    include_reproducible_build: bool = False,
) -> dict[str, Any]:
    root = root.resolve(); package = root / "src" / "flutter_foundry"
    source_fingerprint = repository_fingerprint(root)
    checks = [
        _run(root, "self_audit", ["python", "scripts/self_audit.py"]),
        _run(root, "repo_policy", ["python", "scripts/check_repo_policy.py"]),
        _run(root, "github_action_pins", ["python", "scripts/check_actions_pinned.py"]),
        _run(root, "compileall", ["python", "-m", "compileall", "-q", "src"]),
    ]
    if include_tests:
        checks.append(_run(root, "unit_tests", ["python", "-m", "unittest", "discover", "-s", "tests", "-v"], 300))
    scheduler = Scheduler(root)
    scheduler_schema = scheduler.schema_status()
    scheduler_integrity = scheduler.integrity_check()
    scheduler_events = scheduler.verify_event_chain()
    worker_registry = WorkerRegistry(root).schema_status()
    benchmark_corpus = validate_target_corpus(root / "evals" / "golden_tasks" / "v3_target_500.jsonl")
    security_model = security_posture(root, release=True)
    hardening = adversarial_self_test()
    reproducible = reproducible_build_check(root) if include_reproducible_build else {"status": "not_run"}
    coverage = implementation_coverage(package)
    v3_coverage = v3_implementation_score(package)
    v4_coverage = v4_hardening_score(package)
    v5_coverage = v5_flagship_score(package)
    polyglot_smoke = run_polyglot_smoke()
    env = environment_status(root, probe_docker=probe_docker)
    blocking = [c["name"] for c in checks if c.get("status") != "pass"]
    if scheduler_schema.get("status") != "pass": blocking.append("scheduler_schema")
    if scheduler_integrity.get("status") != "pass": blocking.append("scheduler_integrity")
    if scheduler_events.get("status") != "pass": blocking.append("scheduler_event_chain")
    if worker_registry.get("status") != "pass": blocking.append("worker_registry")
    if benchmark_corpus.get("status") != "pass": blocking.append("benchmark_corpus")
    if hardening.get("status") != "pass": blocking.append("adversarial_self_test")
    if polyglot_smoke.get("status") != "pass": blocking.append("polyglot_smoke")
    if include_reproducible_build and reproducible.get("status") != "pass": blocking.append("reproducible_build")
    report = {
        "schema": "nakeuri-foundry/certification/v5",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_fingerprint": source_fingerprint,
        "status": "fail" if blocking else "pass",
        "blocking": blocking,
        "checks": checks,
        "scheduler": {"schema": scheduler_schema, "integrity": scheduler_integrity, "event_chain": scheduler_events},
        "worker_registry": worker_registry,
        "benchmark_corpus": benchmark_corpus,
        "security_posture": security_model,
        "adversarial": hardening,
        "reproducible_build": reproducible,
        "implementation": coverage,
        "v3_implementation": v3_coverage,
        "v4_hardening": v4_coverage,
        "v5_flagship": v5_coverage,
        "polyglot_smoke": polyglot_smoke,
        "environment": env,
        "statement": "PASS certifies deterministic local repository contracts for the retained V3 target, V4 execution/intelligence hardening, V5 flagship-proof implementation, the 500-scenario benchmark structure, tamper-evident orchestration, transactional worker placement and polyglot control-plane tests on this host. It does not convert unavailable live Antigravity/Docker/Kubernetes/Flutter/device/store/security/signing/head-to-head execution into empirical proof.",
    }
    out = root / ".factory" / "certification" / "latest.json"; out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["report_path"] = str(out)
    return report
