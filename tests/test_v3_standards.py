import json, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from flutter_foundry.standards import init_standards_radar, standards_status, technology_radar

class V3StandardsTests(unittest.TestCase):
    def test_default_registry_is_current_and_source_aware(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); p=init_standards_radar(r)
            self.assertTrue(p.exists())
            s=standards_status(r, now=datetime(2026,9,2,tzinfo=timezone.utc))
            self.assertEqual(s['status'],'pass')
            radar=technology_radar(r)
            self.assertTrue(any(x['id']=='flutter.ai-stack' for x in radar['ADOPT']))
    def test_draft_cannot_be_default_adopt(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); p=init_standards_radar(r)
            data=json.loads(p.read_text()); data['records'][0]['status']='draft'; data['records'][0]['ring']='ADOPT'; p.write_text(json.dumps(data))
            self.assertEqual(standards_status(r, now=datetime(2026,9,2,tzinfo=timezone.utc))['status'],'fail')
