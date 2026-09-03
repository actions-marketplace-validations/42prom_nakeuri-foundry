import unittest
from flutter_foundry.team import role_plan
class T(unittest.TestCase):
    def test_high_has_independent_roles_and_human_merge(self):
        p=role_plan('HIGH','auth');self.assertIn('security-reviewer',p['roles']);self.assertTrue(p['human_merge_required']);self.assertEqual(p['writer'],'worker')
    def test_low_avoids_overstaffing(self):
        self.assertEqual(role_plan('LOW')['roles'],['worker'])
