# Roadmap after v5.0.0-alpha.1

The earlier repository-defined Target-10 remains complete, and V5 flagship-proof hardening is implemented locally. The next roadmap is deliberately **empirical**, not feature-count driven.

## Priority 1 — live specialist-tool validation

- Run official Dart/Flutter MCP and current official Flutter/Dart skills against representative real Flutter repositories.
- Exercise analyzer diagnostics, symbol resolution, tests, runtime introspection, Android emulator/physical-device evidence and iOS/macOS builds.
- Run deep Next.js/TypeScript and Python semantic/toolchain adapters on representative production-shaped repositories.

## Priority 2 — real isolated/distributed execution

- Exercise the OpenHands provider against its supported current SDK.
- Run hardened Docker HIGH/RELEASE workloads and validate observed runtime controls.
- Exercise Kubernetes/remote worker placement, worker death, scheduler restart, network partitions, multi-host contention and long soak tests.

## Priority 3 — production delivery evidence

- Execute signed Android/iOS release candidates, server/web releases and real database migration drills.
- Produce and verify SBOM, provenance, signatures/attestations and protected-environment approvals in hosted CI.
- Exercise Play Internal/TestFlight, staged rollout, canary health, kill-switch and rollback procedures.
- Capture production telemetry evidence without exposing secrets or PII.

## Priority 4 — controlled peer benchmarks

Execute the 500-scenario protocol under `docs/BENCHMARK_METHODOLOGY.md` against current relevant peers and ablations. Expand beyond 500 only when additional scenarios increase coverage rather than headline size.

A public "better than OpenHands" or "better Flutter outcomes" claim must be based on these empirical runs, not the implementation Target-10 score.
