import tempfile,unittest
from pathlib import Path
from flutter_foundry.genome import init_genome,validate_genome
class T(unittest.TestCase):
 def test_init_and_validate(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.assertEqual(init_genome(r)['status'],'pass');self.assertEqual(validate_genome(r)['status'],'pass')
