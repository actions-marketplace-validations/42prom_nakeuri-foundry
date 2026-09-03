import tempfile,unittest
from pathlib import Path
from flutter_foundry.test_quality import scan_test_quality
class T(unittest.TestCase):
 def test_assertion_missing_fails(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'test').mkdir();(r/'test/x_test.dart').write_text("test('x', () { var a=1; });")
   self.assertEqual(scan_test_quality(r)['status'],'fail')
