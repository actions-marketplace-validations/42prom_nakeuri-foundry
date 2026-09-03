import json,tempfile,unittest
from pathlib import Path
from flutter_foundry.bootstrap import bootstrap_project

class T(unittest.TestCase):
    def test_bootstrap_uses_nakeuri_plugin_and_schema(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"pubspec.yaml").write_text("name: demo\n", encoding="utf-8")
            result=bootstrap_project(root)
            plugin=root/".agents"/"plugins"/"nakeuri-flutter-foundry"/"plugin.json"
            self.assertTrue(plugin.exists())
            self.assertEqual(json.loads(plugin.read_text())["name"], "nakeuri-flutter-foundry")
            mcp=json.loads((root/".agents"/"mcp_config.json").read_text())
            self.assertIn("nakeuri-flutter-foundry", mcp["mcpServers"])
            config=json.loads((root/".factory"/"config.json").read_text())
            self.assertEqual(config["schema"], "nakeuri-flutter-foundry/project/v3")
            self.assertIn("nakeuri-flutter-foundry", result["plugin"])
