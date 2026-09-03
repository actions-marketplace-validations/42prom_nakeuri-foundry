import unittest
from unittest.mock import patch
from flutter_foundry.agent_runtime import OpenHandsAgentExecutor, runtime_status

class T(unittest.TestCase):
    @patch('flutter_foundry.agent_runtime.importlib.util.find_spec', side_effect=ModuleNotFoundError('openhands'))
    def test_missing_parent_package_is_cleanly_unavailable(self, _find):
        self.assertFalse(OpenHandsAgentExecutor.available())
        self.assertFalse(runtime_status()['openhands_sdk'])

if __name__=='__main__': unittest.main()
