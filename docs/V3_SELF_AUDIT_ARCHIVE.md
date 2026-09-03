# Nakeuri Flutter Foundry 3.0.0b1 — V3 Target-10 Self-Audit

## Verdict

V3 now reaches the repository-defined **10.0 implementation target in all ten modeled categories**. This is backed by strict implementation criteria plus deterministic local hardening. It is deliberately **not** a claim that Nakeuri has already beaten OpenHands, Official Flutter AI, or another peer in real production.

The product remains **Nakeuri Flutter Foundry**, backed by the universal **Nakeuri Engineering Foundry Core**.

## Executed validation on this build host

- Python unit/integration suite: **138 / 138 PASS**
- V3 target implementation criteria: **99 / 99 PASS**
- Target categories: **10 / 10 at 10.0**
- Adversarial self-test: **19 / 19 PASS**
- Polyglot full-control-plane smoke: **10 / 10 PASS**
- Controlled benchmark protocol corpus: **500 scenarios PASS** across 20 categories, 13 stack shapes and all four risk levels
- Python compile: **PASS**
- Repository governance audit: **PASS**
- GitHub Action immutability audit: **19 / 19 references pinned to full SHAs**
- Reproducible wheel build: **PASS**
- Two independent wheel builds produced identical SHA-256: **PASS**
- Clean isolated wheel install/version probe: **PASS** (`3.0.0b1`)
- Tamper-evident scheduler event chain: **PASS**
- Transactional worker registry / atomic capacity reservation: **PASS**
- Source-snapshot fingerprinting for certification: **implemented and tested**
- Source-bound repository certification v4: **PASS**, zero blocking findings

## Ten-category target implementation result

| Category | Target implementation |
|---|---:|
| Orchestration | **10.0 / 10.0** |
| Flutter expertise integration | **10.0 / 10.0** |
| Polyglot expertise | **10.0 / 10.0** |
| Governance | **10.0 / 10.0** |
| Evidence | **10.0 / 10.0** |
| Security | **10.0 / 10.0** |
| Production architecture | **10.0 / 10.0** |
| Reliability | **10.0 / 10.0** |
| CLI / developer experience | **10.0 / 10.0** |
| Cost efficiency | **10.0 / 10.0** |

`nakeuri target-10` enforces the separation between this implementation target and external empirical proof.

## Candid practical maturity assessment

The table above is repository-defined implementation coverage. A stricter engineering review of the actual wiring gives a lower practical score today:

| Dimension | Current practical estimate | Why it is not 10 yet |
|---|---:|---|
| Orchestration | **8.4 / 10** | Durable scheduler/worktrees/proofs are real, but CLI lifecycle is currently wired directly to the OpenHands executor rather than one end-to-end provider-neutral Docker/OpenHands/remote/Kubernetes executor. |
| Flutter engineering | **8.9 / 10** | Official Flutter/Dart skills and Dart MCP are composed correctly, but live Dart/Flutter MCP and device execution were not available on this build host. |
| Polyglot engineering | **7.8 / 10** | Adapter contracts are broad; Python has AST semantics, while several other language graphs still rely on portable fallback parsing instead of live LSP/analyzer queries. |
| Governance | **9.7 / 10** | Genome, ownership, invariants, scope, standards and policy are unusually strong; external project-scale validation is still needed. |
| Evidence / proof | **9.5 / 10** | Hash chains, source-bound certification, reviews and reproducible builds are strong; external signed/transparency anchoring remains an empirical release gate. |
| Security | **9.1 / 10** | Architecture and adversarial local tests are strong; required external scanners/signers and live hardened sandbox evidence are not available here. |
| Production maturity | **7.0 / 10** | Release/migration/store/telemetry contracts exist, but real multi-stack deploys, stores, canary health and rollback drills are not yet proven end-to-end. |
| Reliability | **8.8 / 10** | Recovery/integrity/concurrency mechanisms are tested locally; distributed multi-host/partition/soak evidence is still absent. |
| CLI / DX | **9.3 / 10** | CLI automation and deterministic exits are strong; runtime-provider UX still needs unified end-to-end wiring. |
| Cost efficiency | **9.0 / 10** | Budgets, usage accounting and empirical-routing contracts exist; peer-controlled cost data has not yet been collected. |

Approximate unweighted practical average: **8.75 / 10**. This is an engineering estimate, not a benchmark result. The current public positioning should therefore remain **beta**. See `docs/COMPETITIVE_ASSESSMENT.md`.

## What was strengthened in the Target-10 pass

- SQLite/WAL worker registry with atomic reservations, slot accounting, reservation TTL and recovery.
- Hash-chained scheduler events with schema migration and deterministic replay/tamper detection.
- Hardened container policy plus a Docker executor that validates **observed** container settings rather than trusting requested policy.
- Hardened Docker repository profile with non-root execution, read-only filesystem, dropped capabilities, no-new-privileges, resource limits and default no-network mode.
- Universal semantic graph with official analyzer/MCP/LSP authority preferred over portable fallback parsing.
- Flutter official stack composition: Flutter/Dart skills, Dart MCP, Developer Knowledge MCP model and package skills.
- Next.js/Node, Python, .NET/Roslyn, Go, Rust and Java specialist adapter contracts.
- Cross-language contract drift and migration compatibility blocking.
- Health-gated release controller requiring PASS proof, canary health and explicit production approval.
- External release-attestation contract for artifact/SBOM hashes, source commit, builder identity, provenance, signature, transparency anchoring and SLSA level.
- OWASP ASVS 5.0, OWASP MASVS/MASTG/MASWE, NIST SSDF, SLSA and Sigstore-aware security posture.
- MCP 2026-07-28 stateless routing/auth/deprecation/security gateway model.
- Side-effect firewall, zero-trust content boundary, secret/network policy and strict agent result schemas.
- 500-scenario fairness-controlled benchmark protocol and empirical model router.
- Repository fingerprint bound into certification so a later source change makes a prior certification stale instead of silently reusable.
- GitHub-facing release presentation hardened with architecture/security/evidence diagrams, real CLI walkthroughs, benchmark methodology, release procedure, Dependabot policy and current v7 checkout/setup-python action pins.

## External empirical gaps — deliberately not credited as peer superiority

This build host does not provide all real execution environments required for an externally proven 10/10 result. In particular, live Flutter/Dart MCP execution, OpenHands runtime, Docker daemon, Kubernetes, Android devices, macOS/Xcode/iOS, complete release security scanner/signing toolchain, app stores and a production telemetry environment are not all available here.

The 500-scenario corpus is a **benchmark protocol**, not a fabricated 500-task victory. A superiority claim requires the same repository snapshot, prompt, model policy, token/time budget, machine class and hidden acceptance tests to be executed against the peer workflows.

## 10/10 claim boundary

A repository target score of 10.0 means all defined implementation criteria exist and the applicable local deterministic hardening gates pass. A claim such as **“better than OpenHands in orchestration/production”** or **“better Flutter engineering outcomes than Official Flutter AI alone”** requires live external evidence: distributed/runtime tests, device/store release drills, production rollback/health evidence, signed external attestations and controlled head-to-head benchmark results.
