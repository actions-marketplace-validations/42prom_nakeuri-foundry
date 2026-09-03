import tempfile,unittest
from pathlib import Path
from flutter_foundry.capability_graph import register_capability,load_graph,save_graph
from flutter_foundry.duplicate_guard import scan_semantic_duplicates
class T(unittest.TestCase):
 def test_duplicate_capability_blocks(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);register_capability(r,'A','a',['x']);g=load_graph(r);g['capabilities']['B']={'owner':'b','provides':['x']};save_graph(r,g)
   self.assertEqual(scan_semantic_duplicates(r)['status'],'fail')
