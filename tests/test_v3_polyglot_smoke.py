import unittest
from flutter_foundry.polyglot_smoke import run_polyglot_smoke
class V3PolyglotSmokeTests(unittest.TestCase):
    def test_polyglot_full_control_plane_smoke(self):
        r=run_polyglot_smoke(); self.assertEqual(r['status'],'pass'); self.assertEqual(r['passed'],r['total'])
