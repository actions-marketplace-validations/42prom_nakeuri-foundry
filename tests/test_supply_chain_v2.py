import tempfile,unittest
from pathlib import Path
from flutter_foundry.supply_chain import scan_supply_chain
class T(unittest.TestCase):
 def test_release_requires_lock_and_action_sha(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'pubspec.yaml').write_text('name: x\n');(r/'.github/workflows').mkdir(parents=True);(r/'.github/workflows/x.yml').write_text('steps:\n - uses: actions/checkout@v4\n');o=scan_supply_chain(r,True);self.assertEqual(o['status'],'fail');self.assertGreaterEqual(o['summary']['high'],2)
 def test_full_sha_and_lock_pass(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'pubspec.yaml').write_text('name: x\n');(r/'pubspec.lock').write_text('packages: {}\n');(r/'.github/workflows').mkdir(parents=True);(r/'.github/workflows/x.yml').write_text('steps:\n - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683\n');self.assertEqual(scan_supply_chain(r,True)['status'],'pass')
