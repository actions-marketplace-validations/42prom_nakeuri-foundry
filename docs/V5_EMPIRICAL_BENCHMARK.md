# V5 Empirical Benchmark Protocol

Version: **5.0.0a1**

The V5 benchmark harness is intended to replace architecture-simulation claims with controlled executions.

## Fairness contract

For each task/profile pair the harness records and enforces:

- fresh clone per run;
- exact resolved Git commit SHA;
- runner prompt without hidden acceptance commands;
- identical hidden acceptance commands across profiles;
- task-level time, token and cost budgets;
- machine OS/architecture/Python fingerprint;
- acceptance result, duration and reported usage.

Profiles are external runner commands, so the same harness can call Nakeuri, Antigravity, OpenHands or another workflow without embedding competitor-specific scoring assumptions.

## Recommended real Flutter corpus

Use at least 100 representative tasks spanning UI/layout, state management, routing, API integration, offline/idempotency, auth, payments, database/API migration, native permission, performance, accessibility, crash recovery and release configuration.

For a defensible flagship claim, target **>=99% accepted runs satisfying all machine-verifiable gates**, zero known blocker merges and a downward escaped-regression trend. This remains an empirical target, not a guarantee of perfect software.

## Ablation matrix

At minimum compare:

- base model/harness;
- + Official Flutter/Dart skills and MCP;
- + Nakeuri executable specification;
- + Project Genome/Knowledge Graph;
- + specialist independent reviewers;
- + risk/model router;
- + evidence/proof gate;
- full Nakeuri.

Only retain expensive components that improve measured outcomes or materially reduce risk.
