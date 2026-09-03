import json,tempfile,unittest
from pathlib import Path
from flutter_foundry.change_intent import validate_change_intent
class T(unittest.TestCase):
 def test_forbidden_file_blocks(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'.factory').mkdir();p=r/'.factory/change-intent.json';p.write_text(json.dumps({'allowed_globs':['lib/**'],'must_not_change_globs':['lib/theme/**']}))
   self.assertEqual(validate_change_intent(r,files=['lib/theme/colors.dart'])['status'],'fail')
