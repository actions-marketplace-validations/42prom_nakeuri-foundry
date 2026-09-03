import json,tempfile,unittest,zipfile
from pathlib import Path
from flutter_foundry.assurance import build_assurance_archive
class T(unittest.TestCase):
    def test_archive_contains_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'.factory/proofs').mkdir(parents=True);(r/'.factory/proofs/TASK-X.json').write_text('{}');out=build_assurance_archive(r,'TASK-X');self.assertEqual(out['status'],'pass');self.assertTrue(Path(out['archive']).exists());
            with zipfile.ZipFile(out['archive']) as z:
                self.assertIn('manifest.json',z.namelist())
                manifest=json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['artifacts'][0]['path'],'.factory/proofs/TASK-X.json')
                self.assertIn('.factory/proofs/TASK-X.json',z.namelist())
