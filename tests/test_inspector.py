import tempfile, unittest
from pathlib import Path
from flutter_foundry.project_inspector import inspect_project

class InspectorTest(unittest.TestCase):
    def test_detects_flutter_and_features(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"pubspec.yaml").write_text('name: demo\ndependencies:\n  flutter:\n    sdk: flutter\n  dio: ^5.0.0\n  flutter_riverpod: ^3.0.0\n')
            (root/"lib/features/auth").mkdir(parents=True)
            out=inspect_project(root)
            self.assertTrue(out["is_flutter"])
            self.assertIn("auth",out["features"])
            self.assertTrue(out["architecture_hints"]["riverpod"])

if __name__ == "__main__": unittest.main()
