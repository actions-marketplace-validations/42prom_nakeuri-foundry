from __future__ import annotations

from pathlib import Path
from typing import Any

from .benchmark_v3 import validate_target_corpus
from .distributed_runtime import WorkerRegistry
from .environment import environment_status
from .hardening import adversarial_self_test
from .polyglot_smoke import run_polyglot_smoke
from .reproducible_build import reproducible_build_check
from .scheduler import Scheduler
from .security_posture import security_posture
from .v3_maturity import v3_implementation_score
from .source_fingerprint import repository_fingerprint


def _pass(value: Any) -> bool:
    return isinstance(value, dict) and value.get("status") == "pass"



def _docker_assets_hardened(root: Path) -> bool:
    try:
        dockerfile = (root / "docker" / "Dockerfile").read_text(encoding="utf-8")
        compose = (root / "compose.yaml").read_text(encoding="utf-8")
    except Exception:
        return False
    required_dockerfile = ("ARG NAKEURI_BASE_IMAGE", "FROM ${NAKEURI_BASE_IMAGE}", "USER 65532:65532")
    required_compose = ("read_only: true", "no-new-privileges:true", "cap_drop:", "network_mode: none", "pids_limit:")
    cap_drop_all = "cap_drop: [\"ALL\"]" in compose or "- ALL" in compose
    floating_default = "ARG NAKEURI_BASE_IMAGE=" in dockerfile
    return all(x in dockerfile for x in required_dockerfile) and all(x in compose for x in required_compose) and cap_drop_all and not floating_default


def _certification_binding(root: Path) -> dict[str, Any]:
    path = root / ".factory" / "certification" / "latest.json"
    if not path.exists():
        return {"status": "missing", "path": str(path)}
    try:
        import json
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "fail", "reason": str(exc), "path": str(path)}
    current = repository_fingerprint(root)
    certified = (report.get("source_fingerprint") or {}).get("sha256")
    return {
        "status": "pass" if report.get("status") == "pass" and certified == current["sha256"] else "stale",
        "path": str(path),
        "certification_status": report.get("status"),
        "certified_sha256": certified,
        "current_sha256": current["sha256"],
    }

def target10_gate(
    root: Path,
    *,
    run_reproducible_build: bool = False,
    probe_docker: bool = False,
    require_certification: bool = False,
) -> dict[str, Any]:
    """Evaluate the V3 10/10 *implementation target* without inflating empirical claims.

    This gate is intentionally two-layered:
    - target implementation: repository-owned capabilities and deterministic contracts;
    - external empirical readiness: live tools/environments needed to prove peer superiority.

    A PASS here means the implementation target is complete and locally hardening-clean.
    It never means that OpenHands/Official Flutter or any other peer has been beaten in a
    controlled external benchmark.
    """
    root = root.resolve()
    package = root / "src" / "flutter_foundry"
    implementation = v3_implementation_score(package)
    scheduler = Scheduler(root)
    workers = WorkerRegistry(root)
    benchmark = validate_target_corpus(root / "evals" / "golden_tasks" / "v3_target_500.jsonl")
    hardening = adversarial_self_test()
    polyglot = run_polyglot_smoke()
    security = security_posture(root, release=True)
    environment = environment_status(root, probe_docker=probe_docker)
    certification_binding = _certification_binding(root)
    reproducible = (
        reproducible_build_check(root, install_smoke=True)
        if run_reproducible_build
        else {"status": "not_run", "rule": "Run with --reproducible-build for release-candidate certification."}
    )

    target_checks = {
        "implementation_10x10": implementation.get("average") == 10.0
        and all(v == 10.0 for v in implementation.get("scores", {}).values()),
        "implementation_criteria": implementation.get("passed") == implementation.get("total") and implementation.get("total", 0) >= 80,
        "scheduler_schema": _pass(scheduler.schema_status()),
        "scheduler_integrity": _pass(scheduler.integrity_check()),
        "scheduler_event_chain": _pass(scheduler.verify_event_chain()),
        "worker_registry": _pass(workers.schema_status()),
        "adversarial_hardening": _pass(hardening),
        "polyglot_smoke": _pass(polyglot),
        "benchmark_protocol": _pass(benchmark) and benchmark.get("count", 0) >= 500,
        "docker_hardened_profile": _docker_assets_hardened(root),
        "reproducible_build": reproducible.get("status") in {"pass", "not_run"},
    }
    if require_certification:
        target_checks["certification_current"] = certification_binding.get("status") == "pass"
    failed_target = [name for name, ok in target_checks.items() if not ok]

    # External empirical gates are deliberately not converted into target failures.
    # They are the proof required for a future market/peer-superiority claim.
    tools = environment.get("tools", {})
    packages = environment.get("packages", {})
    docker = environment.get("docker", {})
    readiness = {
        "flutter_cli_available": bool(tools.get("flutter", {}).get("available")),
        "dart_cli_and_mcp_sdk_available": bool(tools.get("dart", {}).get("available")) and bool(packages.get("mcp")),
        "openhands_sdk_available": bool(packages.get("openhands_sdk")),
        "docker_daemon_responding": docker.get("daemon") is True,
        "kubectl_available": bool(tools.get("kubectl", {}).get("available")),
        "adb_available": bool(tools.get("adb", {}).get("available")),
        "ios_host_ready": bool(environment.get("ios_host_ready")),
        "release_security_tools_available": security.get("status") == "pass",
    }
    # Executable presence is readiness, not runtime evidence. These gates stay false
    # until a source-bound external run manifest/attestation is ingested and verified.
    external = {
        "live_flutter_sdk": False,
        "live_dart_mcp_runtime": False,
        "live_openhands_runtime": False,
        "live_docker_daemon": False,
        "live_kubernetes_runtime": False,
        "android_device_runtime": False,
        "ios_xcode_runtime": False,
        "release_security_toolchain": False,
        "external_signed_release_attestation": False,
        "real_store_delivery": False,
        "production_rollout_and_rollback_drill": False,
        "controlled_peer_benchmark_completed": False,
    }
    external_gaps = [name for name, ok in external.items() if not ok]

    return {
        "schema": "nakeuri-foundry/target-10/v1",
        "status": "pass" if not failed_target else "fail",
        "target": 10.0,
        "implementation": implementation,
        "target_checks": target_checks,
        "failed_target_checks": failed_target,
        "benchmark": benchmark,
        "hardening": hardening,
        "polyglot_smoke": polyglot,
        "security_posture": security,
        "reproducible_build": reproducible,
        "certification_binding": certification_binding,
        "external_empirical": {
            "status": "proven" if not external_gaps else "not_yet_proven",
            "checks": external,
            "environment_readiness": readiness,
            "gaps": external_gaps,
            "rule": "Tool availability is reported as readiness only and never promoted to empirical runtime proof.",
        },
        "claim_boundary": (
            "PASS means the repository retains the defined V3 Target-10 implementation target across all ten categories "
            "and passes its local deterministic hardening gates. It is not evidence of real-world superiority over peers. "
            "That claim requires the external empirical gates and controlled head-to-head benchmark to pass."
        ),
    }
