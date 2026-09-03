import tempfile, unittest, sqlite3
from pathlib import Path
from flutter_foundry.scheduler import Scheduler

class T(unittest.TestCase):
    def test_dependency_and_atomic_claim(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); s=Scheduler(r)
            a=s.create_task('a',task_id='TASK-A'); b=s.create_task('b',depends_on=['TASK-A'],task_id='TASK-B')
            s.ready('TASK-A')
            with self.assertRaises(ValueError): s.ready('TASK-B')
            c=s.claim_next('worker-1'); self.assertEqual(c['id'],'TASK-A'); self.assertEqual(c['state'],'IMPLEMENTING')
            self.assertIsNone(s.claim_next('worker-2'))
    def test_retry_budget_consistent(self):
        with tempfile.TemporaryDirectory() as d:
            s=Scheduler(Path(d)); s.create_task('x',max_attempts=1,task_id='TASK-X'); s.ready('TASK-X')
            s.claim_next('w'); x=s.finish_attempt('TASK-X','w',False,'boom'); self.assertEqual(x['state'],'REPAIRING'); self.assertEqual(x['attempts'],1)
            s.claim_next('w'); x=s.finish_attempt('TASK-X','w',False,'boom2'); self.assertEqual(x['state'],'FAILED'); self.assertEqual(x['attempts'],2)
    def test_heartbeat_requires_lease_owner(self):
        with tempfile.TemporaryDirectory() as d:
            s=Scheduler(Path(d)); s.create_task('x',task_id='TASK-X'); s.ready('TASK-X'); s.claim_next('w')
            with self.assertRaises(ValueError): s.heartbeat('TASK-X','other')
            self.assertEqual(s.heartbeat('TASK-X','w')['lease_owner'],'w')
