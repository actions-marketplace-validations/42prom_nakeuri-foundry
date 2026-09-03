import tempfile, unittest
from pathlib import Path
from flutter_foundry.architecture import architecture_scan

class ArchitectureTest(unittest.TestCase):
    def test_multiple_state_systems_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            root.joinpath('pubspec.yaml').write_text('name: x\ndependencies:\n  flutter:\n    sdk: flutter\n  flutter_riverpod: ^3.0.0\n  flutter_bloc: ^9.0.0\n')
            out=architecture_scan(root)
            self.assertEqual(out['status'],'fail')

if __name__ == '__main__': unittest.main()
