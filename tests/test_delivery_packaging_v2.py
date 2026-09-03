import tempfile,unittest
from pathlib import Path
from flutter_foundry.delivery import install_delivery_plane
class T(unittest.TestCase):
    def test_packaged_assets_install_real_workflows(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);o=install_delivery_plane(r);self.assertEqual(o['status'],'pass');text=(r/'.github/workflows/flutter-pr-ci.yml').read_text();self.assertIn('FLUTTER_GIT_REF',text);self.assertNotIn('echo "Use your organization-approved',text)
