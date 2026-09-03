import tempfile
import unittest
from pathlib import Path

from flutter_foundry.budget import budget_status
from flutter_foundry.scheduler import Scheduler

class T(unittest.TestCase):
    def test_usage_is_durable_and_budget_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); s=Scheduler(root)
            t=s.create_task('tiny','LOW',max_attempts=1); s.ready(t['id']); s.claim_next('w')
            s.record_usage(t['id'],'w','worker',cost_usd=0.60,tokens=10,seconds=1)
            b=budget_status(root,t['id'],'LOW')
            self.assertEqual(b['status'],'blocked')
            self.assertEqual(b['usage']['entries'],1)
            blocked=s.block(t['id'],'budget-gate','over budget')
            self.assertEqual(blocked['state'],'BLOCKED')
            self.assertIsNone(blocked['lease_owner'])

    def test_under_budget_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); s=Scheduler(root)
            t=s.create_task('normal','MEDIUM')
            s.record_usage(t['id'],'w','worker',cost_usd=0.10,tokens=1000,seconds=3)
            self.assertEqual(budget_status(root,t['id'],'MEDIUM')['status'],'pass')

if __name__=='__main__': unittest.main()
