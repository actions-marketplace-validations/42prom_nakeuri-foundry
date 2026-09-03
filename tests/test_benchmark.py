import tempfile,unittest
from pathlib import Path
from flutter_foundry.benchmark import summarize_results
class T(unittest.TestCase):
 def test_summary(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r.jsonl';p.write_text('{"accepted":true,"cost":2,"repair_iterations":1}\n{"accepted":false,"cost":1,"repair_iterations":2}\n')
   self.assertEqual(summarize_results(p)['acceptance_rate'],0.5)
