import tempfile,unittest
from pathlib import Path
from flutter_foundry.product_compiler import compile_product,write_product_definition
class T(unittest.TestCase):
 def test_hypothesis(self):self.assertEqual(compile_product('Flutter app for customers with login')['status'],'hypothesis')
 def test_write(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);write_product_definition(r,'Flutter app for users');self.assertTrue((r/'.factory/product-definition.json').exists())
