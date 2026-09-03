# GitHub Publication Guide — Nakeuri Foundry

**Build metadata:** Python package snapshot `5.0.0a1`.

Recommended repository name:

```text
nakeuri-foundry
```

Recommended GitHub description:

> Flutter-first, polyglot, evidence-first AI engineering control plane — specialist agents, deterministic verification, proof-bound delivery and production-aware orchestration.

Recommended topics:

```text
flutter dart ai-agents antigravity mcp openhands docker kubernetes devtools software-engineering orchestration ci-cd security supply-chain python
```

## 1. Validate the exact source snapshot

```bash
python -m pip install -e . --no-deps
python -m unittest discover -s tests -v
python scripts/self_audit.py
python scripts/check_repo_policy.py
python scripts/check_actions_pinned.py
nakeuri target-10 .
nakeuri flagship-score .
nakeuri adversarial-self-test
nakeuri polyglot-smoke .
nakeuri certify . --reproducible-build
nakeuri target-10 . --reproducible-build --require-certification
```

Do not publish a certification badge from a stale source fingerprint.

## 2. Create the GitHub repository

Create an empty repository named `nakeuri-foundry`. Do not ask GitHub to create a README, license, `.gitignore` or workflows; those assets already exist.

```bash
git init -b main
git add .
git commit -m "chore: publish Nakeuri Foundry"
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/nakeuri-foundry.git
git push -u origin main
```

## 3. Protect `main`

Recommended protections:

- require pull requests before merge;
- require Foundry CI/security jobs to pass;
- dismiss stale approvals for higher-assurance changes;
- block force pushes and deletion of `main`;
- enable Dependabot/security alerts where available;
- enable secret scanning/private vulnerability reporting where available;
- use protected environments for privileged release credentials.

Install the local pre-push guard if desired:

```bash
bash scripts/install_hooks.sh
```

## 4. Configure target-project workflow variables

Generated workflows avoid floating toolchain assumptions. Configure immutable values where the generated CI expects them:

```text
FOUNDRY_INSTALL_SPEC   exact package version or immutable VCS SHA
FLUTTER_GIT_REF        exact Flutter source commit SHA when pinned by policy
```

Production credentials belong in protected environments/OIDC/platform secret stores, not ordinary repository variables.

## 5. First public release

Publish the project as a **pre-release** until real provider/device/store and controlled head-to-head evidence exists.

Suggested tag format:

```bash
git tag -a v5.0.0-alpha.1 -m "Nakeuri Foundry 5.0.0 alpha 1"
git push origin v5.0.0-alpha.1
```

The public release notes should link to:

- `SELF_AUDIT.md`;
- `docs/V5_FLAGSHIP_PROOF.md`;
- `docs/V5_EMPIRICAL_BENCHMARK.md`;
- `docs/BENCHMARK_METHODOLOGY.md`;
- the exact source commit.

## 6. First real pilot

Install Foundry once, bootstrap a representative target repository and run a controlled real-task corpus. Flutter projects should install the official Flutter/Dart skills and configure Dart MCP before judging Flutter engineering quality.

The project should not claim to be “better than OpenHands/Antigravity/Official Flutter AI” until the empirical comparison contract has actually been executed.
