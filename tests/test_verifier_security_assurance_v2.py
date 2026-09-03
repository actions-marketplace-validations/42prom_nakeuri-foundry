import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flutter_foundry.models import CheckResult
from flutter_foundry.verifier import verify_project


class T(unittest.TestCase):
    def _root(self) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        (root / 'pubspec.yaml').write_text('name: demo\n', encoding='utf-8')
        (root / 'pubspec.lock').write_text('# Generated lockfile\n', encoding='utf-8')
        return root

    @patch('flutter_foundry.verifier._run')
    @patch('flutter_foundry.verifier.run_security_assurance')
    @patch('flutter_foundry.verifier.validate_production_ops')
    @patch('flutter_foundry.verifier.scan_supply_chain')
    @patch('flutter_foundry.verifier.verify_invariant_coverage')
    @patch('flutter_foundry.verifier.validate_genome')
    @patch('flutter_foundry.verifier.scan_test_quality')
    @patch('flutter_foundry.verifier.scan_semantic_duplicates')
    @patch('flutter_foundry.verifier.scan_design')
    @patch('flutter_foundry.verifier.scan_clean_code')
    @patch('flutter_foundry.verifier.scan_project')
    @patch('flutter_foundry.verifier.architecture_scan')
    def test_release_security_gap_propagates_to_pass_with_gaps(self, arch, sec, clean, design, dupes, tq, genome, inv, supply, prod, external, run):
        for mock in [arch, sec, clean, design, dupes, tq, genome, inv, supply, prod]:
            mock.return_value = {'status': 'pass'}
        external.return_value = {'status': 'pass_with_gaps', 'missing_tools': ['gitleaks']}
        run.return_value = CheckResult(name='tool', status='pass')
        result = verify_project(self._root(), 'release')
        self.assertEqual(result['status'], 'pass_with_gaps')
        self.assertIn('foundry_security_assurance', result['warnings'])
        self.assertIn('foundry_security_assurance', result['environment_gaps'])

    @patch('flutter_foundry.verifier._run')
    @patch('flutter_foundry.verifier.run_security_assurance')
    @patch('flutter_foundry.verifier.validate_production_ops')
    @patch('flutter_foundry.verifier.scan_supply_chain')
    @patch('flutter_foundry.verifier.verify_invariant_coverage')
    @patch('flutter_foundry.verifier.validate_genome')
    @patch('flutter_foundry.verifier.scan_test_quality')
    @patch('flutter_foundry.verifier.scan_semantic_duplicates')
    @patch('flutter_foundry.verifier.scan_design')
    @patch('flutter_foundry.verifier.scan_clean_code')
    @patch('flutter_foundry.verifier.scan_project')
    @patch('flutter_foundry.verifier.architecture_scan')
    def test_release_external_scanner_failure_blocks(self, arch, sec, clean, design, dupes, tq, genome, inv, supply, prod, external, run):
        for mock in [arch, sec, clean, design, dupes, tq, genome, inv, supply, prod]:
            mock.return_value = {'status': 'pass'}
        external.return_value = {'status': 'fail', 'findings': ['scanner failed']}
        run.return_value = CheckResult(name='tool', status='pass')
        result = verify_project(self._root(), 'release')
        self.assertEqual(result['status'], 'fail')
        self.assertIn('foundry_security_assurance', result['blocking'])


if __name__ == '__main__': unittest.main()
