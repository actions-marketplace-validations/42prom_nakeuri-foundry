import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from flutter_foundry.verifier import verify_project
class T(unittest.TestCase):
 def test_monorepo_flutter_root_is_mobile(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d).resolve();(r/'mobile').mkdir();(r/'mobile/pubspec.yaml').write_text('name: x');(r/'.factory/genome').mkdir(parents=True)
   # No SDK in test environment: path selection is still deterministic and gaps are explicit.
   out=verify_project(r,'fast');self.assertEqual(Path(out['flutter_root']).resolve(),(r/'mobile').resolve());self.assertIn(out['status'],{'fail','pass_with_gaps'})
 def test_python_project_uses_native_unittest_and_not_flutter(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'pyproject.toml').write_text('[project]\nname="x"\n');(r/'tests').mkdir()
   with patch('flutter_foundry.verifier._run') as run:
    from flutter_foundry.models import CheckResult
    run.return_value=CheckResult(name='native',status='pass')
    out=verify_project(r,'standard')
   commands=[call.args[2] for call in run.call_args_list]
   self.assertIn(['python','-m','unittest','discover','-s','tests'],commands)
   self.assertFalse(any(command and command[0] in {'dart','flutter'} for command in commands))
   self.assertIn('native_ci_plan',out)
