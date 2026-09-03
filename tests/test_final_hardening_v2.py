import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from flutter_foundry.assurance import verify_assurance_archive
from flutter_foundry.hardening import adversarial_self_test
from flutter_foundry.maintenance import deep_doctor
from flutter_foundry.maturity import implementation_coverage
from flutter_foundry.worktrees import create_isolated_worktree


class FinalHardeningTests(unittest.TestCase):
    def test_adversarial_self_test_passes(self):
        r = adversarial_self_test()
        self.assertEqual(r["status"], "pass")
        self.assertEqual(r["passed"], r["total"])
        self.assertGreaterEqual(r["total"], 8)

    def test_assurance_verifier_rejects_archive_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.zip"
            manifest={"schema":"foundry/assurance-archive/v2","artifacts":[]}
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("manifest.json",json.dumps(manifest))
                z.writestr("../escape.txt","bad")
            r=verify_assurance_archive(p)
            self.assertEqual(r["status"],"fail")
            self.assertTrue(any("unsafe archive path" in x for x in r["findings"]))

    def test_deep_doctor_does_not_turn_missing_sdk_into_false_success(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch("flutter_foundry.environment.shutil.which", return_value=None), patch("flutter_foundry.environment.importlib.util.find_spec", return_value=None):
                r=deep_doctor(root)
            self.assertIn(r["status"], {"pass_with_gaps", "pass"})
            self.assertEqual(r["checks"]["environment"]["status"], "partial")
            self.assertNotEqual(r["checks"]["environment"]["status"], "ready")

    def test_implementation_coverage_includes_hardening(self):
        package=Path(__file__).resolve().parents[1]/"src/flutter_foundry"
        r=implementation_coverage(package)
        self.assertEqual(r["average"],10.0)
        names=[x["criterion"] for group in r["criteria"].values() for x in group]
        self.assertIn("scheduler schema migrations + recovery", names)
        self.assertIn("ledger anchoring receipt", names)
        self.assertIn("reproducible wheel + clean install smoke", names)

if __name__=="__main__": unittest.main()
