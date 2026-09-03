import tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from flutter_foundry.distributed_runtime import WorkerCapability, WorkerRegistry

class V3DistributedRuntimeTests(unittest.TestCase):
    def test_worker_placement_respects_risk_platform_provider(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); reg=WorkerRegistry(r)
            reg.register(WorkerCapability('w1','host1',('docker',),('flutter','python'),'RELEASE',2),ttl_seconds=120)
            reg.register(WorkerCapability('w2','host2',('worktree',),('python',),'MEDIUM',1),ttl_seconds=120)
            self.assertEqual(reg.select(risk='HIGH',platform='flutter',provider='docker')['worker']['worker_id'],'w1')
            self.assertEqual(reg.select(risk='HIGH',platform='python',provider='worktree')['status'],'blocked')
    def test_expired_worker_is_not_selected(self):
        with tempfile.TemporaryDirectory() as d:
            reg=WorkerRegistry(Path(d)); reg.register(WorkerCapability('w','h',('docker',),('flutter',),'RELEASE'),ttl_seconds=1)
            future=datetime.now(timezone.utc)+timedelta(seconds=5)
            self.assertEqual(reg.eligible(risk='LOW',now=future),[])
