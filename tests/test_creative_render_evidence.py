import tempfile
import unittest
from pathlib import Path

from reels_maker.creative.llm.evidence import (
    RenderEvidenceError,
    bind_render_evidence,
)


class RenderEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.video = self.root / "render.mp4"
        self.sheet = self.root / "motion.png"
        self.video.write_bytes(b"synthetic-encoded-render")
        self.sheet.write_bytes(b"actual-storyboard-bytes")
        self.render = {"output": str(self.video), "duration": 2.0,
                       "frames": 48, "fps": 24}
        self.storyboard = {
            "output": str(self.sheet), "mode": "motion_strip",
            "samples": [
                {"scene": 1, "phase": phase, "timestamp_seconds": time}
                for phase, time in (("entry", .06), ("settled", .8),
                                    ("exit", 1.9))
            ],
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_binds_real_file_hashes_and_sample_timestamps(self):
        evidence = bind_render_evidence(self.render, self.storyboard)
        self.assertEqual(len(evidence["evidence_hash"]), 64)
        self.assertEqual(len(evidence["render_sha256"]), 64)
        self.assertEqual(len(evidence["storyboard_sha256"]), 64)
        self.assertEqual(evidence["samples"][1]["timestamp_seconds"], .8)
        self.assertTrue(evidence["host_observation_required"])

    def test_hash_changes_when_storyboard_evidence_changes(self):
        first = bind_render_evidence(self.render, self.storyboard)
        self.sheet.write_bytes(b"different-frame-evidence")
        second = bind_render_evidence(self.render, self.storyboard)
        self.assertNotEqual(first["evidence_hash"], second["evidence_hash"])

    def test_refuses_fake_or_incomplete_motion_evidence(self):
        missing = dict(self.storyboard, output=str(self.root / "absent.png"))
        with self.assertRaises(RenderEvidenceError):
            bind_render_evidence(self.render, missing)
        partial = dict(self.storyboard, samples=[self.storyboard["samples"][0]])
        with self.assertRaises(RenderEvidenceError):
            bind_render_evidence(self.render, partial)


if __name__ == "__main__":
    unittest.main()
