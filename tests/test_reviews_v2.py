import json, subprocess, tempfile, unittest
from pathlib import Path
from flutter_foundry.reviews import write_review, validate_review

def gitrepo(root:Path):
    subprocess.run(['git','init','-q'],cwd=root,check=True); subprocess.run(['git','config','user.email','a@b.c'],cwd=root,check=True); subprocess.run(['git','config','user.name','T'],cwd=root,check=True)
    (root/'x.txt').write_text('x'); subprocess.run(['git','add','.'],cwd=root,check=True); subprocess.run(['git','commit','-qm','init'],cwd=root,check=True)

class T(unittest.TestCase):
    def test_writer_cannot_review_self(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); gitrepo(r)
            with self.assertRaises(ValueError): write_review(r,'TASK-1','same','same','PASS')
    def test_hash_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); gitrepo(r); rv=write_review(r,'TASK-1','reviewer','writer','PASS')
            self.assertTrue(validate_review(r,rv)[0])
            (r/rv['artifact']).write_text('{}')
            self.assertFalse(validate_review(r,rv)[0])
