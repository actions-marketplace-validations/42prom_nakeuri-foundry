import tempfile,unittest
from pathlib import Path
from flutter_foundry.clean_code import scan_clean_code
class T(unittest.TestCase):
 def test_base_abstraction_blocks(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'lib').mkdir();(r/'lib/a.dart').write_text('abstract class BaseService<T> {}')
   self.assertEqual(scan_clean_code(r)['status'],'fail')
