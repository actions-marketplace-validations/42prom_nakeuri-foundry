import tempfile
import unittest
from pathlib import Path
from flutter_foundry.sbom import cyclonedx_from_pub_deps, generate_cyclonedx_from_pub_deps
import json

class T(unittest.TestCase):
    def sample(self):
        return {"roots":["app"],"packages":[
            {"name":"app","version":"1.0.0","dependencies":["dio"],"devDependencies":["test"],"source":"root"},
            {"name":"dio","version":"5.8.0","dependencies":[],"source":"hosted"},
            {"name":"test","version":"1.25.0","dependencies":[],"source":"hosted"},
        ]}
    def test_valid_cyclonedx_shape_and_edges(self):
        bom=cyclonedx_from_pub_deps(self.sample())
        self.assertEqual(bom["bomFormat"],"CycloneDX");self.assertEqual(bom["specVersion"],"1.6")
        app=next(c for c in bom["components"] if c["name"]=="app")
        self.assertEqual(app["type"],"application")
        dep=next(x for x in bom["dependencies"] if x["ref"]==app["bom-ref"])
        self.assertEqual(len(dep["dependsOn"]),2)
    def test_file_generation(self):
        with tempfile.TemporaryDirectory() as td:
            inp=Path(td)/"deps.json";out=Path(td)/"bom.cdx.json"
            inp.write_text(json.dumps(self.sample()))
            result=generate_cyclonedx_from_pub_deps(inp,out)
            self.assertEqual(result["status"],"pass");self.assertTrue(out.is_file())

if __name__=='__main__':unittest.main()
