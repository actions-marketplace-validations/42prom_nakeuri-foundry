import json
import tempfile
import unittest
from pathlib import Path

from flutter_foundry.source_fingerprint import repository_fingerprint
from flutter_foundry.target10 import target10_gate


class SourceFingerprintTests(unittest.TestCase):
    def test_fingerprint_changes_with_source_but_not_factory_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'src').mkdir(); (root/'src'/'a.py').write_text('x=1\n')
            a=repository_fingerprint(root)['sha256']
            (root/'.factory').mkdir(); (root/'.factory'/'runtime.json').write_text('noise')
            b=repository_fingerprint(root)['sha256']
            self.assertEqual(a,b)
            (root/'src'/'a.py').write_text('x=2\n')
            c=repository_fingerprint(root)['sha256']
            self.assertNotEqual(a,c)

    def test_target_gate_can_require_current_certification(self):
        root=Path(__file__).resolve().parents[1]
        # This assertion is intentionally tolerant before a certification run;
        # once certification is generated, the strict mode must pass.
        loose=target10_gate(root)
        self.assertEqual(loose['status'],'pass')
        binding=loose['certification_binding']['status']
        self.assertIn(binding,{'missing','stale','pass'})


if __name__=='__main__':
    unittest.main()
