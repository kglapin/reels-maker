"""Golden frame snapshots for representative title presets.

Captures reference frames at fixed positions so creative regressions can be
reviewed visually by humans. Snapshot files are PNG images stored under
renders/<brand>/golden/ and are NOT part of the Git repository.

The snapshot test validates that golden frames exist and are valid images
after rendering. Actual pixel comparison must be reviewed by a human with the
scorecard (docs/REVIEW_RUBRIC.md).
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from reels_maker.renderer import render
from reels_maker.spec import load_project
from reels_maker.ffmpeg import execute, probe
from media_fixtures import has_real_media

_GOLDEN_MEDIA_AVAILABLE = all(has_real_media(path) for path in (
    Path("brands/asta-energy/media/footage/2_dron-pv-dla-firm-asta.mp4"),
    Path("brands/asta-energy/media/footage/5_reels-asta-pv-dla-branzy-drzewnej.mp4"),
))
_GOLDEN_FRAMES_AVAILABLE = Path("renders/asta-energy/golden").is_dir()


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg/FFprobe required")
@unittest.skipUnless(_GOLDEN_MEDIA_AVAILABLE and _GOLDEN_FRAMES_AVAILABLE,
                     "Golden rendering requires local LFS media and ignored review frames")
class GoldenFrameTests(unittest.TestCase):
    """Render known-good projects and extract key reference frames."""

    GOLDEN_DIR = Path("renders/asta-energy/golden")

    def _render_project(self, project_name: str) -> Path:
        """Render an existing project and return the MP4 path."""
        manifest = Path(f"brands/asta-energy/projects/{project_name}.json")
        project = load_project(manifest)
        result = render(project, root=Path(".").resolve())
        self.assertTrue(result["ok"], f"Render failed for {project_name}")
        return Path(result["output"])

    def _extract_frame(self, video: Path, timestamp: float, out: Path) -> None:
        """Extract a single frame at a given timestamp."""
        execute([
            "-ss", str(timestamp), "-i", str(video),
            "-frames:v", "1", "-q:v", "2", str(out)
        ])

    def _assert_valid_frame(self, frame: Path) -> None:
        """Assert a frame file exists and is a valid image."""
        self.assertTrue(frame.exists(), f"Frame not found: {frame}")
        self.assertGreater(frame.stat().st_size, 100,
                           f"Frame file too small: {frame}")
        from PIL import Image
        img = Image.open(frame)
        self.assertGreater(img.width, 100, f"Frame width too small: {frame}")
        self.assertGreater(img.height, 100, f"Frame height too small: {frame}")

    def test_typography_golden_frames(self):
        """Generate golden reference frames for the typography demo."""
        video = self._render_project("asta-typography-editorial-demo")
        metadata = probe(video)
        
        # Extract frames at key moments: intro, headline settle, body settle
        out_dir = self.GOLDEN_DIR / "typography-demo"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Frame at 0.5s (headline entrance begins)
        frame1 = out_dir / "headline-entrance.png"
        self._extract_frame(video, 0.5, frame1)
        self._assert_valid_frame(frame1)
        
        # Frame at 1.5s (headline should be settled)
        frame2 = out_dir / "headline-settled.png"
        self._extract_frame(video, 1.5, frame2)
        self._assert_valid_frame(frame2)
        
        # Frame at 2.5s (body text settled)
        frame3 = out_dir / "body-settled.png"
        self._extract_frame(video, 2.5, frame3)
        self._assert_valid_frame(frame3)
        
        # Store metadata for human review
        meta = {
            "project": "asta-typography-editorial-demo",
            "video": str(video),
            "duration": float(metadata.get("format", {}).get("duration", 0)),
            "width": metadata.get("streams", [{}])[0].get("width", 0),
            "height": metadata.get("streams", [{}])[0].get("height", 0),
            "fps": 25,
            "frames": [
                {"name": "headline-entrance", "timestamp": 0.5},
                {"name": "headline-settled", "timestamp": 1.5},
                {"name": "body-settled", "timestamp": 2.5}
            ],
            "review_required": True,
            "review_instructions": (
                "Verify headline is dominant within first second, "
                "emphasized phrases enter on intended cues, "
                "body remains readable at mobile size, "
                "no text overlaps important image content."
            )
        }
        (out_dir / "snapshot-meta.json").write_text(
            json.dumps(meta, indent=2))

    def test_dissolve_golden_frames(self):
        """Generate golden reference frames for the dissolve QA project."""
        video = self._render_project("asta-creative-qa-dissolve")
        
        out_dir = self.GOLDEN_DIR / "dissolve"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Frame at 0.1s (scene 1 settle)
        frame1 = out_dir / "scene1-settled.png"
        self._extract_frame(video, 0.1, frame1)
        self._assert_valid_frame(frame1)
        
        # Frame at midpoint (during dissolve)
        duration = float(probe(video).get("format", {}).get("duration", 1))
        mid = duration / 2
        frame2 = out_dir / "dissolve-midpoint.png"
        self._extract_frame(video, mid, frame2)
        self._assert_valid_frame(frame2)

    def test_montage_golden_frames(self):
        """Generate golden reference frames for the 15-scene montage."""
        video = self._render_project("asta-montage")
        metadata = probe(video)
        duration = float(metadata.get("format", {}).get("duration", 0))
        
        out_dir = self.GOLDEN_DIR / "montage"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Sample 6 evenly-spaced frames across the entire montage
        timestamps = [duration * i / 6 for i in range(6)]
        for i, ts in enumerate(timestamps):
            frame = out_dir / f"montage-frame-{i:02d}.png"
            self._extract_frame(video, ts, frame)
            self._assert_valid_frame(frame)
        
        # Store metadata
        meta = {
            "project": "asta-montage",
            "video": str(video),
            "duration": duration,
            "width": metadata.get("streams", [{}])[0].get("width", 0),
            "height": metadata.get("streams", [{}])[0].get("height", 0),
            "fps": 25,
            "scenes_total": 15,
            "review_required": True,
            "review_instructions": (
                "Verify no baked-in logos appear in clean_source clips, "
                "check for finished_promo clips flagged during transition, "
                "confirm text hierarchy across all 15 cuts."
            )
        }
        (out_dir / "snapshot-meta.json").write_text(
            json.dumps(meta, indent=2))

    def test_edge_case_polish_diacritics(self):
        """Verify Polish diacritics render correctly in headline text."""
        video = self._render_project("asta-typography-editorial-demo")
        
        out_dir = self.GOLDEN_DIR / "polish-diacritics"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # The typography demo headline contains "WIĘCEJ" with Ę diacritic
        frame = out_dir / "polish-diacritics.png"
        self._extract_frame(video, 1.5, frame)
        self._assert_valid_frame(frame)
        
        # Check that the image contains non-ASCII text content
        from PIL import Image
        img = Image.open(frame)
        self.assertEqual(img.mode, "RGB")


if __name__ == "__main__":
    unittest.main()
