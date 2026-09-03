---
name: foundry-intake
description: Convert a Flutter product request into explicit scope, acceptance criteria, risk signals, and a minimal execution plan before coding.
---
# Intake
1. Use `inspect_project` for existing projects.
2. Translate the request into explicit acceptance criteria; separate "must" from optional polish.
3. Use `classify_risk` before choosing an execution path.
4. If reusable capabilities are involved, call `resolve_components`.
5. Do not code until scope and success conditions are clear enough to test.
6. For trivial low-risk tasks, keep this phase short.
