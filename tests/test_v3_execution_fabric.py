import unittest
from flutter_foundry.execution_fabric import choose_provider, authorize_side_effect, network_policy_for, secret_broker_policy

class V3FabricTests(unittest.TestCase):
    def test_risk_routing_never_treats_worktree_as_release_sandbox(self):
        self.assertEqual(choose_provider('LOW', docker_healthy=False)['provider']['id'],'worktree')
        self.assertEqual(choose_provider('RELEASE', preferred='worktree')['status'],'blocked')
        self.assertEqual(choose_provider('HIGH', docker_healthy=True)['provider']['id'],'docker')
    def test_privileged_side_effect_needs_human_and_proof(self):
        self.assertEqual(authorize_side_effect('deploy-production',risk='RELEASE')['status'],'blocked')
        self.assertEqual(authorize_side_effect('deploy-production',risk='RELEASE',human_approved=True,proof_status='PASS')['status'],'pass')
    def test_high_risk_network_and_secrets_are_zero_trust(self):
        self.assertTrue(network_policy_for('HIGH')['deny_unknown'])
        p=secret_broker_policy('production'); self.assertFalse(p['raw_secret_to_model']); self.assertTrue(p['production_requires_human_approval'])
