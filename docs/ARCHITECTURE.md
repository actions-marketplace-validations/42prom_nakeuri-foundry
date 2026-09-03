# Architecture

## 1. Core thesis

AI should sit at the top of a trusted engineering substrate, not at the bottom of a shaky one.

The Foundry separates five planes:

1. **Knowledge plane** — project constitution, component contracts, decisions, learnings.
2. **Control plane** — Antigravity agents, skills, worktrees, task routing.
3. **Execution plane** — implementation workers and deterministic developer tools.
4. **Verification plane** — compiler/analyzer/tests/security/runtime evidence.
5. **Evidence plane** — append-only proof bundles and learnings.

## 2. Two-loop design

### Build loop

```text
brief -> requirement model -> components -> plan -> worktree -> implementation -> verify -> review -> proof
```

### Audit loop

```text
read fresh -> map reality -> classify -> reproduce -> blast radius -> surgical fix -> regression -> re-verify -> learn
```

The two loops share the same verifier and memory. This prevents the common failure where the generator and auditor evolve as unrelated systems.

## 3. Component Fabric

A component capsule is not copied source code. It is a contract describing a capability:

- what it provides;
- what it requires;
- what it conflicts with;
- its default risk;
- acceptance criteria;
- verification classes;
- implementation notes.

The agent can then implement or reuse the capability within the current project's architecture instead of blindly pasting a template.

## 4. Context Compiler

Full-repository context is expensive and often harmful. The compiler ranks files using:

- lexical task overlap;
- feature-path affinity;
- project rules;
- tests near candidate source files;
- known failure patterns.

The initial implementation is intentionally deterministic and local. A vector index can be added later only if benchmark data proves it improves recall enough to justify its cost.

## 5. Risk engine

Risk is adaptive. Signals include:

- auth/payment/tenant/security terms;
- native/platform configuration;
- file count;
- changed-symbol call sites;
- persistence/schema changes;
- previous failed strategies;
- component risk metadata.

The router returns a tier (`low`, `medium`, `high`, `release`) plus an execution recommendation rather than hard-coding one model vendor.

## 6. Deterministic Oracle

The verifier owns correctness claims where automation is possible:

- formatter;
- analyzer;
- unit/widget/integration tests;
- architecture policy;
- security scan;
- platform build / E2E in release profile when available.

An LLM review is additional evidence, never a substitute.

## 7. Proof bundles

Every accepted change should be able to produce a compact JSON artifact containing:

- task and requirement IDs;
- risk level;
- Git commit/diff identity when available;
- changed files;
- verification results;
- review findings;
- cost/time metadata when available;
- final decision.

This lets a later agent re-verify the evidence without trusting a previous narrative.

## 8. Failure memory

Every escaped defect should become at least one durable defense:

1. regression test, else
2. static/architecture rule, else
3. contract/invariant, else
4. explicit reviewer pattern.

Memory is append-only and queryable. It is not a giant prompt.
