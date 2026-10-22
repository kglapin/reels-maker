"""Asset review prevents accidental double branding over finished promo videos."""
import json
import tempfile
import unittest
from pathlib import Path

from reels_maker.asset_reviews import load_media_reviews
from reels_maker.quality import review_project
from reels_maker.spec import Project


class MediaReviewTests(unittest.TestCase):
    def test_finished_promo_is_flagged_for_brand_overlay(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            review=root/"brands/demo/media/asset-reviews.json"
            review.parent.mkdir(parents=True)
            review.write_text(json.dumps({
                "schema_version":1,
                "assets":{"media/finished.mp4":{
                    "type":"finished_promo","burned_in":["logo","captions"]
                }}
            }))
            p=Project(name="bad",width=720,height=1280,fps=25,
                scenes=[{"file":"media/finished.mp4","duration":3.5,
                         "title":{"headline":"Nowy napis"}}],
                music=None,branding={},output="out.mp4",brand="demo")
            report=review_project(p,root=root)
            self.assertEqual(report["status"],"review")
            self.assertIn("source_is_prebranded",
                [w["code"] for w in report["warnings"]])

    def test_unreviewed_media_is_not_falsely_assumed_to_be_prebranded(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Project(name="good",width=720,height=1280,fps=25,
                scenes=[{"file":"media/clean.mp4","duration":3.5,
                         "title":{"headline":"Energia"}}],
                music=None,branding={},output="out.mp4",brand="demo")
            r=review_project(p,root=Path(folder))
            self.assertNotIn("source_is_prebranded",
                [w["code"] for w in r["warnings"]])

    def test_invalid_review_data_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            path=root/"brands/demo/media/asset-reviews.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"schema_version":1,
                "assets":{"../other.mp4":{"type":"finished_promo","burned_in":["logo"]}}}))
            with self.assertRaises(ValueError):
                load_media_reviews("demo",root)

    def test_actual_asta_sources_are_marked(self):
        root=Path(__file__).resolve().parents[1]
        if not (root/"brands/asta-energy/media/asset-reviews.json").exists():
            self.skipTest("Brand review file missing in sparse checkout")
        records=load_media_reviews("asta-energy",root)
        self.assertEqual(
            records["media/footage/8_asta-pila-realizacja-30kwp.mp4"]["type"],
            "finished_promo")


if __name__=="__main__":
    unittest.main()
