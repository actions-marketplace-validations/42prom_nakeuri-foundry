import unittest
from pathlib import Path
from flutter_foundry.maturity import implementation_coverage,empirical_ceiling
class T(unittest.TestCase):
    def test_implementation_is_separate_from_empirical(self):
        pkg=Path(__file__).parents[1]/'src/flutter_foundry';impl=implementation_coverage(pkg);self.assertGreaterEqual(impl['average'],9.0)
        empirical=empirical_ceiling({});self.assertEqual(empirical['average'],0.0)
