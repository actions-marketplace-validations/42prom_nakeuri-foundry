import tempfile,unittest
from pathlib import Path
from flutter_foundry.delivery import install_delivery_plane
class T(unittest.TestCase):
 def test_install(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);out=install_delivery_plane(r);self.assertEqual(out['status'],'pass');self.assertTrue((r/'.github/pull_request_template.md').exists())
