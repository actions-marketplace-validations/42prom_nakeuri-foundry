# Quality Model

A "100/100" score is meaningful only if every point maps to evidence.

| Area | Weight |
|---|---:|
| Functional correctness | 25 |
| Architecture & maintainability | 15 |
| Test quality | 15 |
| Security & privacy | 10 |
| Performance | 10 |
| UX consistency & accessibility | 10 |
| Reliability & error handling | 5 |
| Dependency / supply-chain hygiene | 5 |
| Documentation / operability | 3 |
| Cost efficiency | 2 |

Rules:

- any blocker -> release score cannot pass;
- unresolved high severity -> score capped at 79;
- 100 requires all mandatory deterministic gates to pass;
- coverage alone is never proof of correctness;
- critical journeys require integration or E2E evidence in release mode.

The CLI's current `release_score` is deliberately conservative and scores available automated evidence only. It never fabricates missing runtime/store evidence.
