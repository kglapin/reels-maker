"""MD-206 samples authored keyframes and intervening transform states."""
import unittest
from types import SimpleNamespace

from reels_maker.core.scene_graph import Node
from reels_maker.motionkit.easing import back, easing_extrema_progress, spring
from reels_maker.motionkit.keyframes import Keyframe, Track
from reels_maker.motionkit.presets import apply_entrance
from reels_maker.qa.report import audit_camera_canvas, sample_geometry_frames
from reels_maker.design.tokens import resolve_tokens
from reels_maker.layout.composition_optimizer import solve_scene_layout
from reels_maker.layout.engine import LayoutEngine
from reels_maker.renderers.camera_canvas import (
    build_camera_canvas_hierarchy, camera_viewport_to_world,
    camera_world_to_viewport, plan_camera_path,
)
from reels_maker.textkit.typesetter import FontBook


class TimelineGeometrySamplingTests(unittest.TestCase):
    def test_includes_all_track_keys_and_quarter_interval_frames(self):
        node = Node(kind="rect", props={"x": 10, "y": 10, "w": 10, "h": 10})
        node.track("dx", Track.from_pairs([(0.0, 0), (.5, 80), (1.5, -30), (2.0, 0)]))
        group = Node(kind="group", children=[node])
        built = SimpleNamespace(nodes=[group], duration=2.0)
        timing = SimpleNamespace(frames=61)
        frames = sample_geometry_frames(built, timing, 30, samples_per_scene=6)
        for key_frame in (0, 15, 45, 60):
            self.assertIn(key_frame, frames)
        # 0.125s is a quarter of the 0.0..0.5 key interval; 0.75s is a
        # quarter into the long .5..1.5 interval.
        self.assertIn(4, frames)
        self.assertIn(22, frames)
        self.assertGreater(len(frames), 6)
        self.assertEqual(frames, sorted(set(frames)))

    def test_empty_track_sets_still_preserve_even_samples_and_endpoints(self):
        built = SimpleNamespace(nodes=[Node(kind="rect")], duration=1.0)
        timing = SimpleNamespace(frames=31)
        frames = sample_geometry_frames(built, timing, 30, samples_per_scene=4)
        self.assertEqual(frames, [0, 8, 10, 15, 20, 22, 30])

    def test_invalid_sample_counts_fail_closed(self):
        built = SimpleNamespace(nodes=[], duration=1.0)
        timing = SimpleNamespace(frames=30)
        for count in (0, 1, True, 2.5):
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, "samples_per_scene"):
                sample_geometry_frames(built, timing, 30, samples_per_scene=count)

    def test_entrance_travel_and_scale_are_clamped_to_safe_bounds(self):
        tokens = resolve_tokens("editorial-premium", width=100, height=100)
        bottom_aligned = Node(kind="rect", props={"x": 20, "y": 80,
                                                   "w": 30, "h": 20})
        apply_entrance(bottom_aligned, "fade-up", 0, .5, tokens,
                       safe_bounds=(0, 0, 100, 100))
        self.assertEqual(bottom_aligned.tracks["dy"].value(0), 0)
        edge_aligned = Node(kind="rect", props={"x": 85, "y": 20,
                                                 "w": 15, "h": 15})
        apply_entrance(edge_aligned, "scale-focus", 0, .5, tokens,
                       safe_bounds=(0, 0, 100, 100))
        self.assertAlmostEqual(edge_aligned.tracks["scale"].value(0), 1.0)

    def test_analytical_easing_extrema_sampled_for_back_and_spring(self):
        self.assertEqual(easing_extrema_progress("linear"), ())
        self.assertEqual(easing_extrema_progress("out-cubic"), ())
        back_peaks = easing_extrema_progress("back")
        self.assertEqual(len(back_peaks), 1)
        p_peak = back_peaks[0]
        self.assertGreater(back(p_peak), 1.0)
        self.assertGreaterEqual(back(p_peak), back(max(0.0, p_peak - 0.02)))
        self.assertGreaterEqual(back(p_peak), back(min(1.0, p_peak + 0.02)))

        spring_peaks = easing_extrema_progress("spring")
        self.assertGreaterEqual(len(spring_peaks), 2)
        self.assertGreater(spring(spring_peaks[0]), 1.0)

        node = Node(kind="rect", props={"x": 10, "y": 10, "w": 10, "h": 10})
        node.track("dx", Track([
            Keyframe(0.0, 0.0, "linear"),
            Keyframe(1.0, 100.0, "back"),
        ]))
        built = SimpleNamespace(nodes=[node], duration=2.0)
        timing = SimpleNamespace(frames=61)
        frames = sample_geometry_frames(built, timing, 30, samples_per_scene=2)
        expected_peak_frame = round(p_peak * 30)
        self.assertIn(expected_peak_frame, frames)

    def test_camera_canvas_hierarchy_and_subject_retention_qa(self):
        scenes = [
            {
                "photo": "a.jpg",
                "headline": "Pierwszy kadr",
                "duration": 3.0,
                "camera_canvas": {"x": 1000, "y": 1200, "angle": 0, "zoom": 1.0,
                                  "layout": "photo-above"},
            },
            {
                "photo": "b.jpg",
                "headline": "Drugi kadr",
                "duration": 3.0,
                "camera_canvas": {"x": 2200, "y": 1400, "angle": -6, "zoom": 1.0,
                                  "layout": "photo-left", "move_duration": 0.8},
            },
        ]
        hierarchy, bounds = build_camera_canvas_hierarchy(scenes, 1080, 1920)
        self.assertIn("shot-0/photo", bounds)
        fwd = camera_world_to_viewport(1000, 1200, -6, 1.0, 1080, 1920)
        inv = camera_viewport_to_world(1000, 1200, -6, 1.0, 1080, 1920)
        composed = fwd.then(inv)
        self.assertAlmostEqual(composed.a, 1.0, places=6)
        self.assertAlmostEqual(composed.d, 1.0, places=6)

        report = audit_camera_canvas(scenes, 1080, 1920)
        self.assertTrue(report["ok"], report["issues"])
        self.assertEqual(report["path"]["transitions"][0]["settled_subject_retention"], 1.0)

        excessive = [
            scenes[0],
            {**scenes[1], "camera_canvas": {**scenes[1]["camera_canvas"], "angle": 90}},
        ]
        bad_report = audit_camera_canvas(excessive, 1080, 1920, max_angle_delta=35.0)
        self.assertFalse(bad_report["ok"])
        self.assertEqual(bad_report["issues"][0]["code"], "excessive_camera_rotation")

    def test_layout_solver_evaluates_real_built_candidates(self):
        from reels_maker.components.base import SceneContext
        tokens = resolve_tokens("editorial-premium", width=1080, height=1920)
        ctx = SceneContext(
            width=1080, height=1920, fps=30, duration=3.5,
            tokens=tokens, style="editorial-premium", fonts=FontBook(),
        )
        scene = {
            "headline": "CZYSTA ENERGIA W DOMU",
            "subtitle": "Sprawdzone parametry bez obietnic bez pokrycia",
            "duration": 3.5,
            "composition": "stack-center",
        }
        solved = solve_scene_layout(
            ctx, scene, ("stack-center", "full-bleed-type", "statement")
        )
        self.assertIsNotNone(solved["selected_id"])
        self.assertIsNotNone(solved["selected_built"])
        self.assertTrue(any(c["valid"] for c in solved["candidates"]))

    def test_platform_profiles_safe_polygons_audio_selection_and_qa_repair(self):
        from reels_maker.audiokit.cues import select_compatible_audio
        from reels_maker.components.base import SceneContext
        from reels_maker.design.tokens import (
            platform_safe_polygon, resolve_platform_profile,
        )
        from reels_maker.qa.report import repair_scene_layout

        ig = resolve_platform_profile("instagram-reels")
        self.assertEqual((ig["width"], ig["height"], ig["aspect"]), (1080, 1920, "9:16"))
        poly = platform_safe_polygon("instagram_reels")
        # 6-vertex L-polygon excluding the lower-right action rail
        self.assertEqual(len(poly.vertices), 6)
        self.assertTrue(poly.contains_point(500, 900))
        self.assertFalse(poly.contains_point(960, 1400))

        sq = platform_safe_polygon("square_feed")
        self.assertEqual(len(sq.vertices), 4)

        audio_res = select_compatible_audio(
            [
                {
                    "id": "unreviewed-track",
                    "kind": "music",
                    "rights_status": "unknown",
                    "delivery_ready": False,
                    "platforms_allowed": ["instagram_reels"],
                    "duration": 20.0,
                },
                {
                    "id": "approved-short",
                    "kind": "music",
                    "rights_status": "approved",
                    "delivery_ready": True,
                    "platforms_allowed": ["instagram_reels"],
                    "duration": 8.0,
                },
                {
                    "id": "approved-fit",
                    "kind": "music",
                    "rights_status": "approved",
                    "delivery_ready": True,
                    "platforms_allowed": ["instagram_reels"],
                    "duration": 16.0,
                },
            ],
            platform="instagram_reels",
            required_duration=15.0,
        )
        self.assertTrue(audio_res["ok"])
        self.assertEqual(audio_res["selected"]["id"], "approved-fit")
        self.assertEqual(len(audio_res["rejected"]), 2)

        tokens = resolve_tokens("editorial-premium", width=1080, height=1920)
        # Short scene duration triggers reading-hold warning on a table scene,
        # which repair_scene_layout resolves by extending hold / compacting type.
        ctx = SceneContext(
            width=1080, height=1920, fps=30, duration=0.55,
            tokens=tokens, style="editorial-premium", fonts=FontBook(),
        )
        table_scene = {
            "type": "table",
            "duration": 0.55,
            "headline": "Krótki czas ekspozycji",
            "columns": [
                {"id": "k", "label": "Parametr", "width": 0.6, "align": "left"},
                {"id": "v", "label": "Wartość", "width": 0.4, "align": "right"},
            ],
            "rows": [
                {"id": "r1", "values": {"k": "Moc", "v": "10 kW"}},
                {"id": "r2", "values": {"k": "Pojemność", "v": "15 kWh"}},
            ],
        }
        repaired = repair_scene_layout(ctx, table_scene, max_retries=3)
        self.assertTrue(repaired["ok"])
        self.assertTrue(repaired["repaired"])
        self.assertGreater(len(repaired["attempts"]), 1)
        self.assertGreater(repaired["scene"]["duration"], 0.55)

    def test_md306_polish_typography_regression_and_md603_inspector(self):
        from reels_maker.creative.pipeline import export_scene_graph_inspector
        from reels_maker.qa.report import run_polish_typography_regression
        from reels_maker.renderers.camera_canvas import bezier_camera_point

        reg = run_polish_typography_regression()
        self.assertTrue(reg["ok"], reg["failures"])
        self.assertEqual(reg["combinations_checked"], 32)

        mid = bezier_camera_point((0.0, 0.0), (0.0, 100.0), (100.0, 100.0), (100.0, 0.0), 0.5)
        self.assertEqual(mid, (50.0, 75.0))

        tokens = resolve_tokens("editorial-premium", width=720, height=1280)
        from reels_maker.components.base import SceneContext
        from reels_maker.components.scenes import build_scene
        ctx = SceneContext(720, 1280, 24, 2.5, tokens, "editorial-premium", FontBook())
        built = build_scene(ctx, {"headline": "INSPEKTOR GRAFU", "duration": 2.5})
        inspected = export_scene_graph_inspector([built])
        self.assertEqual(len(inspected["scenes"]), 1)
        self.assertTrue(any(n["motion_path_svg"] for n in inspected["scenes"][0]["nodes"]))


if __name__ == "__main__":
    unittest.main()
