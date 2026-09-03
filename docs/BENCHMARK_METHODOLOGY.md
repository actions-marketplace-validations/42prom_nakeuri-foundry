# Peer Benchmark Methodology

Nakeuri must not convert feature coverage into a claim that it is better than another engineering system. Peer-superiority claims require controlled execution.

## What is being measured

The V3 corpus contains 500 structured scenarios across product creation, bug fixing, refactoring, security, authentication, payments, offline behavior, performance, accessibility, native integration, database migration, API compatibility, CI/CD, production incidents, rollback, dependency upgrades, architecture, testing and supply-chain work.

The corpus is a **protocol**, not evidence that 500 tasks were successfully completed.

## Fair comparison contract

A valid comparison between Nakeuri and another workflow must keep the following fixed whenever technically possible:

- repository source snapshot and starting state;
- task description and hidden acceptance tests;
- model/provider policy or a clearly disclosed equivalent policy;
- token/cost/time budget;
- machine class and network policy;
- toolchain versions;
- human-intervention rules;
- success criteria and failure classification.

A peer may use its native runtime/orchestrator if that is part of the product being compared. The report must disclose that difference rather than normalizing it away.

## Primary metrics

Measure at least:

```text
acceptance success
first-pass success
hidden-test pass rate
escaped regression rate
security defects
architecture/policy violations
duplicate capability creation
cross-service contract breakage
repair iterations
human interventions
elapsed time
tokens
monetary cost
runtime/scheduler recovery
release success
rollback success
```

For Flutter-specific comparisons, include analyzer/test/device outcomes, accessibility/performance evidence and platform-release correctness where applicable.

## Required baselines

The public benchmark should include the strongest relevant current baselines available at execution time. Candidates include:

- Official Flutter AI stack alone for Flutter-focused tasks;
- VGV Wingspan + its Flutter plugin for Flutter workflow comparisons;
- OpenHands for general agent-runtime/orchestration and production-control comparisons;
- OpenAI Symphony/reference-style orchestration where its workflow is relevant;
- a model/tooling baseline without Nakeuri governance for ablation.

Versions, commit SHAs and dates must be recorded. "Current" must be re-verified before each public benchmark cycle.

## Score policy

Do not publish a single 10/10 score when the underlying metrics disagree. Publish raw results, confidence intervals where sample sizes support them, failure categories and the benchmark artifacts required to reproduce the run.

A statement such as "Nakeuri delivers stronger Flutter engineering outcomes" is only supported if Nakeuri materially outperforms the corresponding baseline under the fairness contract. A statement such as "better than OpenHands in orchestration" additionally requires distributed/runtime failure testing at comparable scale, not only coding-task success.

## Evidence retention

Each benchmark run should preserve:

```text
source fingerprint
system/version fingerprint
task id
model policy
toolchain/runtime fingerprint
budget
stdout/stderr or structured events
acceptance results
review/repair history
final artifacts
cost/token/time metrics
```

Published aggregate results should link back to these run manifests without exposing secrets or private source code.
