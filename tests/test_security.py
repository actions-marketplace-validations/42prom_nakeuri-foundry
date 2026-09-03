import tempfile, unittest
from pathlib import Path
from flutter_foundry.security import scan_project

class SecurityTest(unittest.TestCase):
    def test_secret_detection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root/"lib").mkdir()
            (root/"lib"/"x.dart").write_text('const apiKey = "abcdefghijklmnopqrstuvwx";')
            out = scan_project(root)
            self.assertEqual(out["status"], "fail")
            self.assertTrue(any(f["rule"] == "generic-api-key" for f in out["findings"]))

if __name__ == "__main__": unittest.main()
