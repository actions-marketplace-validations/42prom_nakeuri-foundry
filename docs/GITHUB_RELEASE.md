# GitHub Release Procedure

This procedure applies to Nakeuri Foundry releases. It is intentionally stricter than a normal source archive because repository claims are source-bound.

## Release sequence

```text
freeze candidate
  ↓
run tests + repository policy
  ↓
run adversarial hardening
  ↓
reproducible wheel build + clean install
  ↓
source-bound certification
  ↓
Target-10 current-certification check
  ↓
review README / changelog / security boundary
  ↓
tag exact commit
  ↓
GitHub pre-release
  ↓
post-release smoke / provenance checks
```

## Commands

```bash
python -m unittest discover -s tests -v
python scripts/self_audit.py
python scripts/check_repo_policy.py
python scripts/check_actions_pinned.py
nakeuri adversarial-self-test
nakeuri certify . --reproducible-build
nakeuri target-10 . --reproducible-build --require-certification
```

The final command must be run after all release-relevant documentation and workflow changes. Any later source change makes the previous certification stale by design.

## Versioning

The Python package uses PEP 440 (`5.0.0a1`), while the Git tag may use the more readable SemVer-style pre-release spelling (`v5.0.0-alpha.1`). Document both explicitly to avoid treating them as conflicting versions.

## Public claim boundary

A beta release may state deterministic repository validation that was actually executed. It must not claim peer superiority from the 500-scenario protocol alone. External runtime, device/store, production and controlled peer-benchmark evidence must be reported separately.
