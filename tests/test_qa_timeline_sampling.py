"""MD-206 samples authored keyframes and intervening transform states."""
import unittest
from types import SimpleNamespace

from reels_maker.core.scene_graph import Node
from reels_maker.motionkit.keyframes import Track
from reels_maker.motionkit.presets import apply_entrance
from reels_maker.qa.report import sample_geometry_frames
from reels_maker.design.tokens import resolve_tokens


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


if __name__ == "__main__":
    unittest.main()
