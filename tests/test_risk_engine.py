import unittest
from flutter_foundry.risk_engine import classify_risk

class RiskTest(unittest.TestCase):
    def test_trivial_ui_is_low(self):
        self.assertEqual(classify_risk("change button padding").level, "low")

    def test_auth_is_high_or_release(self):
        self.assertIn(classify_risk("change OAuth token refresh and secure storage", 4, 8).level, {"high","release"})

if __name__ == "__main__": unittest.main()
