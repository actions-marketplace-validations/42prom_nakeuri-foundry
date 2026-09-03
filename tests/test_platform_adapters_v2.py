import json,tempfile,unittest
from pathlib import Path
from flutter_foundry.platform_adapters import detect_platforms,adapter_report
class T(unittest.TestCase):
    def test_detects_multi_surface(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'pubspec.yaml').write_text('name: x');(r/'package.json').write_text('{}');(r/'pyproject.toml').write_text('[project]\nname="x"')
            self.assertEqual(detect_platforms(r),['flutter','node','python']);self.assertEqual(adapter_report(r)['status'],'pass')
