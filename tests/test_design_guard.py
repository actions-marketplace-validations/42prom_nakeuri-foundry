import tempfile,unittest
from pathlib import Path
from flutter_foundry.design_guard import scan_design
class T(unittest.TestCase):
 def test_raw_color_warns(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'lib/features/a').mkdir(parents=True);(r/'lib/features/a/a.dart').write_text('final x = Color(0xFF112233);')
   self.assertEqual(scan_design(r)['status'],'warn')
