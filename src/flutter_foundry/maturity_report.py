from __future__ import annotations

from pathlib import Path
from typing import Any

from .environment import environment_status
from .target10 import target10_gate


def _ratio(*values: bool) -> float:
    if not values:
        return 0.0
    return round(10.0 * sum(bool(v) for v in values) / len(values), 1)


def maturity_report(root: Path, *, run_reproducible_build: bool = False, probe_docker: bool = False) -> dict[str, Any]:
    """Three-layer maturity report.

    1. target_implementation: repository-owned implementation/hardening target.
    2. host_readiness: whether this host can execute the major live toolchains.
    3. external_empirical: evidence needed before a peer-superiority claim.

    The three layers must never be collapsed into a marketing score.
    """
    root = root.resolve()
    target = target10_gate(root, run_reproducible_build=run_reproducible_build, probe_docker=probe_docker)
    env = environment_status(root, probe_docker=probe_docker)
    tools = env.get("tools", {})
    packages = env.get("packages", {})
    available = lambda name: bool(tools.get(name, {}).get("available"))

    host_scores = {
        "orchestration": _ratio(available("git"), env.get("docker", {}).get("daemon") is True, bool(packages.get("openhands_sdk")), available("kubectl")),
        "flutter_expertise": _ratio(available("dart"), available("flutter"), bool(packages.get("mcp")), available("adb"), bool(env.get("ios_host_ready"))),
        "polyglot_expertise": _ratio(available("node"), available("npx"), available("dotnet"), available("go"), available("rustc"), available("java")),
        "governance": 10.0 if target.get("status") == "pass" else 0.0,
        "evidence": _ratio(target.get("target_checks", {}).get("scheduler_event_chain", False), target.get("target_checks", {}).get("reproducible_build", False), available("cosign")),
        "security": _ratio(available("gitleaks"), available("osv-scanner"), available("semgrep"), available("trivy"), available("cosign")),
        "production": _ratio(available("docker"), available("kubectl"), available("fastlane"), available("xcodebuild"), available("adb")),
        "reliability": 10.0 if all(target.get("target_checks", {}).get(k, False) for k in ("scheduler_integrity", "scheduler_event_chain", "worker_registry", "adversarial_hardening")) else 0.0,
        "cli_dx": _ratio(available("git"), True),
        "cost_efficiency": 10.0 if target.get("implementation", {}).get("scores", {}).get("cost_efficiency") == 10.0 else 0.0,
    }

    empirical = target.get("external_empirical", {})
    return {
        "schema": "nakeuri/maturity-report/v2",
        "target_implementation": {
            "status": target.get("status"),
            "scores": target.get("implementation", {}).get("scores", {}),
            "average": target.get("implementation", {}).get("average"),
            "criteria": {"passed": target.get("implementation", {}).get("passed"), "total": target.get("implementation", {}).get("total")},
        },
        "host_readiness": {
            "scores": host_scores,
            "average": round(sum(host_scores.values()) / len(host_scores), 2),
            "scope": "tool/runtime availability on this host; availability is not successful execution evidence",
        },
        "external_empirical": empirical,
        "environment": env,
        "claim_boundary": "A 10.0 target implementation score is an engineering-completeness target. Peer superiority requires real controlled benchmark, live runtime/device/store/production evidence, and external attestation.",
    }
