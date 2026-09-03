---
name: foundry-release
description: Produce an evidence-based Flutter release readiness decision across builds, tests, security, runtime/device gaps, accessibility, performance and proof artifacts.
---
# Release workflow
1. Run `verify_project(profile="release")`.
2. Run `security_scan` and dedicated project-specific security tooling if configured.
3. Require Android release build; require iOS release build on a macOS runner for iOS products.
4. Require runtime evidence for critical journeys.
5. Require device/accessibility/performance evidence where product scope demands it.
6. Use `release_score` only as an evidence summary; missing evidence is a gap, not a pass.
7. Human approval is required for release and high-risk changes.
