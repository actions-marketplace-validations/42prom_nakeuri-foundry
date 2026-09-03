import unittest
from flutter_foundry.requirements import compile_requirements

class RequirementCompilerTest(unittest.TestCase):
    def test_auth_offline_resolves_contracts(self):
        out = compile_requirements("Android and iOS app with login and offline sync to backend API")
        self.assertIn("auth-session", out["inferred_components"])
        self.assertIn("offline-outbox", out["inferred_components"])
        self.assertTrue(out["acceptance_criteria"])

if __name__ == "__main__": unittest.main()
