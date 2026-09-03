import subprocess,tempfile,unittest
from pathlib import Path
from flutter_foundry.worktrees import create_isolated_worktree,require_worker_commit

def init(root):
    subprocess.run(['git','init','-q'],cwd=root,check=True);subprocess.run(['git','config','user.email','a@b.c'],cwd=root,check=True);subprocess.run(['git','config','user.name','T'],cwd=root,check=True)
    (root/'a').write_text('1');subprocess.run(['git','add','.'],cwd=root,check=True);subprocess.run(['git','commit','-qm','base'],cwd=root,check=True)
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
class T(unittest.TestCase):
    def test_dirty_source_blocks_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);init(r);(r/'a').write_text('dirty');self.assertEqual(create_isolated_worktree(r,'TASK-X')['status'],'fail')
    def test_worker_must_commit(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);base=init(r);out=create_isolated_worktree(r,'TASK-X');w=Path(out['worktree']);self.assertEqual(require_worker_commit(w,base)['status'],'fail');(w/'b').write_text('2');subprocess.run(['git','add','.'],cwd=w,check=True);subprocess.run(['git','commit','-qm','work'],cwd=w,check=True);self.assertEqual(require_worker_commit(w,base)['status'],'pass')
