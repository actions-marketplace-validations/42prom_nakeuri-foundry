---
name: foundry-audit
description: Audit an existing Flutter project using fresh repo/runtime evidence, risk classification, security, architecture, device and release lenses without inventing issues.
---
# Audit workflow
Read fresh -> map reality -> inspect risk surfaces -> verify findings -> classify -> propose surgical fixes -> regression lock -> re-verify.

Rules:
- absence is not a bug until the required behavior is proven;
- stale findings must be rechecked against current HEAD;
- missing runtime/device evidence reduces confidence rather than being guessed;
- security boundary violations take priority over polish.
