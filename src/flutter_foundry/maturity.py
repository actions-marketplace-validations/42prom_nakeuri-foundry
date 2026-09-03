from __future__ import annotations

from pathlib import Path
from typing import Any


def _contains(path: Path, *needles: str) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return False
    return all(n in text for n in needles)


def _exists(package_dir: Path, name: str) -> bool:
    return (package_dir / name).is_file()


def _implementation_criteria(package_dir: Path) -> dict[str, list[tuple[str, bool]]]:
    a = package_dir / "assets" / "github"
    plugin_mcp = package_dir / "assets" / "plugin" / "mcp_config.json"
    return {
        "orchestration": [
            ("durable SQLite scheduler", _contains(package_dir / "scheduler.py", "sqlite3", "scheduler.db")),
            ("task dependency DAG", _contains(package_dir / "scheduler.py", "CREATE TABLE IF NOT EXISTS deps", "unmet dependencies")),
            ("lease + heartbeat recovery", _contains(package_dir / "scheduler.py", "lease_until", "heartbeat", "claim_next")),
            ("retry + cost/token/time budget", _contains(package_dir / "scheduler.py", "max_attempts", "task_usage") and _contains(package_dir / "budget.py", "max_cost_usd", "max_tokens", "max_agent_seconds")),
            ("isolated Git worktrees", _contains(package_dir / "worktrees.py", "git", "worktree", "require_clean")),
            ("worker commit contract", _contains(package_dir / "worktrees.py", "require_worker_commit", "worker produced no commit")),
            ("end-to-end lifecycle runner", _contains(package_dir / "lifecycle.py", "class LifecycleRunner", "finish_attempt", "build_proof", "MERGEABLE")),
            ("OpenHands SDK executor adapter", _contains(package_dir / "agent_runtime.py", "OpenHandsAgentExecutor", "Conversation", "TerminalTool")),
            ("risk-adaptive team roles", _contains(package_dir / "team.py", "security-reviewer", "human_merge_required")),
            ("independent merge arbiter + human gate", _contains(package_dir / "merge_arbiter.py", "human_approved", "HIGH", "RELEASE")),
            ("scheduler schema migrations + recovery", _contains(package_dir / "scheduler.py", "SCHEMA_VERSION", "migration_history", "recover_expired_leases")),
            ("idempotent task creation", _contains(package_dir / "scheduler.py", "idempotency_key", "idx_tasks_idempotency")),
        ],
        "flutter_expertise": [
            ("official Dart MCP configured", _contains(plugin_mcp, '"dart"', '"mcp-server"')),
            ("official Flutter Agent Skills installer", _contains(package_dir / "flutter_stack.py", "flutter/agent-plugins", "npx", "skills")),
            ("official Dart Agent Skills installer", _contains(package_dir / "flutter_stack.py", "dart-lang/skills")),
            ("skill integrity lock", _contains(package_dir / "flutter_stack.py", "skills-lock.json", "sha256")),
            ("Flutter platform adapter", _contains(package_dir / "platform_adapters.py", "Flutter", "pubspec.yaml")),
            ("Dart-MCP semantic snapshot ingestion", _contains(package_dir / "semantic_snapshot.py", "semantic", "definitions", "references")),
            ("monorepo-aware Flutter verifier", _contains(package_dir / "verifier.py", "mobile", "pubspec.yaml", "flutter_root")),
            ("Android release workflow", (a / "release-gate.yml").is_file() and _contains(a / "release-gate.yml", "--ci", "verify . --profile release") and _contains(package_dir / "verifier.py", "android_release_build", "appbundle")),
            ("Android emulator E2E workflow", (a / "flutter-e2e.yml").is_file() and _contains(a / "flutter-e2e.yml", "integration_test", "emulator")),
            ("iOS release compile workflow", (a / "ios-compile.yml").is_file() and _contains(a / "ios-compile.yml", "flutter build ios", "--no-codesign")),
        ],
        "governance": [
            ("Project Genome", _exists(package_dir, "genome.py")),
            ("capability ownership graph", _exists(package_dir, "capability_graph.py")),
            ("domain invariant registry", _exists(package_dir, "invariants.py")),
            ("change-intent scope guard", _exists(package_dir, "change_intent.py")),
            ("component compatibility solver", _exists(package_dir, "component_solver.py")),
            ("clean-code/simplicity guard", _exists(package_dir, "clean_code.py")),
            ("design consistency guard", _exists(package_dir, "design_guard.py")),
            ("duplicate capability guard", _exists(package_dir, "duplicate_guard.py")),
            ("deterministic aggregate gate", _exists(package_dir, "gate.py")),
            ("architecture decision records", _exists(package_dir, "adr.py")),
            ("strict agent output protocol", _contains(package_dir / "agent_protocol.py", "REVIEW_SCHEMA", "unknown fields")),
            ("untrusted-content boundary", _contains(package_dir / "trust_boundary.py", "UNTRUSTED_CONTENT", "instruction_authority")),
        ],
        "evidence": [
            ("commit-bound evidence records", _contains(package_dir / "evidence.py", "commit", "sha256_file")),
            ("append-only hash-chained ledger", _contains(package_dir / "evidence_ledger.py", "prev_hash", "entry_hash")),
            ("strict Proof Bundle v3", _contains(package_dir / "proof.py", "proof/v3", "STRICT_RISKS")),
            ("independent hashed review artifacts", _contains(package_dir / "reviews.py", "writer cannot independently review", "sha256")),
            ("portable assurance archive v2", _contains(package_dir / "assurance.py", "assurance-archive/v2", "verify_assurance_archive")),
            ("evidence-backed release scoring", _exists(package_dir, "score.py")),
            ("benchmark comparison protocol", _contains(package_dir / "benchmark.py", "compare_runs", "first_pass")),
            ("artifact tamper validation", _contains(package_dir / "proof.py", "artifact hash mismatch")),
            ("review commit binding", _contains(package_dir / "reviews.py", "expected_commit", "wrong commit")),
            ("strict high/release verification rule", _contains(package_dir / "proof.py", "HIGH/RELEASE proof requires verification status PASS")),
            ("ledger anchoring receipt", _contains(package_dir / "evidence_ledger.py", "evidence-anchor/v1", "ledger_head")),
            ("repository-local artifact path confinement", _contains(package_dir / "safe_paths.py", "path escapes repository root", "absolute path is not allowed")),
        ],
        "production_maturity": [
            ("GitHub delivery plane", _exists(package_dir, "delivery.py")),
            ("production operations contract", _contains(package_dir / "production.py", "staged", "rollback", "incident")),
            ("Google Play/TestFlight delivery contract", _contains(package_dir / "store_delivery.py", "supply", "pilot", "explicit approval")),
            ("supply-chain scanner", _exists(package_dir, "supply_chain.py")),
            ("external security assurance bridge", _contains(package_dir / "security_assurance.py", "gitleaks", "osv-scanner", "pass_with_gaps")),
            ("release verifier", _contains(package_dir / "verifier.py", "profile=='release'", "android_release_build", "ios_release_build")),
            ("release SBOM/dependency artifact", _contains(a / "release-gate.yml", "Generate CycloneDX SBOM", "sbom.cdx.json")),
            ("GitHub provenance attestation", _contains(a / "release-gate.yml", "actions/attest@", "subject-path")),
            ("immutable GitHub Action refs", _contains(a / "release-gate.yml", "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a")),
            ("real-device/E2E assurance path", _contains(a / "flutter-e2e.yml", "flutter test integration_test", "android-35")),
            ("reproducible wheel + clean install smoke", _contains(package_dir / "reproducible_build.py", "SOURCE_DATE_EPOCH", "force-reinstall")),
            ("safe upgrade/backup/repair path", _exists(package_dir, "upgrade.py") and _exists(package_dir, "maintenance.py")),
            ("toolchain compatibility contract", _exists(package_dir, "compatibility.py")),
        ],
    }


def implementation_coverage(package_dir: Path) -> dict[str, Any]:
    """Measure implemented capability contracts, not external/empirical maturity.

    This score deliberately cannot prove production quality. It only answers whether
    the concrete implementation surfaces required by the V2 design are present.
    """

    package_dir = package_dir.resolve(); criteria = _implementation_criteria(package_dir)
    scores: dict[str, float] = {}; detail: dict[str, list[dict[str, Any]]] = {}
    total_pass = total = 0
    for category, checks in criteria.items():
        passed = sum(1 for _, ok in checks if ok); total_pass += passed; total += len(checks)
        scores[category] = round(10 * passed / len(checks), 1)
        detail[category] = [{"criterion": name, "pass": bool(ok)} for name, ok in checks]
    return {
        "scores": scores,
        "average": round(sum(scores.values()) / len(scores), 2),
        "passed": total_pass,
        "total": total,
        "criteria": detail,
        "scope": "implementation capability only; not empirical maturity",
    }


def empirical_ceiling(environment: dict[str, bool]) -> dict[str, Any]:
    """Conservative maturity ceiling from evidence-capable environment, not feature presence."""
    required={
      "orchestration":["git","durable_scheduler","isolated_runtime","real_agent_execution","crash_recovery"],
      "flutter_expertise":["flutter_sdk","dart_mcp","official_flutter_skills","android_runtime","ios_runtime"],
      "governance":["deterministic_gates","adversarial_tests","real_project_duplicate_prevention","design_regression"],
      "evidence":["proof_validation","artifact_hashing","independent_review","assurance_archive","benchmark_reproducibility"],
      "production_maturity":["android_release","ios_release","real_device_e2e","store_delivery","production_observability","rollback_drill"],
    }
    scores={};gaps={}
    for category,keys in required.items():
        ok=[k for k in keys if environment.get(k,False)]; gaps[category]=[k for k in keys if k not in ok]
        scores[category]=round(10*len(ok)/len(keys),1)
    return {"scores":scores,"gaps":gaps,"average":round(sum(scores.values())/len(scores),2),"rule":"No environment evidence => no maturity credit."}
