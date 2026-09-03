import unittest
from unittest.mock import patch
from flutter_foundry.cli import doctor_status

class T(unittest.TestCase):
    @patch("flutter_foundry.cli.importlib.util.find_spec", return_value=object())
    @patch("flutter_foundry.cli.shutil.which")
    def test_ready_requires_git_dart_flutter_and_mcp(self, which, _find_spec):
        which.side_effect=lambda name: f"/bin/{name}"
        result=doctor_status()
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["missing"], [])

    @patch("flutter_foundry.cli.importlib.util.find_spec", return_value=None)
    @patch("flutter_foundry.cli.shutil.which")
    def test_partial_reports_missing(self, which, _find_spec):
        which.side_effect=lambda name: "/bin/git" if name == "git" else None
        result=doctor_status()
        self.assertEqual(result["status"], "partial")
        self.assertIn("dart", result["missing"])
        self.assertIn("flutter", result["missing"])
        self.assertIn("mcp-python-sdk", result["missing"])
