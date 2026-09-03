import json,tempfile,unittest
from pathlib import Path
from flutter_foundry.production import init_production_ops,validate_production_ops
class T(unittest.TestCase):
    def test_placeholders_block_release(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);p=init_production_ops(r);self.assertEqual(validate_production_ops(r)['status'],'fail')
            x=json.loads(p.read_text());x['health']={'crash_signal':'crashlytics','api_signal':'/health'};x['rollback']={'strategy':'server kill switch + previous image','owner':'oncall','kill_switch':'remote-config'};x['incident']={'runbook':'docs/runbook.md','escalation_owner':'oncall'};x['migration']={'backward_compatible':True,'rollback_tested':False};p.write_text(json.dumps(x))
            self.assertEqual(validate_production_ops(r)['status'],'pass')
