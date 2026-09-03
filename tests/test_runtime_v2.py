import tempfile,unittest,sys
from pathlib import Path
from flutter_foundry.runtime import CommandRuntime,DryRunRuntime
class T(unittest.TestCase):
    def test_command_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            o=CommandRuntime().execute(Path(d),[sys.executable,'-c','print("ok")']);self.assertEqual(o['status'],'pass');self.assertIn('ok',o['stdout'])
    def test_dry_run_is_not_pass(self):
        with tempfile.TemporaryDirectory() as d:self.assertEqual(DryRunRuntime().execute(Path(d),['echo','x'])['status'],'simulated')
