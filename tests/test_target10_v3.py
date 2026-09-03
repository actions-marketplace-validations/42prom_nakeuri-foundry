import tempfile
import unittest
from pathlib import Path

from flutter_foundry.environment import environment_status
from flutter_foundry.target10 import target10_gate


class Target10V3Tests(unittest.TestCase):
    def test_target_10_gate_reaches_repository_target_without_claiming_external_superiority(self):
        root = Path(__file__).resolve().parents[1]
        report = target10_gate(root)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["implementation"]["average"], 10.0)
        self.assertEqual(report["implementation"]["passed"], report["implementation"]["total"])
        self.assertGreaterEqual(report["implementation"]["total"], 80)
        self.assertEqual(report["benchmark"]["count"], 500)
        self.assertIn(report["external_empirical"]["status"], {"not_yet_proven", "proven"})
        if report["external_empirical"]["status"] == "not_yet_proven":
            self.assertTrue(report["external_empirical"]["gaps"])
        self.assertIn("environment_readiness", report["external_empirical"])
        self.assertFalse(report["external_empirical"]["checks"]["live_kubernetes_runtime"])

    def test_environment_separates_universal_core_from_flutter_profile(self):
        report = environment_status(Path('.'), probe_docker=False)
        self.assertIn("universal_core_missing", report)
        self.assertIn("flutter_profile_missing", report)
        self.assertIn("universal_core_status", report)
        self.assertIn("flutter_profile_status", report)
        self.assertIn("node", report["tools"])
        self.assertIn("kubectl", report["tools"])
        self.assertIn("cosign", report["tools"])


if __name__ == '__main__':
    unittest.main()
