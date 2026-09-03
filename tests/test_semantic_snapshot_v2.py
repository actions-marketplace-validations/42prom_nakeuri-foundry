import subprocess,tempfile,unittest
from pathlib import Path
from flutter_foundry.semantic_snapshot import write_snapshot
from flutter_foundry.blast_radius import blast_radius
class T(unittest.TestCase):
 def test_blast_prefers_commit_bound_semantics(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);subprocess.run(['git','init','-q'],cwd=r,check=True);subprocess.run(['git','config','user.email','a@b.c'],cwd=r,check=True);subprocess.run(['git','config','user.name','T'],cwd=r,check=True);(r/'x').write_text('x');subprocess.run(['git','add','.'],cwd=r,check=True);subprocess.run(['git','commit','-qm','init'],cwd=r,check=True)
   write_snapshot(r,[{'name':'Foo','path':'lib/a.dart'}],[{'symbol':'Foo','path':'lib/b.dart'}]);out=blast_radius(r,'Foo');self.assertEqual(out['source'],'semantic-snapshot');self.assertEqual(out['files'],2)
