import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from flutter_foundry.security_assurance import run_security_assurance

class T(unittest.TestCase):
    @patch("flutter_foundry.security_assurance.shutil.which", return_value=None)
    def test_release_missing_tools_is_gap_not_pass(self, _which):
        with tempfile.TemporaryDirectory() as td:
            x=run_security_assurance(Path(td),release=True)
            self.assertEqual(x["status"],"pass_with_gaps")
            self.assertIn("gitleaks",x["missing_tools"]);self.assertIn("osv-scanner",x["missing_tools"])
    @patch("flutter_foundry.security_assurance.shutil.which", return_value=None)
    def test_standard_missing_optional_tools_does_not_fake_scan(self, _which):
        with tempfile.TemporaryDirectory() as td:
            x=run_security_assurance(Path(td),release=False)
            self.assertEqual(x["status"],"pass")
            self.assertEqual(x["scans"],[])

if __name__=='__main__':unittest.main()
