# Nakeuri Flutter Foundry V4 — Final Modeled Comparison

> Claim boundary: deterministic architecture/code-state simulation anchored to the stored V3 modeled peer baselines. This is not a live empirical benchmark against current peer systems.

## Final validation snapshot

- Unit/integration: **144 / 144 PASS**
- Retained V3 Target-10: **99 / 99 PASS; 10 / 10 categories at 10.0**
- V4 hardening: **25 / 25 PASS; 10.0 / 10.0**
- Adversarial: **22 / 22 PASS**
- Polyglot smoke: **10 / 10 PASS**
- Modeled observations: **25,000**
- Scheduler chaos: **500/500 completed, 73 injected crashes, 0 duplicate claims, 0 errors**
- Event chain / SQLite integrity: **PASS / PASS**
- Release drill: **PASS** (`ROLLED_BACK` rollback; `VERIFIED` healthy production)

## Modeled peer comparison

| Profile | Engineering index | Acceptance | First-pass | Escaped defects | Architecture escapes | Contract escapes | Security escapes | Runtime failures | Modeled cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Nakeuri V4 modeled code-state | **85.79** | 78.41% | 63.27% | 20.97% | 3.52% | 1.91% | 2.12% | 1.09% | 1.188 |
| Nakeuri V3 code-state model | **81.04** | 74.70% | 57.90% | 31.65% | 6.46% | 3.60% | 3.24% | 2.34% | 1.238 |
| OpenHands-class modeled profile | **77.08** | 68.18% | 52.06% | 40.82% | 10.76% | 5.35% | 3.41% | 2.06% | 1.204 |
| Official Flutter AI modeled profile | **72.69** | 60.83% | 47.98% | 52.95% | 13.14% | 7.30% | 4.60% | 4.64% | 1.230 |
| Generic coding-agent baseline | **63.19** | 44.46% | 40.64% | 87.96% | 19.60% | 10.51% | 7.41% | 6.73% | 1.261 |

## Delta vs V3 stored model

- Engineering index: **+4.75** points
- Acceptance: **+3.71 pp**
- First-pass: **+5.37 pp**
- Escaped defects: **-10.68 pp**
- Architecture escapes: **-2.94 pp**
- Contract escapes: **-1.69 pp**
- Security escapes: **-1.12 pp**
- Runtime failures: **-1.25 pp**
- Modeled cost: **-4.06%**

V4 modeled engineering-index lead over the stored OpenHands-class profile: **+8.71 points**.

## Interpretation

The largest V4 gains come from closing the specific practical gaps identified after V3: provider-neutral risk-aware execution, authoritative LSP semantic paths, Flutter-specific structural awareness, lease fencing plus lifecycle heartbeat, and confidence/evidence-aware model routing. The modeled runtime-failure disadvantage visible in V3 is reversed in this code-state model, but that reversal still requires real multi-host/provider execution to become an empirical claim.

## Still required for empirical flagship proof

Real Docker/OpenHands/Kubernetes/CI provider runs; installed Dart/Flutter MCP and language servers on representative repositories; Android/iOS and store delivery; external security/signing infrastructure; distributed partition/soak drills; and a fair hidden-test head-to-head benchmark under identical budgets and machine conditions.
