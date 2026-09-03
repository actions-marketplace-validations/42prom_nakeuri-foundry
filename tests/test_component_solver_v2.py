import unittest
from flutter_foundry.component_solver import solve_components
class T(unittest.TestCase):
    def test_auth_contract_aggregates_risk_and_tags(self):
        out=solve_components(['auth-session'],['android','ios'],'RELEASE'); self.assertEqual(out['status'],'pass'); self.assertIn(out['aggregate_risk'],{'HIGH','RELEASE'}); self.assertIn('auth',out['security_tags'])
    def test_platform_incompatibility_blocks(self):
        out=solve_components(['camera'],['server'],'RELEASE'); self.assertEqual(out['status'],'fail')
