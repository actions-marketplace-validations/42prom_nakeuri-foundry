import json,tempfile,unittest
from pathlib import Path
from flutter_foundry.platform_adapters import detect_project_surfaces, adapter_report
from flutter_foundry.knowledge_graph import build_project_graph, compare_contract_snapshots, write_project_graph

class V3PlatformGraphTests(unittest.TestCase):
    def test_polyglot_monorepo_detection(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); (r/'mobile').mkdir(); (r/'mobile'/'pubspec.yaml').write_text('name: app')
            (r/'admin').mkdir(); (r/'admin'/'package.json').write_text(json.dumps({'dependencies':{'next':'16.0.0'}}))
            (r/'ai').mkdir(); (r/'ai'/'pyproject.toml').write_text('[project]\nname="ai"')
            (r/'worker').mkdir(); (r/'worker'/'go.mod').write_text('module worker')
            ids={(x['id'],x['root']) for x in detect_project_surfaces(r)}
            self.assertIn(('flutter','mobile'),ids); self.assertIn(('nextjs','admin'),ids); self.assertIn(('python','ai'),ids); self.assertIn(('go','worker'),ids)
            rep=adapter_report(r); self.assertEqual(rep['status'],'pass')
            graph=build_project_graph(r); self.assertEqual(graph['surface_count'],4)
            self.assertTrue(write_project_graph(r).exists())
    def test_cross_language_contract_drift_blocks(self):
        snaps=[
          {'contract_id':'user','provider':'openapi','fields':{'email':{'type':'string','required':True,'nullable':False}}},
          {'contract_id':'user','provider':'dart','fields':{'email':{'type':'string','required':False,'nullable':True}}},
        ]
        res=compare_contract_snapshots(snaps); self.assertEqual(res['status'],'fail'); self.assertEqual(res['findings'][0]['issue'],'type/required/nullability drift')
