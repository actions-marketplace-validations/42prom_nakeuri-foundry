# V4 Execution & Intelligence Hardening

V4 targets the practical gaps identified after the V3 Target-10 pass. The retained V3 target remains an implementation-coverage contract; V4 adds deeper executable wiring and resilience without changing the external-proof boundary.

## Implemented

1. **Unified provider runtime** — `runtime_provider.py` routes lifecycle agent work by risk, availability and actual isolation. Worktree-only agents cannot satisfy HIGH/RELEASE execution.
2. **Provider proof gate** — successful provider output is rejected unless risk-specific execution obligations are verified.
3. **Hardened Docker agent protocol** — explicit request/response JSON, digest-pinned HIGH/RELEASE images and observed runtime attestation.
4. **Lease fencing + heartbeat** — scheduler schema v4 issues a unique lease token per claim; stale workers cannot commit completion after recovery/reclaim, and long worker execution heartbeats the lease.
5. **Direct LSP semantics** — standard stdio JSON-RPC queries for document symbols/references, with Dart, TypeScript, Python, C#, Go, Rust and Java backends when installed.
6. **Flutter specialist layer** — state-management signals, GoRouter routes, platform channels and async BuildContext risk detection.
7. **Conservative model router** — verified outcome recording, Wilson lower-confidence ranking, risk-specific quality bands and independent second-model review for HIGH/RELEASE tasks.
8. **V4 simulation suite** — deterministic modeled comparison, real scheduler chaos exercise and real release-controller rollback/health drill.

## Local validation

- Full Python tests: **144/144 PASS** before the final documentation-only pass.
- Retained V3 Target-10: **99/99 criteria, 10/10 categories, PASS**.
- V4 hardening: **25/25 criteria, 10.0/10 implementation coverage**.
- Adversarial hardening: **22/22 PASS**.
- Polyglot smoke: **10/10 PASS**.
- Scheduler chaos: **500 tasks / 32 workers / 73 crashes / 0 duplicate claims / 0 errors**.

## Claim boundary

These results prove local code-state behavior and deterministic contracts on this host. They do not replace live Docker/OpenHands/Kubernetes/device/store/production trials or a controlled peer benchmark.
