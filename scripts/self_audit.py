from pathlib import Path
import json,py_compile,sys,tomllib
root=Path('.');errors=[]
for p in (root/'src').rglob('*.py'):
    try: py_compile.compile(str(p),doraise=True)
    except Exception as e: errors.append(f'{p}: {e}')
    try:
        if b'\x08' in p.read_bytes(): errors.append(f'{p}: contains literal backspace byte (likely broken regex)')
    except Exception: pass
for p in list((root/'policies').glob('*.json'))+list((root/'registry').rglob('*.json'))+list((root/'src'/'flutter_foundry'/'assets').rglob('*.json')):
    try: json.loads(p.read_text())
    except Exception as e: errors.append(f'{p}: {e}')
try:
    data=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))
    if data['project']['name']!='nakeuri-flutter-foundry': errors.append('pyproject project name mismatch')
except Exception as e: errors.append(f'pyproject invalid: {e}')
required=[
 'src/flutter_foundry/scheduler.py','src/flutter_foundry/worktrees.py','src/flutter_foundry/reviews.py',
 'src/flutter_foundry/evidence_ledger.py','src/flutter_foundry/proof.py','src/flutter_foundry/gate.py',
 'src/flutter_foundry/platform_adapters.py','src/flutter_foundry/component_solver.py','src/flutter_foundry/production.py',
 'src/flutter_foundry/assurance.py','src/flutter_foundry/lifecycle.py','src/flutter_foundry/agent_runtime.py',
 'src/flutter_foundry/security_assurance.py','src/flutter_foundry/budget.py','src/flutter_foundry/environment.py','src/flutter_foundry/certification.py',
 'src/flutter_foundry/store_delivery.py','src/flutter_foundry/sbom.py','src/flutter_foundry/safe_paths.py','src/flutter_foundry/agent_protocol.py',
 'src/flutter_foundry/trust_boundary.py','src/flutter_foundry/maintenance.py','src/flutter_foundry/upgrade.py','src/flutter_foundry/compatibility.py',
 'src/flutter_foundry/reproducible_build.py','src/flutter_foundry/hardening.py','src/flutter_foundry/maturity_report.py',
 'src/flutter_foundry/standards.py','src/flutter_foundry/execution_fabric.py','src/flutter_foundry/distributed_runtime.py',
 'src/flutter_foundry/knowledge_graph.py','src/flutter_foundry/production_graph.py','src/flutter_foundry/migration_safety.py',
 'src/flutter_foundry/mcp_gateway.py','src/flutter_foundry/telemetry.py','src/flutter_foundry/v3_maturity.py',
 'src/flutter_foundry/ci_plan.py','src/flutter_foundry/polyglot_smoke.py','src/flutter_foundry/semantic_engine.py',
 'src/flutter_foundry/runtime_security.py','src/flutter_foundry/docker_runtime.py','src/flutter_foundry/release_controller.py',
 'src/flutter_foundry/attestation.py','src/flutter_foundry/security_posture.py','src/flutter_foundry/benchmark_v3.py',
 'src/flutter_foundry/model_router.py','src/flutter_foundry/target10.py','src/flutter_foundry/source_fingerprint.py',
 'src/flutter_foundry/runtime_provider.py','src/flutter_foundry/lsp_semantics.py','src/flutter_foundry/flutter_intelligence.py',
 'src/flutter_foundry/v4_maturity.py','src/flutter_foundry/v4_simulation.py',
 'src/flutter_foundry/specification.py','src/flutter_foundry/antigravity_native.py','src/flutter_foundry/native_e2e.py',
 'src/flutter_foundry/defense_memory.py','src/flutter_foundry/empirical_benchmark.py','src/flutter_foundry/v5_maturity.py','src/flutter_foundry/v5_simulation.py',
 'docs/V4_HARDENING.md','docs/V4_MODELED_COMPARISON.md','docs/V5_FLAGSHIP_PROOF.md','docs/V5_EMPIRICAL_BENCHMARK.md',
 'docker/Dockerfile','docker/README.md','compose.yaml','.dockerignore','evals/golden_tasks/v3_target_500.jsonl',
 'src/flutter_foundry/assets/github/flutter-pr-ci.yml',
 'src/flutter_foundry/assets/github/foundry-governance.yml',
 'src/flutter_foundry/assets/github/release-gate.yml'
]
errors += [f'missing {x}' for x in required if not (root/x).exists()]
try:
    project_version=data['project']['version']
    ns={}
    exec((root/'src/flutter_foundry/__init__.py').read_text(encoding='utf-8'),ns)
    if ns.get('__version__')!=project_version: errors.append('package __version__ does not match pyproject version')
    for rel in ['README.md','START_HERE.md','SELF_AUDIT.md','SECURITY.md','MANIFEST.md','CHANGELOG.md','GITHUB_READY.md']:
        text=(root/rel).read_text(encoding='utf-8')
        if project_version not in text: errors.append(f'{rel}: current version {project_version} missing')
except Exception as e: errors.append(f'version consistency check failed: {e}')
try:
    factory=json.loads((root/'factory.json').read_text(encoding='utf-8'))
    if factory.get('version')!=project_version: errors.append('factory.json version does not match pyproject version')
except Exception as e: errors.append(f'factory version check failed: {e}')
try:
    corpus=root/'evals/golden_tasks/v3_target_500.jsonl'
    rows=[json.loads(x) for x in corpus.read_text(encoding='utf-8').splitlines() if x.strip()]
    if len(rows)!=500: errors.append(f'V3 target corpus must contain exactly 500 scenarios, found {len(rows)}')
    ids=[r.get('id') for r in rows]
    if len(ids)!=len(set(ids)): errors.append('V3 target corpus contains duplicate scenario IDs')
except Exception as e: errors.append(f'benchmark corpus invalid: {e}')
if errors:
    print('\n'.join(errors));sys.exit(1)
print('PASS: Foundry V5 self-audit')
