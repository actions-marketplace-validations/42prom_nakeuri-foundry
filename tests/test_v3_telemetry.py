import json,tempfile,unittest
from pathlib import Path
from flutter_foundry.telemetry import foundry_event, append_event

class V3TelemetryTests(unittest.TestCase):
    def test_vendor_neutral_event_has_otel_core_attributes(self):
        e=foundry_event('foundry.task.started',attributes={'task.id':'T1'})
        self.assertIn('service.name',e['attributes']); self.assertEqual(len(e['trace_id']),32)
        with tempfile.TemporaryDirectory() as d:
            p=append_event(Path(d),e); self.assertTrue(p.exists()); self.assertEqual(json.loads(p.read_text().strip())['name'],'foundry.task.started')
