---
name: foundry-compose
description: Build a new Flutter project as compatible reusable capability capsules instead of a giant copied template.
---
# Compose workflow
1. Extract product capabilities from the brief.
2. Call `resolve_components` with required component IDs/capabilities.
3. Reject conflicts before implementation.
4. Scaffold only selected capabilities; do not install speculative modules.
5. Each capability must satisfy its acceptance and verification contract.
6. Keep project-local `PROJECT_RULES.md` authoritative when a generic capsule conflicts with a deliberate choice.
