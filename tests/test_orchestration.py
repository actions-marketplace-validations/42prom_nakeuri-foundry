import tempfile,unittest
from pathlib import Path
from flutter_foundry.orchestration import create_task,transition
class T(unittest.TestCase):
 def test_state_machine_and_proof_gate(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);t=create_task(r,'x');tid=t['id'];transition(r,tid,'READY');transition(r,tid,'IMPLEMENTING');transition(r,tid,'VERIFYING');transition(r,tid,'REVIEWING')
   with self.assertRaises(ValueError):transition(r,tid,'MERGEABLE',{'proof_status':'fail','review_blockers':0})
   self.assertEqual(transition(r,tid,'MERGEABLE',{'proof_status':'pass','review_blockers':0})['state'],'MERGEABLE')
 def test_illegal_transition(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);tid=create_task(r,'x')['id']
   with self.assertRaises(ValueError):transition(r,tid,'MERGED')
