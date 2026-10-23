import unittest
from reels_maker.design.editorial_quality import audit_editorial_style
from reels_maker.components.scenes import _decor


class EditorialQualityTests(unittest.TestCase):
    def test_plain_scene_has_no_warnings(self):
        self.assertEqual(audit_editorial_style({
            "background": {"kind": "solid", "color": "#ffffff"},
            "headline": "A clear message",
        }), [])

    def test_flags_template_tropes(self):
        scene = {
            "decor": True,
            "background": {"kind": "gradient", "from": "#111", "to": "#222"},
            "icon_assets": [{}, {}, {}, {}],
            "headline": {"runs": [{"text": str(i), "color": "accent"} for i in range(5)]},
            "transition_out": {"type": "pixel-dissolve"},
        }
        codes = {issue["code"] for issue in audit_editorial_style(scene)}
        self.assertEqual(codes, {"ornamental_decor", "generic_gradient",
                                "icon_overload", "fragmented_typography",
                                "excessive_accent", "novelty_transition"})

    def test_default_decor_does_not_inject_ornaments(self):
        class Ctx:
            scene_index = 1
        self.assertEqual(_decor(Ctx(), {}, {}), [])
        self.assertEqual(_decor(Ctx(), {"decor": False}, {}), [])


if __name__ == "__main__":
    unittest.main()
