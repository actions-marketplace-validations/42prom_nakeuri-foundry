import json,tempfile,unittest
from pathlib import Path
from flutter_foundry.ci_plan import build_ci_plan
from flutter_foundry.delivery import install_delivery_plane

class V3CIPlanTests(unittest.TestCase):
    def test_native_ci_plan_does_not_invent_missing_node_scripts(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); (r/'package.json').write_text(json.dumps({'dependencies':{'next':'16'},'scripts':{'lint':'next lint','build':'next build'}})); (r/'package-lock.json').write_text('{}')
            plan=build_ci_plan(r); cmds=plan['plans'][0]['commands']
            self.assertIn(['npm','ci'],cmds); self.assertIn(['npm','run','lint'],cmds); self.assertNotIn(['npm','run','test'],cmds)
    def test_non_flutter_delivery_does_not_install_flutter_workflows(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); (r/'package.json').write_text('{}')
            res=install_delivery_plane(r); self.assertEqual(res['status'],'pass')
            self.assertTrue((r/'.github/workflows/foundry-governance.yml').exists())
            self.assertFalse((r/'.github/workflows/flutter-pr-ci.yml').exists())
    def test_profiles_scale_native_checks_and_unittest_is_not_misclassified(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'pyproject.toml').write_text('[project]\nname="x"\n');(r/'tests').mkdir()
            fast=build_ci_plan(r,'fast')['plans'][0]['commands']
            standard=build_ci_plan(r,'standard')['plans'][0]['commands']
            self.assertNotIn(['python','-m','unittest','discover','-s','tests'],fast)
            self.assertIn(['python','-m','unittest','discover','-s','tests'],standard)
