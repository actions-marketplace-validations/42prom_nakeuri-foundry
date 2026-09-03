# Design Lineage

The Foundry implementation is original. It borrows design ideas from successful public systems without copying their source code.

## Google Antigravity

Adopted ideas:
- plugins bundle skills, rules, MCP, and hooks;
- workspace/project-local configuration;
- isolated worktree execution;
- pre/post tool safety hooks.

## Official Flutter Agent Plugins + Dart MCP

Adopted as first-class dependencies of the workflow:
- on-demand Flutter/Dart skills;
- analyzer diagnostics;
- symbol resolution;
- test runners;
- runtime inspection.

Project-local `PROJECT_RULES.md` still wins when official generic guidance conflicts with a deliberate project architecture decision.

## VGV Wingspan

Borrowed workflow idea:
- brainstorm -> plan -> build -> review;
- specialized architecture/test/simplicity review.

## OpenAI Symphony / worktree orchestrators

Borrowed ideas:
- task -> isolated workspace;
- proof-of-work artifacts;
- CI/review evidence before landing;
- provider-independent orchestration concepts.

## Aider-style repository mapping

Borrowed idea:
- small repository map/context instead of dumping the whole codebase into every model call.

## Patrol

Recommended for critical Flutter E2E/native journeys where ordinary widget tests cannot cover OS dialogs, permissions, deep links, or platform integration.

## Anthropic-Cybersecurity-Skills community repository

Borrowed idea:
- large skill catalog with progressive discovery;
- curated defensive subset rather than loading hundreds of skills into every task.

No third-party skill text is bundled in this repository. The optional vendor script requires an explicit pinned commit and records hashes.

## User-originated design principles incorporated

This Foundry also incorporates project-engineering principles supplied in the working design materials used to create it:
- feature-first independently removable modules;
- evidence over memory;
- read-fresh audit cycles;
- blast-radius pre-checks;
- risk mode thresholds;
- surgical fixes;
- regression tests for every repair;
- append-only learnings and false-positive memory;
- security veto for critical authorization/data-boundary failures;
- simplicity-first, anti-overengineering discipline.
