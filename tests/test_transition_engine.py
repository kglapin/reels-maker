"""Endpoint, geometry and determinism regression tests for transitions."""
import unittest
from PIL import Image
from reels_maker.renderers.transition_engine import EFFECTS, transition_frame


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.a = Image.new("RGB", (120, 216), "#151023")
        self.b = Image.new("RGB", (120, 216), "#47A013")

    def test_all_effects_have_exact_endpoints_and_dimensions(self):
        for effect in sorted(EFFECTS):
            with self.subTest(effect=effect):
                first = transition_frame(self.a,self.b,0,effect=effect)
                middle = transition_frame(self.a,self.b,.5,effect=effect)
                last = transition_frame(self.a,self.b,1,effect=effect)
                self.assertEqual(first.tobytes(),self.a.tobytes())
                self.assertEqual(last.tobytes(),self.b.tobytes())
                self.assertEqual(middle.size,self.a.size)
                self.assertEqual(middle.tobytes(),
                                 transition_frame(self.a,self.b,.5,effect=effect).tobytes())

    def test_rgb_and_rgba_sources_produce_identical_transition_frames(self):
        rgba_a = self.a.convert("RGBA")
        rgba_b = self.b.convert("RGBA")
        for effect in sorted(EFFECTS):
            with self.subTest(effect=effect):
                rgb = transition_frame(self.a, self.b, .37, effect=effect)
                rgba = transition_frame(rgba_a, rgba_b, .37, effect=effect)
                self.assertEqual(rgb.tobytes(), rgba.tobytes())

    def test_invalid_effect_fails_fast(self):
        with self.assertRaises(ValueError):
            transition_frame(self.a,self.b,.5,effect="not-a-transition")


if __name__ == "__main__":
    unittest.main()
