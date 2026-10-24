"""CLI-level integration checks for Creative Engine and immutable revisions."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from reels_maker.cli import main

class CreativeCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.dir=Path(self.tmp.name)
        (self.dir/"assets").mkdir()
        Image.new("RGB",(600,800),(42,83,126)).save(self.dir/"assets"/"photo.png")
        self.spec=self.dir/"project.json"
        self.spec.write_text(json.dumps({
            "creative_schema_version":1,"name":"cli-project","mode":"camera_canvas",
            "shots":[{"id":"first","headline":"THE FIRST SHOT","asset":"assets/photo.png",
                      "duration":3.1}],
            "video":{"width":360,"height":640,"fps":24},
        }),encoding="utf-8")
    def tearDown(self):
        self.tmp.cleanup()
    def invoke(self,*args):
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            code=main(list(args))
        stream=out.getvalue() if code==0 else err.getvalue()
        return code,json.loads(stream)
    def test_capabilities_cli(self):
        code,report=self.invoke("creative-capabilities","--json")
        self.assertEqual(code,0)
        self.assertTrue(report["ok"])
        self.assertIn("camera_canvas",report["modes"])
        self.assertEqual(report["schema_version"],2)
        self.assertIn("providers",report)
        self.assertIn("icon_packs",report)
    def test_json_schema_cli(self):
        code,report=self.invoke("creative-schema","--json")
        self.assertEqual(code,0)
        self.assertEqual(report["json_schema"]["properties"]["creative_schema_version"]["const"],1)
    def test_compile_cli_to_manifest(self):
        target=self.dir/"test.studio.json"
        code,report=self.invoke("creative-compile",str(self.spec),"--output",str(target),"--json")
        self.assertEqual(code,0,report)
        self.assertTrue(target.is_file())
        loaded=json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(loaded["scenes"][0]["headline"],"THE FIRST SHOT")
        self.assertIn("camera_canvas",loaded["scenes"][0])
    def test_edit_cli_writes_new_spec(self):
        patch=self.dir/"patch.json"
        patch.write_text(json.dumps([
            {"op":"replace","path":"/shots/@first/headline","value":"A BETTER SHOT"}
        ]),encoding="utf-8")
        output=self.dir/"project-v2.json"
        code,report=self.invoke("creative-edit",str(self.spec),str(patch),
                                "--output",str(output),"--json")
        self.assertEqual(code,0,report)
        self.assertTrue(output.is_file())
        self.assertEqual(json.loads(output.read_text())["shots"][0]["headline"],
                         "A BETTER SHOT")
        self.assertEqual(json.loads(self.spec.read_text())["shots"][0]["headline"],
                         "THE FIRST SHOT")
    def test_missing_media_fails_before_manifest_write(self):
        spec=json.loads(self.spec.read_text())
        spec["shots"][0]["asset"]="assets/nope.jpg"
        self.spec.write_text(json.dumps(spec))
        target=self.dir/"should-not-exist.studio.json"
        code,report=self.invoke("creative-compile",str(self.spec),"--output",
                                str(target),"--json")
        self.assertEqual(code,2)
        self.assertFalse(target.exists())
        self.assertFalse(report["ok"])

if __name__=="__main__":
    unittest.main()
