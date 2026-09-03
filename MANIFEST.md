# Nakeuri Foundry — Repository Manifest

**Build metadata:** `5.0.0a1`

**Public product:** **Nakeuri Foundry**

**Default profile:** Flutter flagship
**License:** Apache-2.0

## Identity

- Repository: `nakeuri-foundry`
- Python distribution: `nakeuri-foundry`
- Python import package: `flutter_foundry` (compatibility/internal namespace)
- Primary CLI: `nakeuri`
- Compatibility CLI aliases: `nakeuri-foundry`, `flutter-foundry`
- MCP command: `flutter-foundry-mcp`

## Core modules

- `specification.py` — executable requirements, NFR, negative-case and acceptance-oracle compiler
- `standards.py` — evergreen standards radar
- `platform_adapters.py` — stack/language specialist adapters
- `semantic_engine.py` / `lsp_semantics.py` — native-first semantic graph and LSP queries
- `flutter_intelligence.py` — Flutter state/navigation/platform specialist layer
- `knowledge_graph.py` — software/product graph and cross-stack contract drift
- `scheduler.py` — durable DAG, leases, fencing, heartbeat and dependency reconciliation
- `lifecycle.py` — risk-aware end-to-end engineering lifecycle
- `execution_fabric.py` / `runtime_provider.py` — provider selection and unified runtime contract
- `antigravity_native.py` — native Antigravity specialist agents and validation
- `agent_runtime.py` — OpenHands execution adapter
- `docker_runtime.py` / `runtime_security.py` — hardened Docker execution
- `native_e2e.py` — Patrol/native Flutter E2E evidence
- `reviews.py` / `verifier.py` — independent review and verification
- `evidence_ledger.py` / `proof.py` — tamper-evident evidence and source-bound proof
- `mcp_gateway.py` — MCP security/compatibility gateway
- `security_posture.py` / `security_assurance.py` — security controls and release-security posture
- `production_graph.py` / `migration_safety.py` — deployment order and migration compatibility
- `release_controller.py` — approval/health-gated rollout and rollback state machine
- `attestation.py` / `sbom.py` — provenance/SBOM/signing contracts
- `telemetry.py` — vendor-neutral operational telemetry
- `defense_memory.py` — verified defect → durable defense promotion
- `empirical_benchmark.py` — fresh-clone hidden-test empirical comparison and ablation
- `model_router.py` — evidence/cost/risk-aware model routing
- `certification.py` / `source_fingerprint.py` — source-bound repository certification

## Specialist surfaces

- Flutter / Dart — flagship
- Next.js / TypeScript / Node.js
- Python
- .NET / C#
- Go
- Rust
- Java
- database/schema and migration contracts
- Docker/Kubernetes/CI/release surfaces

## Public documentation

- `README.md`
- `START_HERE.md`
- `SECURITY.md`
- `docs/ARCHITECTURE.md`
- `docs/V5_FLAGSHIP_PROOF.md`
- `docs/V5_EMPIRICAL_BENCHMARK.md`
- `docs/BENCHMARK_METHODOLOGY.md`
- `docs/AUDIT_2026-09-03.md`
- `docs/SECURITY_ARCHITECTURE.md`
- `docs/EVIDENCE_LEDGER.md`
- `docs/FULL_LIFECYCLE.md`

Historical internal milestones remain under `docs/history/` and selected legacy filenames for compatibility/audit lineage. They are not the public product name.

## Claim boundary

The repository contains implementation checks, local simulations and stress paths. Those do not replace real Docker/Antigravity/OpenHands/Kubernetes runs, installed language servers, Flutter device/store evidence, external security/signing infrastructure or a controlled hidden-test head-to-head benchmark.
