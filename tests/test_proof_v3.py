import subprocess,tempfile,unittest
from pathlib import Path
from flutter_foundry.proof import build_proof,validate_proof
from flutter_foundry.reviews import write_review

def init(root):
    subprocess.run(['git','init','-q'],cwd=root,check=True);subprocess.run(['git','config','user.email','a@b.c'],cwd=root,check=True);subprocess.run(['git','config','user.name','T'],cwd=root,check=True);(root/'x').write_text('x');subprocess.run(['git','add','.'],cwd=root,check=True);subprocess.run(['git','commit','-qm','init'],cwd=root,check=True)
class T(unittest.TestCase):
    def test_high_requires_real_pass_and_independent_review(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);init(r);v={'status':'pass_with_gaps','blocking':[]};p=build_proof(r,'TASK-X','x',{'level':'HIGH'},v,writer='worker');self.assertEqual(p['result'],'FAIL')
            v={'status':'pass','blocking':[]};rv=write_review(r,'TASK-X','reviewer','worker','PASS');p=build_proof(r,'TASK-X','x',{'level':'HIGH'},v,reviews=[rv],writer='worker');self.assertEqual(p['result'],'PASS');self.assertEqual(validate_proof(r,p)['status'],'pass')
