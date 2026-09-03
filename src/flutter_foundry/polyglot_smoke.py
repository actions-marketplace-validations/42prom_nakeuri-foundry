from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from .bootstrap import bootstrap_project
from .ci_plan import build_ci_plan
from .knowledge_graph import build_project_graph, compare_contract_snapshots
from .migration_safety import assess_migration
from .production_graph import validate_release_graph
from .standards import standards_status


def run_polyglot_smoke() -> dict[str, Any]:
    checks=[]
    def add(name: str, ok: bool, detail: str=''):
        checks.append({'name':name,'status':'pass' if ok else 'fail','detail':detail})
    with tempfile.TemporaryDirectory() as d:
        r=Path(d)
        (r/'mobile').mkdir(); (r/'mobile/pubspec.yaml').write_text('name: mobile\n',encoding='utf-8')
        (r/'admin').mkdir(); (r/'admin/package.json').write_text(json.dumps({'dependencies':{'next':'16.0.0'},'scripts':{'lint':'next lint','build':'next build'}}),encoding='utf-8'); (r/'admin/package-lock.json').write_text('{}')
        (r/'backend').mkdir(); (r/'backend/package.json').write_text(json.dumps({'scripts':{'test':'node --test'}}),encoding='utf-8')
        (r/'ai').mkdir(); (r/'ai/pyproject.toml').write_text('[project]\nname="ai"\n[tool.ruff]\n[tool.pytest.ini_options]\n',encoding='utf-8')
        (r/'worker').mkdir(); (r/'worker/go.mod').write_text('module worker\n')
        (r/'native').mkdir(); (r/'native/Cargo.toml').write_text('[package]\nname="native"\nversion="0.1.0"\n')
        (r/'dotnet').mkdir(); (r/'dotnet/app.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"></Project>')
        (r/'java').mkdir(); (r/'java/pom.xml').write_text('<project></project>')
        boot=bootstrap_project(r,install_delivery=True)
        ids={s['id'] for s in boot['platform_surfaces']}
        add('polyglot bootstrap detects specialist surfaces', {'flutter','nextjs','node','python','go','rust','dotnet','java'} <= ids)
        mcp=json.loads((r/'.agents/mcp_config.json').read_text())
        add('Flutter surface composes official Dart MCP entry', 'dart' in mcp.get('mcpServers',{}))
        add('standards registry valid', standards_status(r).get('status') in {'pass','warn'})
        graph=build_project_graph(r); add('knowledge graph covers all surfaces', graph.get('surface_count') >= 8)
        ci=build_ci_plan(r); add('native CI plan generated for every surface', len(ci.get('plans',[])) >= 8)
        add('universal governance workflow installed', (r/'.github/workflows/foundry-governance.yml').exists())
        add('Flutter delivery workflows installed only because Flutter exists', (r/'.github/workflows/flutter-pr-ci.yml').exists())
        drift=compare_contract_snapshots([
            {'contract_id':'profile','provider':'api','fields':{'id':{'type':'string','required':True,'nullable':False}}},
            {'contract_id':'profile','provider':'mobile','fields':{'id':{'type':'int','required':True,'nullable':False}}},
        ])
        add('cross-language contract drift fails closed', drift.get('status')=='fail')
        release=validate_release_graph({'components':[
            {'id':'db','kind':'database','depends_on':[]},{'id':'api','kind':'api','depends_on':['db']},
            {'id':'admin','kind':'web','depends_on':['api']},{'id':'mobile','kind':'mobile','depends_on':['api']},
        ],'migrations':[]})
        add('multi-surface release graph orders dependencies', release.get('status')=='pass' and release['order'].index('db') < release['order'].index('api'))
        migration=assess_migration({'operations':[{'op':'drop_column','field':'legacy'}],'backup_verified':True,'rollback_tested':True,'backward_compatible':False,'expand_contract':True},[{'id':'mobile-old','fields':['legacy']}])
        add('old client blocks unsafe migration',migration.get('status')=='fail')
    failed=[c for c in checks if c['status']!='pass']
    return {'schema':'nakeuri/polyglot-smoke/v1','status':'fail' if failed else 'pass','passed':len(checks)-len(failed),'total':len(checks),'checks':checks}
