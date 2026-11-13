"""Tests for the procedural isometric explainer engine and Studio wiring."""
from __future__ import annotations

import unittest

from reels_maker.iso import COPY_BEATS, FILM_DURATION, render_iso_frame
from reels_maker.iso.film import (
    TITLE_MAX_WIDTH, frame_at, ustate, world_cam, wrap_title)
from reels_maker.iso.projection import DEFAULT_PALETTE, E, iso, resolve_font


class IsoStudioWiringTest(unittest.TestCase):
    """The Studio graph must advance playback_time every frame (frozen-clock
    regression: an explicit playback_time=0.0 prop froze scene 1 on blank)."""

    def _scene(self, duration=7.0, t0=15.0):
        from reels_maker.components.iso_scenes import build_iso_explainer
        from reels_maker.components.model import SceneContext
        from reels_maker.design.tokens import resolve_tokens
        from reels_maker.textkit.typesetter import FontBook

        tokens = resolve_tokens("editorial-premium", width=1080, height=1920)
        ctx = SceneContext(1080, 1920, 30, duration, tokens, "editorial-premium",
                           FontBook())
        return build_iso_explainer(ctx, {"type": "iso-explainer", "duration": duration,
                                         "t0": t0, "logo": None})

    def test_playback_time_advances(self):
        built = self._scene()
        node = built.elements["world"]
        self.assertNotIn("playback_time", node.props)
        times = set()
        for t in (0.0, 1.0, 3.5):
            sampled = node.sample(t)
            times.add(sampled.props.get("playback_time"))
        self.assertEqual(times, {0.0, 1.0, 3.5})

    def test_consecutive_frames_differ(self):
        from reels_maker.iso import render_iso_frame

        spec = {"t0": 15.0, "snow": 1.0, "logo": None, "font": None}
        a = render_iso_frame(spec, 270, 480, 1.0)
        b = render_iso_frame(spec, 270, 480, 1.0 + 1 / 30)
        self.assertNotEqual(list(a.getdata()), list(b.getdata()))


class IsoEngineTest(unittest.TestCase):
    def test_easing_bounds(self):
        self.assertEqual(E(-1), 0.0)
        self.assertEqual(E(2), 1.0)
        self.assertAlmostEqual(E(0.5), 0.5, places=6)

    def test_iso_projection_origin(self):
        self.assertEqual(iso((0, 0, 0)), (0.0, 0.0))

    def test_beats_cover_full_film_without_gaps(self):
        starts = [b[0] for b in COPY_BEATS]
        self.assertEqual(starts[0], 0)
        self.assertEqual(len(COPY_BEATS), 13)
        total = sum(b - a for a, b in zip(starts, starts[1:] + [FILM_DURATION]))
        self.assertAlmostEqual(total, FILM_DURATION)

    def test_font_resolves_without_crash(self):
        path = resolve_font()
        self.assertIsInstance(path, str)

    def test_state_model_ranges(self):
        pal = dict(DEFAULT_PALETTE)
        for u in (0, 7, 20, 30, 45, 55, 70, 95, 105):
            st = ustate(u, pal)
            for key in ("frost", "heat", "plume", "drip", "puddle", "ring", "air"):
                self.assertGreaterEqual(st[key], 0.0, f"{key}@{u}")
                self.assertLessEqual(st[key], 1.2, f"{key}@{u}")

    def test_camera_deterministic(self):
        self.assertEqual(world_cam(20), world_cam(20))
        self.assertNotEqual(world_cam(20), world_cam(60))

    def test_frame_renders_master_size(self):
        font = resolve_font()
        im, boxes = frame_at(20.25, dict(DEFAULT_PALETTE), font, None)
        self.assertEqual(im.size, (1080, 1920))
        self.assertTrue(any("szron" in s for s, _b in boxes))

    def test_render_entry_scales(self):
        im = render_iso_frame({"t0": 15.0, "snow": 0.0}, 270, 480, 5.0)
        self.assertEqual(im.size, (270, 480))

    def test_render_entry_deterministic(self):
        a = render_iso_frame({"t0": 40.0, "snow": 0.0}, 270, 480, 2.0)
        b = render_iso_frame({"t0": 40.0, "snow": 0.0}, 270, 480, 2.0)
        self.assertEqual(list(a.getdata()), list(b.getdata()))


class IsoCopyOverrideTests(unittest.TestCase):
    def test_override_replaces_beat_copy(self):
        font = resolve_font()
        _im, boxes = frame_at(
            20.25, dict(DEFAULT_PALETTE), font, None,
            copy_override={"title": "Test nagłówka",
                           "body": ["Linia pierwsza"]},
            scene_time=2.0)
        texts = [s for s, _b in boxes]
        self.assertIn("Test nagłówka", texts)
        self.assertIn("Linia pierwsza", texts)
        self.assertNotIn("Skąd bierze się", texts)
        self.assertNotIn("szron na lamelach?", texts)

    def test_override_entry_point_renders(self):
        im = render_iso_frame(
            {"t0": 15.0, "snow": 0.0,
             "copy": {"title": "Test nagłówka", "body": ["Linia pierwsza"]}},
            270, 480, 2.0)
        self.assertEqual(im.size, (270, 480))

    def test_no_override_keeps_beat_copy(self):
        font = resolve_font()
        _im, boxes = frame_at(20.25, dict(DEFAULT_PALETTE), font, None)
        texts = [s for s, _b in boxes]
        self.assertIn("Skąd bierze się", texts)
        self.assertIn("szron na lamelach?", texts)


class TitleWrapTests(unittest.TestCase):
    def test_fitting_title_passes_through(self):
        from reels_maker.iso.film import TITLE_MAX_WIDTH, asset
        title = "Cykl trwa zazwyczaj kilka minut."
        # Font metrics differ across environments (resolve_font picks the
        # first installed candidate): only assert passthrough when the
        # resolved font actually fits the title inside the margins.
        if asset(title, 52, (255, 255, 255), None).width > TITLE_MAX_WIDTH:
            self.skipTest("title overflows margins with this font")
        self.assertEqual(wrap_title(title, None), [title])

    def test_overflowing_title_breaks_within_margins(self):
        from reels_maker.iso.film import asset
        font = resolve_font()
        for title in ("Ogrzewanie domu wraca samoczynnie.",
                      "Skąd bierze się szron na lamelach?"):
            lines = wrap_title(title, font)
            self.assertEqual(len(lines), 2)
            self.assertEqual(" ".join(lines), title)
            for line in lines:
                self.assertLessEqual(
                    asset(line, 52, (255, 255, 255), font).width,
                    TITLE_MAX_WIDTH)


if __name__ == "__main__":
    unittest.main()
