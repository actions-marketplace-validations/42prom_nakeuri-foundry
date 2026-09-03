import tempfile, unittest
from pathlib import Path
from flutter_foundry.evidence_ledger import EvidenceLedger

class T(unittest.TestCase):
    def test_chain_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as d:
            l=EvidenceLedger(Path(d)); l.append({'kind':'acceptance','result':'PASS'},'worker'); l.append({'kind':'runtime','result':'PASS'},'verifier')
            self.assertTrue(all(line.strip() for line in l.path.read_text().splitlines()))
            self.assertEqual(l.verify()['status'],'pass')
            p=l.path; lines=p.read_text().splitlines(); lines[0]=lines[0].replace('worker','evil'); p.write_text('\n'.join(lines)+'\n')
            self.assertEqual(l.verify()['status'],'fail')
