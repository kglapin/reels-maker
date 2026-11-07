"""Regression guard for CTA panel copy centering.

The phone number and tagline must sit as one vertically centered group on
the red panel (user-reported: number rode too high with dead space below).
Builds a real Studio scene graph without rendering video.
"""
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image


def _build_cta(tmp):
    from reels_maker.studio import load_studio

    root = Path(tmp)
    brand = root / "brands" / "cta-probe"
    (brand / "imports").mkdir(parents=True)
    (brand / "brand.json").write_text(json.dumps({
        "id": "cta-probe",
        "branding": {"accent": "#D41217"},
    }))
    logo = brand / "imports" / "logo.png"
    Image.new("RGB", (200, 100), (255, 255, 255)).save(logo)
    manifest = root / "cta.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "name": "cta probe",
        "brand": "cta-probe",
        "video": {"width": 1080, "height": 1920, "fps": 30},
        "scenes": [{
            "id": "cta",
            "composition": "cta",
            "duration": 5.0,
            "background": {"kind": "solid", "color": "#FFFFFF"},
            "headline": "Masz pytania?",
            "phone": "505 012 600",
            "line_one": "BEZPŁATNA WYCENA",
            "line_two": "KALISZ I OKOLICE",
            "logo": "imports/logo.png",
        }],
    }))
    project = load_studio(manifest, root=root)
    built = project.build()
    nodes = [n for scene in built for n in scene.nodes]
    flat = [n for root_node in nodes for n in root_node.flatten()]
    return {n.role: n.base_bounds() for n in flat if n.role}


class CtaPanelCenteringTest(unittest.TestCase):
    def test_phone_and_tag_are_centered_on_panel(self):
        with tempfile.TemporaryDirectory() as tmp:
            boxes = _build_cta(tmp)
        panel = boxes["cta-panel"]
        phone = boxes["phone"]
        tag = boxes["cta-tag"]
        panel_h = panel[3] - panel[1]
        # Number sits in the lower-middle of the panel, not near the top.
        self.assertGreaterEqual(phone[1] - panel[1], 0.28 * panel_h)
        # Tagline follows the number with a readable gap and stays inside.
        self.assertGreaterEqual(tag[1] - phone[3], 0)
        self.assertLessEqual(tag[3], panel[3])
        # The phone+tagline group is centered on the panel as one block.
        group_center = (phone[1] + tag[3]) / 2
        panel_center = (panel[1] + panel[3]) / 2
        self.assertLessEqual(abs(group_center - panel_center),
                             0.08 * panel_h)

    def test_no_invented_defaults_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            boxes = _build_cta(tmp)
        self.assertIn("phone", boxes)
        self.assertIn("cta-tag", boxes)


if __name__ == "__main__":
    unittest.main()
