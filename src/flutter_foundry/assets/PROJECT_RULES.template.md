# PROJECT_RULES.md — Nakeuri Flutter Foundry Constitution

## Priority
1. Explicit user/product requirements
2. Project Genome and approved ADRs
3. This constitution
4. Task-specific skills
5. Agent defaults

## Core invariants
- Feature-first ownership. A feature must be independently understandable and removable.
- One business capability has one canonical owner. Search the Capability Graph before creating a new service, repository, endpoint, model, state container, or screen that may overlap.
- One business fact has one source of truth. Consumers may project it; they may not invent parallel truth.
- Architecture follows demonstrated complexity. Do not add layers, interfaces, factories, managers, coordinators, generic bases, or future-proofing without an actual current use case.
- Business logic stays outside widgets and remains unit-testable without Flutter rendering where practical.
- Use the project's selected single state-management system and network client unless an ADR explicitly changes them.
- Design must use Project Genome tokens and canonical interaction patterns. Raw visual constants outside the design system require explicit justification.
- Every bug fix gets a regression test that fails before and passes after, unless impossible; exceptions require evidence.
- High-risk domain invariants require explicit tests.
- Every task declares Change Intent; unrelated changes are scope drift.
- Writer does not self-approve. High-risk work requires independent review.
- No proof bundle, no mergeable state.
- Security veto: known critical/high exploitable security failures block merge/release.

## Simplicity rule
Choose the smallest correct, readable, testable, secure solution. If 200 lines can safely be 50, simplify. Complexity must pay rent with present evidence.

## Git discipline
- PR-only to main.
- Isolated branch/worktree per concurrent implementation task.
- CI green before merge.
- Never bypass checks silently.
