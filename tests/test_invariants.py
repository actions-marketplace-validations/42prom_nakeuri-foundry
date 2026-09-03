import tempfile,unittest
from pathlib import Path
from flutter_foundry.invariants import register_invariant,verify_invariant_coverage
class T(unittest.TestCase):
 def test_high_requires_test(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);register_invariant(r,'INV-1','expired token invalid','auth');self.assertEqual(verify_invariant_coverage(r)['status'],'fail')
 def test_tested_high_passes(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);register_invariant(r,'INV-1','expired token invalid','auth',['test/auth_test.dart']);self.assertEqual(verify_invariant_coverage(r)['status'],'pass')
