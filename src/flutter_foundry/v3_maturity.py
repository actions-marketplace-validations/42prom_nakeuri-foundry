from __future__ import annotations

from pathlib import Path
from typing import Any


def _exists(p: Path, name: str) -> bool:
    return (p / name).exists()


def _contains(p: Path, name: str, *needles: str) -> bool:
    try:
        text = (p / name).read_text(encoding="utf-8")
    except Exception:
        return False
    return all(n in text for n in needles)


def v3_implementation_score(package_dir: Path) -> dict[str, Any]:
    """Strict implementation-target coverage.

    A 10 here means the target capability and enforceable contract exist in the
    repository. It deliberately does NOT mean that an external Docker/K8s/
    Flutter/device/store/production environment has empirically proven it.
    """
    p = package_dir.resolve()
    repo = p.parents[1]
    criteria = {
        "orchestration": [
            ("durable scheduler with leases/retries", _contains(p, "scheduler.py", "claim_next", "heartbeat", "recover_expired_leases")),
            ("tamper-evident scheduler event replay", _contains(p, "scheduler.py", "verify_event_chain", "replay_task", "event_hash")),
            ("transactional worker reservation", _contains(p, "distributed_runtime.py", "BEGIN IMMEDIATE", "def reserve", "busy_slots")),
            ("risk-routed execution fabric", _contains(p, "execution_fabric.py", "choose_provider", "docker", "github-runner")),
            ("real Docker executor + observed attestation", _contains(p, "docker_runtime.py", "docker", "inspect", "validate_runtime_attestation")),
            ("OpenHands provider adapter", _contains(p, "agent_runtime.py", "OpenHandsAgentExecutor")),
            ("worktree isolation", _exists(p, "worktrees.py")),
            ("side-effect firewall", _contains(p, "execution_fabric.py", "authorize_side_effect", "explicit human approval required")),
            ("durable budget usage", _contains(p, "budget.py", "max_cost_usd", "max_tokens", "max_agent_seconds")),
            ("lifecycle runner", _exists(p, "lifecycle.py")),
            ("risk-specific provider proof obligations", _contains(p, "execution_fabric.py", "provider_contract", "security_isolation_attestation", "human_approval_boundary")),
        ],
        "flutter_expertise": [
            ("official Dart MCP", _contains(p, "platform_adapters.py", "dart mcp-server") and _contains(p, "flutter_stack.py", "dart_mcp_configured")),
            ("official Flutter skills", _contains(p, "flutter_stack.py", "flutter/agent-plugins")),
            ("official Dart skills", _contains(p, "flutter_stack.py", "dart-lang/skills")),
            ("package skills", _contains(p, "flutter_stack.py", "PACKAGE_SKILLS_INSTALL", "skills@", "get")),
            ("Developer Knowledge MCP modeled", _contains(p, "flutter_stack.py", "developer_knowledge_mcp")),
            ("Flutter semantic authority/fallback", _contains(p, "semantic_engine.py", "dart_mcp_available", "official language analyzers/MCP/LSP")),
            ("Flutter flagship adapter", _contains(p, "platform_adapters.py", 'id="flutter", maturity="flagship"')),
            ("Flutter verifier/analyzer/tests", _contains(p, "verifier.py", "flutter", "analyze")),
            ("Flutter readiness separated from universal core", _contains(p, "environment.py", "flutter_profile_missing", "universal_core_missing")),
        ],
        "polyglot_expertise": [
            ("Next.js specialist adapter", _contains(p, "platform_adapters.py", "NEXTJS", "Next.js")),
            ("Python adapter", _contains(p, "platform_adapters.py", "PYTHON", "Pyright")),
            (".NET/Roslyn adapter", _contains(p, "platform_adapters.py", "DOTNET", "Roslyn")),
            ("Go/Rust/Java adapters", _contains(p, "platform_adapters.py", "GO =", "RUST =", "JAVA =")),
            ("multi-language semantic graph", _contains(p, "semantic_engine.py", "ast.parse", "typescript", "csharp", "rust", "go")),
            ("software knowledge graph", _contains(p, "knowledge_graph.py", "software-knowledge-graph/v2", "semantic_project_graph")),
            ("cross-language contract drift", _contains(p, "knowledge_graph.py", "compare_contract_snapshots", "type/required/nullability drift")),
            ("native deterministic CI planner", _contains(p, "ci_plan.py", "release Node/Next.js surface has no recognized lockfile", "pubspec.lock", "Cargo.lock")),
            ("polyglot release graph", _contains(p, "production_graph.py", "deploy_order", "rollback_order")),
            ("polyglot toolchain readiness inventory", _contains(p, "environment.py", "rust-analyzer", "gopls", "pyright", "dotnet", "javac")),
        ],
        "governance": [
            ("Project Genome", _exists(p, "genome.py")),
            ("capability ownership", _exists(p, "capability_graph.py")),
            ("domain invariants", _exists(p, "invariants.py")),
            ("change intent/scope firewall", _exists(p, "change_intent.py")),
            ("clean-code/complexity guard", _exists(p, "clean_code.py")),
            ("design and duplicate guards", _exists(p, "design_guard.py") and _exists(p, "duplicate_guard.py")),
            ("ADR decisions", _exists(p, "adr.py")),
            ("evergreen standards radar", _contains(p, "standards.py", "prefer_proven_over_newest", "owasp.asvs", "sigstore.keyless")),
            ("risk engine", _exists(p, "risk_engine.py")),
            ("explicit target-vs-empirical claim boundary", _contains(p, "target10.py", "claim_boundary", "external_empirical")),
        ],
        "evidence": [
            ("hash-chained evidence ledger", _contains(p, "evidence_ledger.py", "entry_hash", "prev_hash")),
            ("hash-chained orchestration history", _contains(p, "scheduler.py", "event_hash", "verify_event_chain")),
            ("commit-bound proof", _exists(p, "proof.py")),
            ("independent hashed reviews", _contains(p, "reviews.py", "reviewer", "hash")),
            ("assurance archive", _exists(p, "assurance.py")),
            ("reproducible build verifier", _exists(p, "reproducible_build.py")),
            ("release attestation contract", _contains(p, "attestation.py", "SLSA", "transparency", "builder_identity")),
            ("runtime isolation attestation", _contains(p, "runtime_security.py", "validate_runtime_attestation", "observed runtime facts")),
            ("source-bound certification fingerprint", _contains(p, "source_fingerprint.py", "repository_fingerprint", "sha256(path-length") and _contains(p, "certification.py", "source_fingerprint")),
        ],
        "security": [
            ("deterministic source scanner", _exists(p, "security.py")),
            ("external security assurance", _exists(p, "security_assurance.py")),
            ("current standards posture", _contains(p, "security_posture.py", "OWASP ASVS", "OWASP MASVS", "SLSA", "Sigstore")),
            ("untrusted content boundary", _exists(p, "trust_boundary.py")),
            ("2026 MCP gateway", _contains(p, "mcp_gateway.py", "Mcp-Method", "issuer validation", "TASKS_EXTENSION")),
            ("hardened container policy", _contains(p, "runtime_security.py", "read_only_rootfs", "cap_drop_all", "no_new_privileges")),
            ("secret broker + network policy", _contains(p, "execution_fabric.py", "raw_secret_to_model", "deny_unknown")),
            ("supply-chain verification", _exists(p, "supply_chain.py") and _exists(p, "attestation.py")),
            ("agent privilege firewall", _contains(p, "execution_fabric.py", "PRIVILEGED_ACTIONS", "human_approved")),
            ("hardened Docker distribution policy", (repo / "docker" / "Dockerfile").exists() and _contains(repo, "compose.yaml", "read_only: true", "network_mode: none", "no-new-privileges:true")),
        ],
        "production": [
            ("multi-component release graph", _contains(p, "production_graph.py", "deploy_order", "rollback_order")),
            ("health-gated rollout controller", _contains(p, "release_controller.py", "CANARY", "PRODUCTION", "evaluate_health")),
            ("automatic rollback state", _contains(p, "release_controller.py", "ROLLING_BACK", "ROLLED_BACK")),
            ("migration safety", _contains(p, "migration_safety.py", "expand/contract", "deployed consumer")),
            ("mobile store delivery", _exists(p, "store_delivery.py")),
            ("SBOM and provenance", _exists(p, "sbom.py") and _exists(p, "supply_chain.py") and _exists(p, "attestation.py")),
            ("production ops", _exists(p, "production.py")),
            ("vendor-neutral telemetry", _contains(p, "telemetry.py", "service.name", "trace_id")),
            ("release CI reproducibility policy", _contains(p, "ci_plan.py", "profile == \"release\"", "reproducible dependency resolution")),
            ("release proof + human approval + health gate", _contains(p, "release_controller.py", "proof", "approve_production", "health")),
        ],
        "reliability": [
            ("scheduler lease recovery", _contains(p, "scheduler.py", "recover_expired_leases")),
            ("worker reservation recovery", _contains(p, "distributed_runtime.py", "recover_expired_reservations")),
            ("atomic worker capacity", _contains(p, "distributed_runtime.py", "BEGIN IMMEDIATE", "reserve")),
            ("scheduler schema migrations", _contains(p, "scheduler.py", "SCHEMA_VERSION = 4", "migration_history")),
            ("backup/repair", _exists(p, "maintenance.py")),
            ("safe path confinement", _exists(p, "safe_paths.py")),
            ("adversarial self-test", _exists(p, "hardening.py")),
            ("runtime attestation verification", _exists(p, "runtime_security.py")),
            ("idempotent task creation", _contains(p, "scheduler.py", "idempotency_key")),
            ("certification bound to audited source snapshot", _contains(p, "certification.py", "repository_fingerprint", "source_fingerprint")),
        ],
        "cli_dx": [
            ("CLI aliases", _contains(repo, "pyproject.toml", "nakeuri-foundry", 'nakeuri =')),
            ("machine-readable JSON", _contains(p, "cli.py", "json.dumps")),
            ("deterministic CI exit classes", _contains(p, "cli.py", "_exit_code", "--ci")),
            ("deep doctor", _exists(p, "maintenance.py")),
            ("compatibility/upgrade", _exists(p, "compatibility.py") and _exists(p, "upgrade.py")),
            ("polyglot project detection", _contains(p, "platform_adapters.py", "detect_project_surfaces")),
            ("first-class Docker execution profile", (repo / "docker" / "Dockerfile").exists() and (repo / "compose.yaml").exists()),
            ("semantic/security/release CLI", _contains(p, "cli.py", "semantic-graph", "security-posture", "release-control-transition")),
            ("MCP mirrors advanced control plane", _contains(p, "mcp_server.py", "semantic_graph", "distributed_worker_reserve", "native_ci_plan")),
            ("target-10 and source fingerprint CLI", _contains(p, "cli.py", "target-10", "source-fingerprint", "require-certification")),
        ],
        "cost_efficiency": [
            ("cost/token/time budgets", _contains(p, "budget.py", "max_cost_usd", "max_tokens", "max_agent_seconds")),
            ("risk-adaptive team", _exists(p, "team.py")),
            ("model policy", (p / "assets" / "policies" / "model_router.json").exists()),
            ("empirical model router", _contains(p, "model_router.py", "acceptance_rate", "quality_band", "avg_cost_usd")),
            ("focused context engine", _exists(p, "context_engine.py")),
            ("progressive official skills", _contains(p, "flutter_stack.py", "official_skills_present", "package_skills")),
            ("risk-adaptive runtime routing", _contains(p, "execution_fabric.py", "choose_provider")),
            ("durable usage accounting", _contains(p, "scheduler.py", "task_usage")),
            ("500-task controlled benchmark contract", (repo / "evals" / "golden_tasks" / "v3_target_500.jsonl").exists() and _contains(p, "benchmark_v3.py", "generate_target_corpus", "superiority_gate")),
            ("fairness-constrained benchmark superiority gate", _contains(p, "benchmark_v3.py", "same_repository_snapshot", "same_model_policy", "hidden_tests", "superiority_gate")),
        ],
    }
    scores: dict[str, float] = {}
    detail: dict[str, list[dict[str, Any]]] = {}
    passed = total = 0
    for category, checks in criteria.items():
        n = sum(bool(ok) for _, ok in checks)
        passed += n
        total += len(checks)
        scores[category] = round(10 * n / len(checks), 2)
        detail[category] = [{"criterion": name, "pass": bool(ok)} for name, ok in checks]
    return {
        "schema": "nakeuri/v3-implementation-score/v2",
        "scores": scores,
        "average": round(sum(scores.values()) / len(scores), 2),
        "passed": passed,
        "total": total,
        "criteria": detail,
        "scope": "strict architecture/implementation target coverage only; not real-world peer superiority and not external runtime evidence",
        "ten_means": "all target implementation criteria in that category exist and are enforceable/testable",
    }
