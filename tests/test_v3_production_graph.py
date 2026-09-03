import json,tempfile,unittest
from pathlib import Path
from flutter_foundry.production_graph import validate_release_graph, init_release_graph, release_plan

class V3ProductionGraphTests(unittest.TestCase):
    def test_polyglot_release_order_and_rollback(self):
        data={'components':[
          {'id':'db','kind':'database','depends_on':[]},
          {'id':'api','kind':'api','depends_on':['db']},
          {'id':'admin','kind':'web','depends_on':['api']},
          {'id':'mobile','kind':'mobile','depends_on':['api']},
        ],'migrations':[]}
        v=validate_release_graph(data); self.assertEqual(v['status'],'pass'); self.assertLess(v['order'].index('db'),v['order'].index('api'))
    def test_destructive_migration_without_rollback_is_blocked(self):
        data={'components':[{'id':'db','kind':'database','depends_on':[]}], 'migrations':[{'id':'m1','destructive':True,'rollback_tested':False,'backward_compatible':False,'expand_contract':False}]}
        self.assertEqual(validate_release_graph(data)['status'],'fail')
    def test_file_release_plan(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); p=init_release_graph(r); data=json.loads(p.read_text()); data['components']=[{'id':'api','kind':'api','depends_on':[]}]; p.write_text(json.dumps(data))
            plan=release_plan(r); self.assertEqual(plan['deploy_order'],['api']); self.assertEqual(plan['rollback_order'],['api'])
