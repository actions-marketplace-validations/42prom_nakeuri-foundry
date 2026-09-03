from pathlib import Path
from urllib.parse import unquote
import json,re,sys

root=Path('.')
required=[
    'policies/quality.json',
    'policies/delivery.json',
    'policies/evidence.json',
    'docs/FULL_LIFECYCLE.md',
    'docs/PROJECT_GENOME.md',
    'docs/ORCHESTRATION_KERNEL.md',
    'README.md',
    'START_HERE.md',
    'GITHUB_READY.md',
    'LICENSE',
    'SUPPORT.md',
    'CODE_OF_CONDUCT.md',
    '.github/dependabot.yml',
    'docs/BENCHMARK_METHODOLOGY.md',
    'docs/COMPETITIVE_ASSESSMENT.md',
    'docs/GITHUB_RELEASE.md',
    '.github/pull_request_template.md',
    '.github/ISSUE_TEMPLATE/bug.yml',
    '.github/ISSUE_TEMPLATE/feature.yml',
    '.agents/plugins/nakeuri-flutter-foundry/plugin.json',
    'docs/V3_UNIVERSAL_ARCHITECTURE.md',
    'docker/Dockerfile',
    'docker/README.md',
    'compose.yaml',
    '.dockerignore',
    'evals/golden_tasks/v3_target_500.jsonl',
]
errors=[f'missing {x}' for x in required if not (root/x).exists()]

# Keep release-facing Markdown references source-bound and locally resolvable.
# External URLs and in-page anchors are outside this repository integrity check.
link_pattern = re.compile(r'!?\[[^\]]*\]\(([^)]+)\)')
for doc in [root/'README.md', root/'START_HERE.md', root/'GITHUB_READY.md', *sorted((root/'docs').rglob('*.md'))]:
    if not doc.exists():
        continue
    for raw in link_pattern.findall(doc.read_text(encoding='utf-8')):
        target = raw.strip().strip('<>').split('#', 1)[0]
        if not target or target.startswith(('http://', 'https://', 'mailto:')):
            continue
        candidate = (doc.parent / unquote(target)).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            errors.append(f'local Markdown link escapes repository in {doc}: {raw}')
            continue
        if not candidate.exists():
            errors.append(f'broken local Markdown link in {doc}: {raw}')

for p in Path('policies').glob('*.json'):
    try: json.loads(p.read_text(encoding='utf-8'))
    except Exception as e: errors.append(f'invalid JSON {p}: {e}')

try:
    factory=json.loads((root/'factory.json').read_text(encoding='utf-8'))
    if factory.get('name')!='Nakeuri Flutter Foundry':
        errors.append('factory.json product name is not Nakeuri Flutter Foundry')
    if factory.get('schema') not in {'nakeuri-flutter-foundry/factory/v1','nakeuri-foundry/factory/v3'}:
        errors.append('factory.json schema is not a supported Nakeuri namespace')
except Exception as e:
    errors.append(f'invalid factory.json: {e}')

try:
    plugin=json.loads((root/'.agents/plugins/nakeuri-flutter-foundry/plugin.json').read_text(encoding='utf-8'))
    if plugin.get('name')!='nakeuri-flutter-foundry':
        errors.append('Antigravity plugin id mismatch')
except Exception as e:
    errors.append(f'invalid plugin.json: {e}')

legacy='Flutter Engineering Foundry'
for rel in ['README.md','START_HERE.md','SECURITY.md','AGENTS.md','pyproject.toml','factory.json']:
    p=root/rel
    if p.exists() and legacy in p.read_text(encoding='utf-8'):
        errors.append(f'legacy branding remains in {rel}')

if errors:
    print('\n'.join(errors));sys.exit(1)
print('PASS: Nakeuri Foundry repository governance assets present')
