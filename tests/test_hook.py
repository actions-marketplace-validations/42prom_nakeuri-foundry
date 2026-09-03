import unittest
from flutter_foundry.hook import pretool

class HookTest(unittest.TestCase):
    def payload(self, command):
        return {"toolCall":{"name":"run_command","args":{"CommandLine":command}}}
    def test_force_push_main_denied(self):
        self.assertEqual(pretool(self.payload("git push origin main --force"))["decision"],"deny")
    def test_normal_test_allowed(self):
        self.assertEqual(pretool(self.payload("flutter test"))["decision"],"allow")
    def test_release_build_asks(self):
        self.assertEqual(pretool(self.payload("flutter build appbundle --release"))["decision"],"force_ask")

if __name__ == "__main__": unittest.main()
