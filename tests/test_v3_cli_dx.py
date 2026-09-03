import unittest
from flutter_foundry.cli import _exit_code, parser

class V3CLITests(unittest.TestCase):
    def test_deterministic_ci_exit_codes(self):
        self.assertEqual(_exit_code({'status':'pass'}),0)
        self.assertEqual(_exit_code({'status':'warn'}),10)
        self.assertEqual(_exit_code({'status':'blocked'}),20)
        self.assertEqual(_exit_code({'status':'fail'}),30)
        self.assertEqual(_exit_code({'status':'pass_with_gaps'}),10)

    def test_allow_gaps_is_explicit_global_ci_policy(self):
        args = parser().parse_args(['--ci', '--allow-gaps', '--compact', 'verify', '.', '--profile', 'release'])
        self.assertTrue(args.ci)
        self.assertTrue(args.allow_gaps)
        self.assertEqual(args.profile, 'release')
