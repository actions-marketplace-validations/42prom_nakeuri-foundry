import tempfile,unittest
from pathlib import Path
from flutter_foundry.adr import create_adr
class T(unittest.TestCase):
 def test_create(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);out=create_adr(r,'Use Riverpod','context','decision','consequences');self.assertTrue(Path(out['path']).exists())
