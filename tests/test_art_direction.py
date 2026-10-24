"""Tests for the artistic direction layer (reels_maker.art)."""
import unittest

from reels_maker.art.dramaturgy import (
    DramaturgyPlan,
    SceneBeat,
    plan_dramaturgy,
    resolve_beat_for_scene,
)
from reels_maker.art.intent import (
    SceneIntent,
    SceneIntentError,
    resolve_scene_intent,
    intent_for_composition,
)
from reels_maker.art.motion_personality import (
    DEFAULT_PERSONALITY,
    MotionPersonality,
    MotionPersonalityError,
    resolve_motion_personality,
)
from reels_maker.design.tokens import resolve_tokens


class DramaturgyTests(unittest.TestCase):
    def test_plan_assigns_phases(self):
        plan = plan_dramaturgy([3.0, 3.5, 4.0, 3.0])
        self.assertIsInstance(plan, DramaturgyPlan)
        self.assertEqual(plan.beats[0].phase, "hook")
        self.assertEqual(plan.beats[-1].phase, "resolve")
        self.assertTrue(any(b.phase == "climax" for b in plan.beats))

    def test_resolve_beat_for_scene_falls_back(self):
        plan = plan_dramaturgy([3.0, 3.0])
        beat = resolve_beat_for_scene(plan, 0)
        self.assertEqual(beat.phase, "hook")
        fallback = resolve_beat_for_scene(plan, 99)
        self.assertEqual(fallback.phase, "build")

    def test_over_synchronized_flag_trips_when_accent_density_is_high(self):
        # The auto-plan keeps accent hits sparse (hook/climax/resolve plus
        # every third build cut).  The guard exists to catch manual overrides
        # where an author marked every scene as an accent hit.
        beats = tuple(
            SceneBeat(scene_index=i, phase="build", energy=0.7,
                      accent_hit=True, start_s=0.0, duration_s=3.0)
            for i in range(8)
        )
        plan = DramaturgyPlan(style="editorial-premium", beats=beats,
                              accent_density=1.0, over_synchronized=True)
        self.assertTrue(plan.over_synchronized)

    def test_over_synchronized_flag_is_false_for_normal_arcs(self):
        plan = plan_dramaturgy([3.0] * 6)
        self.assertFalse(plan.over_synchronized)
        self.assertLess(plan.accent_density, 0.75)


class MotionPersonalityTests(unittest.TestCase):
    def test_defaults_are_valid(self):
        self.assertEqual(DEFAULT_PERSONALITY.acceleration, "balanced")
        self.assertEqual(DEFAULT_PERSONALITY.overshoot, "subtle")
        self.assertEqual(DEFAULT_PERSONALITY.easing_preference, "out-cubic")

    def test_resolve_from_brand(self):
        brand = {"motion": {"acceleration": "snappy", "overshoot": "expressive"}}
        p = resolve_motion_personality(brand)
        self.assertEqual(p.acceleration, "snappy")
        self.assertEqual(p.easing_preference, "out-expo")
        self.assertTrue(p.allows_overshoot)

    def test_unknown_key_raises(self):
        brand = {"motion": {"bogus_key": 1}}
        with self.assertRaises(MotionPersonalityError):
            resolve_motion_personality(brand)

    def test_invalid_acceleration_raises(self):
        with self.assertRaises(MotionPersonalityError):
            MotionPersonality(acceleration="fast")

    def test_scaled_stagger_clamps(self):
        p = MotionPersonality(stagger_scale=5.0)
        self.assertEqual(p.scaled_stagger(1.0), 2.0)
        p2 = MotionPersonality(stagger_scale=0.5)
        self.assertEqual(p2.scaled_stagger(0.2), 0.1)


class SceneIntentTests(unittest.TestCase):
    def test_data_composition_maps_to_data_reveal(self):
        intent = resolve_scene_intent({"composition": "amount"})
        self.assertEqual(intent.intent, "data_reveal")
        self.assertLess(intent.duration_scale, 1.0)

    def test_cta_composition_maps_to_call_to_action(self):
        intent = resolve_scene_intent({"composition": "cta"})
        self.assertEqual(intent.intent, "call_to_action")

    def test_unknown_composition_falls_back(self):
        intent = resolve_scene_intent({"composition": "mystery-box"})
        self.assertEqual(intent.intent, "emotional")
        self.assertLess(intent.confidence, 0.6)

    def test_intent_for_composition_helper(self):
        self.assertEqual(intent_for_composition("breakdown"), "data_reveal")
        self.assertEqual(intent_for_composition("photo"), "emotional")

    def test_invalid_intent_raises(self):
        with self.assertRaises(SceneIntentError):
            SceneIntent(intent="bogus", composition="x")

    def test_preset_families_are_known_mechanisms(self):
        intent = resolve_scene_intent({"composition": "amount"})
        for family in intent.preset_families:
            self.assertIn(family, (
                "horizontal-wipe", "optical-tracking", "vertical-drift",
            ))


class IntegrationTests(unittest.TestCase):
    """The art layer must not change behaviour when opt-in is off."""

    def test_default_personality_is_neutral(self):
        tokens = resolve_tokens("editorial-premium", width=720, height=1280)
        # Personality is neutral by default: entrance duration scale is 1.0,
        # so the resolved token is unchanged from the style baseline.
        self.assertAlmostEqual(tokens.motion.enter, 0.54)

    def test_resolve_art_context_noop_without_brand(self):
        from reels_maker.components.base import SceneContext, resolve_art_context
        ctx = SceneContext(
            width=720, height=1280, fps=30, duration=3.0,
            tokens=resolve_tokens("editorial-premium", width=720, height=1280),
            style="editorial-premium", fonts=None, scene_index=0,
            scene={"composition": "amount"},
        )
        resolve_art_context(ctx, brand_data=None)
        self.assertIsNotNone(ctx.intent)
        self.assertEqual(ctx.intent.intent, "data_reveal")


if __name__ == "__main__":
    unittest.main()
