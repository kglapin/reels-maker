"""Coverage for the captured-footage paper-reveal composition."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from reels_maker.components.paper_reveal import sequence_frames
from reels_maker.renderers.scene import RenderOptions, SceneRenderer
from reels_maker.studio import StudioError, load_studio

FRAME_COLOURS = ((220, 40, 40), (40, 180, 60), (40, 60, 220))


class PaperRevealTests(unittest.TestCase):
    def _project(self, base: Path, **scene_overrides) -> Path:
        brand = base / "brands/paper-studio"
        sequence = brand / "imports/tear"
        sequence.mkdir(parents=True)
        (brand / "brand.json").write_text(json.dumps({
            "id": "paper-studio", "name": "Paper Studio",
            "identity": {"palette": {"primary": "#A66F37"}},
        }), encoding="utf-8")
        for index, colour in enumerate(FRAME_COLOURS, start=1):
            Image.new("RGBA", (240, 400), (*colour, 255)).save(
                sequence / f"f_{index:04d}.png")
        manifest = brand / "projects/reveal.json"
        manifest.parent.mkdir(parents=True)
        scene = {
            "id": "reveal", "type": "paper_reveal", "duration": 4.0,
            "headline": "JEST WIĘCEJ", "kicker": "POD SPODEM",
            "subtitle": "ODKRYJ CO KRYJE SIĘ POD POWIERZCHNIĄ",
            "background": {"kind": "solid", "color": "#141C17"},
            "tear_sequence": "imports/tear",
            "tear_fps": 1, "tear_start": 0, "tear_speed": 1,
            **scene_overrides,
        }
        manifest.write_text(json.dumps({
            "brand": "paper-studio", "style": "editorial-premium",
            "video": {"width": 240, "height": 400, "fps": 10},
            "scenes": [scene],
        }), encoding="utf-8")
        return manifest

    def _corner(self, manifest: Path, time: float):
        project = load_studio(manifest, root=manifest.parents[3])
        built = project.build()[0]
        renderer = SceneRenderer(
            project.width, project.height, project.tokens, project.fonts,
            options=RenderOptions(supersample=1, reuse_settled_frames=False))
        return renderer.render(built, time).convert("RGB").getpixel((2, 2))

    def test_sequence_advances_by_time_and_holds_the_requested_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._project(Path(directory))
            self.assertEqual(self._corner(manifest, 0.0), FRAME_COLOURS[0])
            self.assertEqual(self._corner(manifest, 1.0), FRAME_COLOURS[1])
            self.assertEqual(self._corner(manifest, 2.0), FRAME_COLOURS[2])

        with tempfile.TemporaryDirectory() as directory:
            manifest = self._project(Path(directory), tear_hold_frame=2)
            self.assertEqual(self._corner(manifest, 1.0), FRAME_COLOURS[1])
            self.assertEqual(self._corner(manifest, 3.0), FRAME_COLOURS[1])

    def test_sequence_directory_must_stay_inside_the_brand(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._project(Path(directory), tear_sequence="../outside")
            (manifest.parents[1] / "outside").mkdir(parents=True, exist_ok=True)
            with self.assertRaisesRegex(StudioError, "escapes brand scope"):
                load_studio(manifest, root=manifest.parents[3])

    def test_missing_or_single_frame_sequences_fail_loudly(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            empty = base / "empty"
            empty.mkdir()
            with self.assertRaisesRegex(ValueError, "at least two frames"):
                sequence_frames(empty)
            with self.assertRaisesRegex(ValueError, "missing"):
                sequence_frames(base / "absent")


if __name__ == "__main__":
    unittest.main()
