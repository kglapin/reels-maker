"""MD-07 acceptance: brief-to-scene planning that never invents claims."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from reels_maker.planning import (
    PlanningError, ROLE_COMPOSITION, ROLE_REASON, plan_brief)
from reels_maker.qa.report import audit
from reels_maker.studio import load_studio

ROOT = Path(__file__).resolve().parents[1]
FFMPEG = shutil.which("ffmpeg")


def _make_clip(path: Path) -> None:
    subprocess.run([
        FFMPEG, "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc=size=320x240:rate=20:duration=4",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
    ], check=True, capture_output=True)


def _brand(root: Path, slug: str, clips: dict[str, str]) -> None:
    stock = root / "brands" / slug / "media" / "stock"
    stock.mkdir(parents=True)
    for name in clips:
        _make_clip(stock / f"{name}.mp4")
    reviews = {"schema_version": 1, "updated": "2026-10-23", "assets": {}}
    for name, state in clips.items():
        reviews["assets"][f"media/stock/{name}.mp4"] = {
            "type": state, "burned_in": []}
    (root / "brands" / slug / "media" / "asset-reviews.json").write_text(
        json.dumps(reviews, ensure_ascii=False, indent=2), encoding="utf-8")


def _brief(slug: str, *, duration: float = 24.0) -> dict:
    return {
        "name": f"planned-{slug}",
        "brand": slug,
        "duration_s": duration,
        "beats": [
            {"role": "hook", "headline": "JEDNA IDEA",
             "body": "Pierwsza myśl"},
            {"role": "context", "topic": "pv",
             "headline": "OBRAZ KONTEKSTU", "body": "Fotografia prowadzi"},
            {"role": "proof", "headline": "HERO LICZBY", "value": 16000,
             "counter_label": "ETKIETA LICZBY",
             "subtitle": "PODPIS POD LICZBĄ",
             "format": {"suffix": " kWh", "decimals": 0}},
            {"role": "process", "headline": "LISTA KROKÓW",
             "items": ["Krok pierwszy", "Krok drugi"]},
            {"role": "cta", "headline": "KONTAKT TESTOWY",
             "phone": "+00 000 000 000", "line_one": "TAG TESTOWY",
             "website": "example.org"},
        ],
    }


class PlanningBriefTests(unittest.TestCase):
    def test_plan_is_deterministic_and_explainable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _brand(root, "energy", {"pv-aerial-1": "clean_source",
                                    "pv-aerial-2": "clean_source"})
            first = plan_brief(_brief("energy"), root=root)
            second = plan_brief(_brief("energy"), root=root)
            self.assertEqual(json.dumps(first, sort_keys=True),
                             json.dumps(second, sort_keys=True))
            manifest, report = first
            self.assertTrue(report["deterministic"])
            roles = report["roles"]
            self.assertEqual(roles[0]["role"], "hook")
            self.assertEqual(roles[-1]["role"], "cta")
            for entry in roles:
                self.assertTrue(entry["reason"])
                self.assertEqual(entry["composition"],
                                 ROLE_COMPOSITION[entry["role"]])
            self.assertTrue(ROLE_REASON["hook"])
            for choice in report["asset_choices"]:
                self.assertTrue(choice["reason"])
                self.assertEqual(choice["editorial_state"], "clean_source")

    def test_no_regularized_or_prebranded_asset_enter_the_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _brand(root, "energy", {"pv-aerial-1": "clean_source",
                                    "pv-aerial-2": "clean_source",
                                    "pv-promo-cut": "finished_promo"})
            manifest, report = plan_brief(_brief("energy"), root=root)
            chosen = {entry["file"] for entry in report["asset_choices"]}
            self.assertEqual(len(chosen), 1)
            photos = {scene["photo"] for scene in manifest["scenes"]
                      if scene["type"] == "spotlight"}
            self.assertEqual(len(photos), 1)
            self.assertFalse(any("promo" in photo for photo in photos))
            with self.assertRaises(PlanningError):
                brief = _brief("energy")
                brief["beats"][1]["assets"] = {"asset":
                                               "media/stock/pv-promo-cut.mp4"}
                plan_brief(brief, root=root)

    def test_missing_copy_metrics_or_contact_never_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _brand(root, "energy", {"pv-aerial-1": "clean_source"})
            silent_cta = _brief("energy")
            silent_cta["beats"][-1].pop("phone")
            silent_cta["beats"][-1].pop("website")
            with self.assertRaisesRegex(PlanningError, "contact"):
                plan_brief(silent_cta, root=root)
            unverifiable = _brief("energy")
            unverifiable["beats"][2].pop("value")
            with self.assertRaisesRegex(PlanningError, "verified"):
                plan_brief(unverifiable, root=root)
            blocking = _brief("energy")
            blocking["beats"][0].pop("headline")
            with self.assertRaisesRegex(PlanningError, "copy"):
                plan_brief(blocking, root=root)

    def test_pool_exhaustion_is_named_not_worked_around(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _brand(root, "energy", {"pv-aerial-1": "clean_source",
                                    "pv-aerial-2": "clean_source"})
            stretched = _brief("energy")
            stretched["beats"].insert(2, {
                "role": "context", "topic": "pv",
                "headline": "PANORAMA", "body": "Drugi film"})
            stretched["beats"].insert(3, {
                "role": "context", "topic": "pv",
                "headline": "TRZECI UJĘĆ", "body": "Trzeci film"})
            with self.assertRaisesRegex(PlanningError, "eligible"):
                plan_brief(stretched, root=root)

    def test_two_briefs_build_and_pass_qa_without_invented_strings(self):
        for slug, duration in (("energy", 22.0), ("battery", 12.0)):
            with self.subTest(brief=slug):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    clips = ({"pv-aerial": "clean_source"} if slug == "energy"
                             else {"battery-room": "clean_source"})
                    _brand(root, slug, clips)
                    brief = _brief(slug, duration=duration)
                    brief["beats"][1]["topic"] = (
                        "pv" if slug == "energy" else "battery")
                    manifest, report = plan_brief(brief, root=root)
                    manifest_path = root / f"{slug}-draft.json"
                    manifest_path.write_text(
                        json.dumps(manifest, ensure_ascii=False),
                        encoding="utf-8")
                    project = load_studio(manifest_path, root=root)
                    timeline = project.timeline()
                    built = project.build(timeline)
                    self.assertEqual(len(built), report["scene_count"])
                    qa = audit(project, built, timeline, samples_per_scene=4)
                    self.assertTrue(qa["ok"], qa["issues"])
                    self.assertAlmostEqual(
                        sum(scene["duration"] for scene in manifest["scenes"]),
                        duration, delta=.6)
                    self.assertLessEqual(
                        report["duration_planned"], duration + .01)
                    full_text = json.dumps(manifest, ensure_ascii=False)
                    for banned in ("ZADZWOŃ LUB NAPISZ", "NA MAGAZYN ENERGII",
                                   "DOTACJA DO", "CO ZYSKUJESZ", "CONTACT",
                                   "example.com"):
                        self.assertNotIn(banned, full_text)
                    # No claim duration may appear that the brief lacks.
                    brief_values = {str(entry["value"]) for entry
                                    in brief["beats"] if "value" in entry}
                    for scene in manifest["scenes"]:
                        if scene["type"] == "amount":
                            self.assertIn(str(int(scene["value"])),
                                          brief_values)
                    self.assertEqual(
                        [scene["type"] for scene in manifest["scenes"]],
                        ["statement", "spotlight", "amount", "checklist",
                         "cta"])

    def test_md405_format_matrix_and_md406_end_to_end_delivery(self):
        from reels_maker.data_renderer import credible_data_story_examples
        from reels_maker.planning import run_end_to_end_delivery
        from reels_maker.renderers.studio import render_master_format_matrix
        from reels_maker.studio import load_studio

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _brand(root, "energy", {"pv-aerial": "clean_source"})
            brief = _brief("energy", duration=12.0)
            pv_story = credible_data_story_examples()["pv_generation_annual"]["scenes"]
            out_mp4 = root / "renders" / "e2e.mp4"
            e2e = run_end_to_end_delivery(
                brief, root=root, output_mp4=out_mp4,
                extra_data_scenes=pv_story, render=False,
            )
            self.assertTrue(e2e["ok"])
            self.assertEqual(len(e2e["provenance_ledger"]["data_provenance"]), 1)

            project = load_studio(Path(e2e["manifest_path"]), root=root)
            # Render a fast 1-scene project across portrait/square/landscape matrix
            from dataclasses import replace
            mini_project = replace(project, scenes=project.scenes[:1])
            matrix = render_master_format_matrix(
                mini_project, root / "matrix",
                formats=("portrait", "square", "landscape"),
            )
            self.assertTrue(matrix["ok"])
            self.assertEqual(set(matrix["deliveries"]), {"portrait", "square", "landscape"})


if __name__ == "__main__":
    unittest.main()
