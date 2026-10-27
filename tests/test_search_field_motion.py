"""Search-field typing cadence and interaction-layer regressions."""
import json
from pathlib import Path
import tempfile
import unittest

from reels_maker.studio import load_studio


class SearchFieldMotionTests(unittest.TestCase):
    def test_natural_typing_uses_measured_cursor_and_focus_feedback(self):
        with tempfile.TemporaryDirectory(prefix="search-motion-") as temp:
            root = Path(temp)
            manifest = root / "search-demo.json"
            manifest.write_text(json.dumps({
                "name": "search-motion",
                "style": "editorial-premium",
                "video": {"width": 720, "height": 1280, "fps": 30},
                "scenes": [{
                    "type": "search_canvas", "duration": 5.0,
                    "search_field": {
                        "query": "Jak działa energia?",
                        "typing_profile": "human",
                        "focus_outline": True,
                        "blink_period": .36,
                    },
                }],
            }), encoding="utf-8")
            project = load_studio(manifest, root=root)
            scene = project.build()[0]
            from reels_maker.qa.report import audit
            qa = audit(project, [scene], project.timeline(),
                       samples_per_scene=3, strict=True)
            self.assertEqual(qa["variety"]["compositions"], {"search_canvas": 1})
            self.assertIn("search-field", scene.elements)
            self.assertIn("search-query", scene.elements)
            self.assertIn("search-cursor", scene.elements)
            self.assertIn("search-focus-outline", scene.elements)

            query_track = scene.elements["search-query"].tracks[
                "prop.character_progress"]
            gaps = [right.time - left.time
                    for left, right in zip(query_track.keys, query_track.keys[1:])]
            self.assertGreater(max(gaps), min(gaps))
            cursor_track = scene.elements["search-cursor"].tracks["dx"]
            self.assertEqual([key.time for key in cursor_track.keys],
                             [key.time for key in query_track.keys])

    def test_typing_profile_and_focus_options_fail_closed(self):
        for field in (
            {"query": "abc", "typing_profile": "random"},
            {"query": "abc", "focus_outline": "sometimes"},
        ):
            with tempfile.TemporaryDirectory(prefix="search-motion-invalid-") as temp:
                root = Path(temp)
                manifest = root / "search-invalid.json"
                manifest.write_text(json.dumps({
                    "name": "search-motion",
                    "style": "editorial-premium",
                    "video": {"width": 720, "height": 1280, "fps": 30},
                    "scenes": [{"type": "search_canvas", "duration": 4.0,
                                "search_field": field}],
                }), encoding="utf-8")
                with self.subTest(field=field), self.assertRaises(ValueError):
                    load_studio(manifest, root=root).build()


if __name__ == "__main__":
    unittest.main()
