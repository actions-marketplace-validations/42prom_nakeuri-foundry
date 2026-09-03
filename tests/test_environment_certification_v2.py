import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flutter_foundry.environment import environment_status

class T(unittest.TestCase):
    @patch('flutter_foundry.environment.importlib.util.find_spec', return_value=object())
    @patch('flutter_foundry.environment.shutil.which')
    def test_environment_separates_availability_from_evidence(self, which, _find):
        which.side_effect=lambda name: f'/bin/{name}'
        r=environment_status(Path('.'),probe_docker=False)
        self.assertEqual(r['status'],'ready')
        self.assertIn('not proof',r['rule'])
        self.assertEqual(r['docker']['daemon'],'not_probed')

    @patch('flutter_foundry.environment.importlib.util.find_spec', return_value=None)
    @patch('flutter_foundry.environment.shutil.which', return_value=None)
    def test_environment_reports_release_gaps(self, _which, _find):
        r=environment_status(Path('.'))
        self.assertEqual(r['status'],'partial')
        self.assertIn('gitleaks',r['release_gaps'])
        self.assertIn('mcp-python-sdk',r['core_missing'])

if __name__=='__main__': unittest.main()
