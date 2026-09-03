import tempfile,unittest
from pathlib import Path
from flutter_foundry.capability_graph import register_capability,resolve_intent,duplicate_capabilities
class T(unittest.TestCase):
 def test_owner_and_resolve(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.assertEqual(register_capability(r,'CAP-AUTH','features/auth',['auth.refresh'])['status'],'pass');self.assertEqual(resolve_intent(r,'refresh authentication session')['decision'],'EXTEND_OR_REUSE');self.assertEqual(duplicate_capabilities(r)['status'],'pass')
 def test_overlap_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);register_capability(r,'A','a',['x']);self.assertEqual(register_capability(r,'B','b',['x'])['status'],'conflict')
