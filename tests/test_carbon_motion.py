"""Source constants, isolated adapter contracts, and native Studio integration."""
import copy
import unittest
from dataclasses import dataclass
from types import SimpleNamespace
from reels_maker.motionkit.carbon import (
    CURVES, DURATION_MS, apply_carbon_motion, curve_params, duration_seconds,
)


@dataclass(frozen=True)
class FixtureKey:
    time: float
    value: float
    easing: str = "out-cubic"
    params: tuple = ()


@dataclass
class FixtureTrack:
    keys: list
    clamp_before: bool = True
    clamp_after: bool = True


def fixture(track=None):
    node = SimpleNamespace(role="headline", tracks={"dy": track or FixtureTrack([
        FixtureKey(0, 20), FixtureKey(.4, 0)])})
    node.flatten = lambda: [node]
    return SimpleNamespace(nodes=[node], meta={}), node


class CarbonPolicyTests(unittest.TestCase):
    def test_source_curves_are_exact(self):
        self.assertEqual(CURVES["productive"], {
            "standard": (.2, 0., .38, .9), "entrance": (0., 0., .38, .9),
            "exit": (.2, 0., 1., .9)})
        self.assertEqual(CURVES["expressive"], {
            "standard": (.4, .14, .3, 1.), "entrance": (0., 0., .3, 1.),
            "exit": (.4, .14, 1., 1.)})
        self.assertEqual(DURATION_MS, {"fast-01":70, "fast-02":110,
            "moderate-01":150, "moderate-02":240, "slow-01":400, "slow-02":700})

    def test_frame_duration_is_at_least_source_duration(self):
        for fps in (24, 25, 30, 60):
            for token, ms in DURATION_MS.items():
                value = duration_seconds(token, fps)
                self.assertGreaterEqual(value + 1e-9, ms / 1000)
                self.assertAlmostEqual(value * fps, round(value * fps))
        self.assertEqual(duration_seconds("slow-01", 60, 2), .8)

    def test_invalid_parameters_fail(self):
        for mode, phase in [("unknown", "entrance"), ("productive", "bad"), ([], "exit")]:
            with self.assertRaises(ValueError):
                curve_params(mode, phase)
        for token, fps, scale in [("bad",30,1), ("fast-01",True,1),
                                  ("fast-01",30,float("nan")), ("fast-01",30,True)]:
            with self.assertRaises(ValueError):
                duration_seconds(token, fps, scale)

    def test_adapter_changes_real_key_parameters_not_just_metadata(self):
        built, node = fixture()
        before = copy.deepcopy(node.tracks["dy"].keys)
        apply_carbon_motion(built, {"mode":"expressive"}, duration=3, fps=30)
        keys = node.tracks["dy"].keys
        self.assertEqual([k.value for k in keys], [k.value for k in before])
        self.assertEqual([k.time for k in keys], [k.time for k in before])
        self.assertTrue(all(k.easing == "cubic-bezier" for k in keys))
        self.assertEqual(keys[-1].params, curve_params("expressive", "entrance"))

    def test_data_and_complex_tracks_are_preserved(self):
        built, node = fixture()
        node.tracks["prop.value"] = FixtureTrack([FixtureKey(0,0), FixtureKey(1,42)])
        node.tracks["rotation"] = FixtureTrack([FixtureKey(0,0), FixtureKey(.2,4), FixtureKey(1,0)])
        value, rotation = node.tracks["prop.value"], node.tracks["rotation"]
        apply_carbon_motion(built, {}, duration=3, fps=30)
        self.assertIs(node.tracks["prop.value"], value)
        self.assertIs(node.tracks["rotation"], rotation)

    def test_explicit_phase_and_frame_quantized_retiming(self):
        built, node = fixture()
        config = {"roles":{"headline":{"phase":"standard", "duration_token":"slow-01"}}}
        apply_carbon_motion(built, config, duration=3, fps=30)
        self.assertEqual(node.tracks["dy"].keys[-1].params, curve_params("productive", "standard"))
        self.assertEqual(node.tracks["dy"].keys[-1].time, .4)

    def test_invalid_hold_and_unknown_role_are_atomic(self):
        for config in [{"roles":{"missing":{}}}, {"unknown":1},
                       {"roles":{"headline":{"duration_token":"slow-02", "film_scale":4}}}]:
            built, node = fixture()
            before = node.tracks["dy"]
            with self.assertRaises(ValueError):
                apply_carbon_motion(built, config, duration=1, fps=30)
            self.assertIs(node.tracks["dy"], before)
            self.assertNotIn("carbon_motion", built.meta)

    def test_opacity_exit_uses_exit_curve(self):
        built, node = fixture()
        node.tracks = {"opacity":FixtureTrack([FixtureKey(2,1), FixtureKey(2.4,0)])}
        apply_carbon_motion(built, {}, duration=3, fps=30)
        self.assertEqual(node.tracks["opacity"].keys[-1].params, curve_params("productive", "exit"))


class CarbonNativeIntegrationTests(unittest.TestCase):
    def test_native_track_interpolation_uses_carbon_params(self):
        from reels_maker.motionkit.keyframes import Keyframe, Track
        from reels_maker.motionkit.easing import ease
        built, node = fixture(Track([Keyframe(0,20), Keyframe(1,0)]))
        apply_carbon_motion(built, {"mode":"expressive"}, duration=3, fps=30)
        track = node.tracks["dy"]
        for p in (.1, .3, .5, .8):
            expected = 20 * (1 - ease("cubic-bezier", p, **dict(curve_params("expressive", "entrance"))))
            self.assertAlmostEqual(track.value(p), expected)
        self.assertEqual(track.value(0),20)
        self.assertEqual(track.value(1),0)

    def test_all_six_native_curves_are_bounded_and_monotonic(self):
        from reels_maker.motionkit.easing import ease
        for mode in CURVES:
            for phase in CURVES[mode]:
                values = [ease("cubic-bezier", i/100, **dict(curve_params(mode,phase))) for i in range(101)]
                self.assertTrue(all(-1e-8 <= x <= 1+1e-8 for x in values))
                self.assertTrue(all(a <= b+1e-8 for a,b in zip(values,values[1:])))

    def test_scene_builder_hook_and_no_opt_in_behavior(self):
        from reels_maker.components.base import SceneContext
        from reels_maker.components.scenes import build_scene
        from reels_maker.design.tokens import resolve_tokens
        from reels_maker.textkit.typesetter import FontBook
        tokens = resolve_tokens("editorial-premium", width=360, height=640)
        ctx = SceneContext(360,640,30,4,tokens,"editorial-premium",FontBook())
        scene = {"composition":"statement", "headline":"CARBON MOTION", "duration":4}
        original = build_scene(ctx, scene)
        self.assertNotIn("carbon_motion", original.meta)
        styled = build_scene(ctx, {**scene, "carbon_motion":{"mode":"productive"}})
        self.assertTrue(styled.meta["carbon_motion"]["applied"])
        self.assertIsNone(styled.meta["carbon_motion"]["visual_approval"])


if __name__ == "__main__":
    unittest.main()
