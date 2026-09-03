---
name: foundry-feature
description: Implement a Flutter feature using project-local architecture, minimal context, deterministic verification, and proof-oriented completion.
---
# Feature workflow
1. Read `PROJECT_RULES.md`.
2. Call `context_for_task` and inspect only the highest-value files first.
3. Work in an isolated branch/worktree when the task is medium/high risk.
4. Keep business logic outside widgets and preserve local state/networking conventions.
5. Add the minimum tests that prove acceptance criteria.
6. Run `verify_project` using the risk-appropriate profile.
7. Request independent review for high-risk work.
8. Do not declare completion with a failing/unavailable mandatory gate.
