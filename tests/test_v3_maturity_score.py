import unittest
from pathlib import Path
from flutter_foundry.v3_maturity import v3_implementation_score

class V3MaturityTests(unittest.TestCase):
    def test_v3_implementation_model_is_explicitly_not_empirical(self):
        package=Path(__file__).resolve().parents[1]/'src'/'flutter_foundry'
        r=v3_implementation_score(package)
        self.assertEqual(len(r['scores']),10)
        self.assertIn('polyglot_expertise',r['scores'])
        self.assertIn('not real-world peer superiority',r['scope'])
