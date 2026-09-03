import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flutter_foundry.store_delivery import init_store_delivery, validate_store_delivery, store_delivery_preflight, execute_store_delivery


class T(unittest.TestCase):
    def test_disabled_default_is_not_release_ready(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); init_store_delivery(root)
            result = validate_store_delivery(root)
            self.assertEqual(result["status"], "fail")
            self.assertIn("no store delivery target is enabled", result["findings"])

    def test_android_contract_uses_env_name_not_secret_value(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); p = init_store_delivery(root)
            data = json.loads(p.read_text())
            data["android"].update({"enabled": True, "package_name": "com.example.app", "track": "internal", "rollout_fraction": 1.0})
            p.write_text(json.dumps(data))
            result = validate_store_delivery(root)
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["config"]["android"]["credential_env"], "PLAY_SERVICE_ACCOUNT_JSON")
            self.assertNotIn("private_key", p.read_text())

    def test_execution_requires_explicit_approval_before_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); init_store_delivery(root)
            result = execute_store_delivery(root, "android", approved=False)
            self.assertEqual(result["status"], "blocked")
            self.assertIn("explicit approval", result["reason"])

    @patch("flutter_foundry.store_delivery._fastlane_prefix", return_value=["fastlane"])
    def test_preflight_reports_missing_artifact_and_credentials(self, _prefix):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); p = init_store_delivery(root)
            data = json.loads(p.read_text())
            data["android"].update({"enabled": True, "package_name": "com.example.app"})
            p.write_text(json.dumps(data))
            with patch.dict(os.environ, {}, clear=True):
                result = store_delivery_preflight(root, "android")
            self.assertEqual(result["status"], "fail")
            self.assertTrue(any("release artifact missing" in x for x in result["findings"]))
            self.assertTrue(any("credential environment variables missing" in x for x in result["findings"]))


if __name__ == "__main__": unittest.main()
