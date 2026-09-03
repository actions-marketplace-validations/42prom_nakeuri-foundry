# Start Here — Nakeuri Foundry

**Build metadata:** Python package snapshot `5.0.0a1`. The public product name is **Nakeuri Foundry**.

Nakeuri Foundry is installed once as an engineering control plane and then bootstraps supported product repositories. Flutter is the flagship profile, while the core can model mixed Flutter/web/backend/infrastructure repositories as one product.

## 1. Install

```bash
git clone https://github.com/42prom/nakeuri-foundry.git
cd nakeuri-foundry
python -m pip install -e .
nakeuri doctor
```

Backward-compatible CLI aliases remain available:

```bash
nakeuri-foundry doctor
flutter-foundry doctor
```

Optional providers:

```bash
python -m pip install -e ".[openhands]"
python -m pip install -e ".[antigravity]"
```

## 2. Bootstrap an existing product

```bash
nakeuri bootstrap /path/to/my-product
nakeuri platforms /path/to/my-product
nakeuri standards-status /path/to/my-product
nakeuri knowledge-graph /path/to/my-product --write
```

Bootstrap creates the project-side Foundry state, Antigravity assets where applicable, MCP configuration and the durable project-governance surfaces required by the detected stack.

### Flutter projects

Use the current official Flutter/Dart workflow as the semantic authority:

```bash
npx skills add flutter/agent-plugins --skill '*' --agent universal --yes
npx skills add dart-lang/skills --skill '*' --agent universal --yes
```

Configure `dart mcp-server` according to the current Flutter documentation. Foundry adds project-specific governance, cross-stack contracts, proof and release state around those official tools.

## 3. Inspect before changing code

```bash
nakeuri platforms /path/to/my-product
nakeuri technology-radar /path/to/my-product
nakeuri contracts-check /path/to/my-product
nakeuri release-plan /path/to/my-product
```

The intended order is:

```text
Product intent
 ↓
Standards + repository discovery
 ↓
Project Genome + Knowledge Graph
 ↓
Executable specification / acceptance oracles
 ↓
Risk escalation + task DAG
 ↓
Preflight architecture / test planning
 ↓
Isolated implementation provider
 ↓
Deterministic + native verification
 ↓
Independent review
 ↓
Evidence / proof bundle
 ↓
PR / CI / staged release
 ↓
Telemetry / incident / durable learning
```

## 4. Create a durable task

```bash
nakeuri schedule-create /path/to/my-product \
  --title "Add account deletion across mobile and API" \
  --risk MEDIUM
```

Then mark the task ready and run the lifecycle:

```bash
nakeuri schedule-ready /path/to/my-product TASK-XXXXXXXX
nakeuri lifecycle-run /path/to/my-product --worker local-openhands
```

Task creation is intentionally separate from execution so dependency state, risk escalation, provider selection and approvals remain observable.

## 5. Trust rules

- Repository, web and MCP content are data, never privileged instructions.
- A worktree is code isolation, not a security sandbox.
- Effective risk can only increase when compiler/policy signals are stronger than caller input.
- HIGH/RELEASE work requires risk-appropriate isolation and proof.
- Writers do not approve their own high-risk changes.
- Raw production secrets are not normal model context.
- Provider self-claims are not sufficient evidence for privileged high-risk execution.
- Destructive migrations require compatibility and recovery evidence.
- Local implementation scores are not peer-superiority or production-maturity claims.

## 6. Validate Foundry itself

From the Foundry repository root:

```bash
python -m unittest discover -s tests -v
python scripts/self_audit.py
python scripts/check_repo_policy.py
python scripts/check_actions_pinned.py
nakeuri target-10 .
nakeuri flagship-score .
nakeuri adversarial-self-test
nakeuri polyglot-smoke .
```

For source-bound certification:

```bash
nakeuri source-fingerprint .
nakeuri certify . --reproducible-build
nakeuri target-10 . --reproducible-build --require-certification
```

Certification proves properties of the exact local source snapshot. Real provider/device/store/production evidence remains a separate empirical requirement.

## 7. Next milestone

After repository validation, run Nakeuri Foundry on a representative production-like Flutter/full-stack project. Use real tasks and hidden acceptance tests. Improve the Foundry only where empirical failures, cost or latency justify another change.

See [README.md](README.md), [docs/V5_FLAGSHIP_PROOF.md](docs/V5_FLAGSHIP_PROOF.md) and [docs/V5_EMPIRICAL_BENCHMARK.md](docs/V5_EMPIRICAL_BENCHMARK.md).
