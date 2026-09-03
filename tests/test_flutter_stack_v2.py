import json,tempfile,unittest
from pathlib import Path
from flutter_foundry.flutter_stack import official_stack_status,lock_skills,install_official_skills
class T(unittest.TestCase):
    def test_status_and_lock(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'.agents/skills/x').mkdir(parents=True);(r/'.agents/skills/x/SKILL.md').write_text('x');(r/'.agents/mcp_config.json').write_text(json.dumps({'mcpServers':{'dart':{'command':'dart','args':['mcp-server']}}}))
            self.assertEqual(lock_skills(r)['status'],'pass');s=official_stack_status(r);self.assertTrue(s['dart_mcp_configured']);self.assertTrue(s['skills_lock_valid'])
    def test_network_install_requires_explicit_permission(self):
        with tempfile.TemporaryDirectory() as d:self.assertEqual(install_official_skills(Path(d))['status'],'blocked')
