"""Regression guard for the minimalist closing card.

The cta-minimal end screen is a centered stack (kick, phone, contact
lines) with no panel, photo or logo. The phone carries the only entrance
motion; the text group must sit centered, and long numbers must shrink to
hold side margins. Builds a real Studio scene graph without rendering
video.
"""
import json
import tempfile
import unittest
from pathlib import Path


def _build_minimal(tmp, phone="67 350 90 90"):
    from reels_maker.studio import load_studio

    root = Path(tmp)
    brand = root / "brands" / "cta-minimal-probe"
    (brand / "imports").mkdir(parents=True)
    (brand / "brand.json").write_text(json.dumps({
        "id": "cta-minimal-probe",
        "branding": {"accent": "#47A013"},
    }))
    manifest = root / "cta-minimal.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "name": "cta minimal probe",
        "brand": "cta-minimal-probe",
        "video": {"width": 1080, "height": 1920, "fps": 30},
        "scenes": [{
            "id": "end",
            "composition": "cta-minimal",
            "duration": 5.0,
            "background": {"kind": "solid", "color": "#122A1C"},
            "kicker": "ZAPYTAJ O WYCENĘ",
            "phone": phone,
            "website": "asta-energy.pl",
            "email": "kontakt@asta-energy.pl",
        }],
    }))
    project = load_studio(manifest, root=root)
    built = project.build()
    nodes = [n for scene in built for n in scene.nodes]
    flat = [n for root_node in nodes for n in root_node.flatten()]
    return ({n.role: n.base_bounds() for n in flat if n.role},
            {n.role: dict(n.props) for n in flat if n.role})


class CtaMinimalTests(unittest.TestCase):
    def test_stack_is_centered_without_panel(self):
        with tempfile.TemporaryDirectory() as tmp:
            boxes, _props = _build_minimal(tmp)
        for role in ("kicker", "headline", "body"):
            self.assertIn(role, boxes)
        kicker, phone, body = (boxes["kicker"], boxes["headline"],
                               boxes["body"])
        # Top-to-bottom order with no overlaps.
        self.assertLess(kicker[3], phone[1])
        self.assertLess(phone[3], body[1])
        # Group centered on the frame as one block.
        group_center = (kicker[1] + body[3]) / 2
        self.assertLessEqual(abs(group_center - 960), 0.08 * 1920)
        self.assertNotIn("cta-panel", boxes)
        self.assertNotIn("cta", boxes)

    def test_long_number_shrinks_to_hold_margins(self):
        with tempfile.TemporaryDirectory() as tmp:
            _boxes, normal = _build_minimal(tmp, phone="67 350 90 90")
        with tempfile.TemporaryDirectory() as tmp:
            _boxes, wide = _build_minimal(tmp, phone="67 350 90 90 12 34")
        self.assertEqual(normal["headline"]["size"], 88)
        self.assertLess(wide["headline"]["size"], 88)
        self.assertGreaterEqual(wide["headline"]["size"], 48)


if __name__ == "__main__":
    unittest.main()
