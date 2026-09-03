import tempfile,unittest
from pathlib import Path
from flutter_foundry.visual_regression import init_visual_contract,validate_visual_contract
class T(unittest.TestCase):
 def test_missing_golden_blocks_when_declared(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);init_visual_contract(r,[{'id':'login','golden_test':'test/goldens/login_test.dart'}]);self.assertEqual(validate_visual_contract(r)['status'],'fail');(r/'test/goldens').mkdir(parents=True);(r/'test/goldens/login_test.dart').write_text('// golden');self.assertEqual(validate_visual_contract(r)['status'],'pass')
