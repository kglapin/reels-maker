"""MD-09 acceptance: per-scene studio cache, invalidation and recovery."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from reels_maker.ffmpeg import RenderError
from reels_maker.renderers.studio import probe_output, render_studio
from reels_maker.studio import load_studio

FFMPEG = shutil.which("ffmpeg")


def _manifest(path: Path, headline: str = "CACHE A") -> None:
    path.write_text(json.dumps({
        "name": "cache-bench",
        "video": {"width": 360, "height": 640, "fps": 20},
        "scenes": [
            {"type": "statement", "duration": 1.0, "headline": headline},
            {"type": "amount", "duration": .8, "value": 12000,
             "visual": "none", "kicker": "TEST", "subtitle": "PODPIS"},
            {"type": "cta", "duration": .9, "headline": "KONTAKT KURS",
             "phone": "+00 000 000 000", "line_one": "TAG",
             "website": "example.org"},
        ],
        "export": {"profile": "preview"},
    }), encoding="utf-8")


class StudioRenderCacheTests(unittest.TestCase):
    def test_cold_warm_and_invalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest = base / "cache.json"
            _manifest(manifest)
            cache = base / "seg-cache"
            cold = render_studio(load_studio(manifest, root=base),
                                 cache_dir=cache, supersample=1)
            warm = render_studio(load_studio(manifest, root=base),
                                 cache_dir=cache, supersample=1)
            self.assertEqual(cold["cache_misses"], 3)
            self.assertEqual(cold["cache_hits"], 0)
            self.assertEqual(warm["cache_hits"], 3)
            self.assertEqual(warm["cache_misses"], 0)
            self.assertLess(warm["render_seconds"], cold["render_seconds"])
            self.assertTrue(warm["cache_signature"])
            self.assertLess(warm["render_seconds"], 2.0)
            # Any scene edit or encoder change must invalidate that scene.
            _manifest(manifest, headline="CACHE B")
            changed = render_studio(load_studio(manifest, root=base),
                                    cache_dir=cache, supersample=1)
            self.assertEqual(changed["cache_misses"], 3)
            self.assertNotEqual(changed["cache_signature"][:6],
                                cold["cache_signature"][:6])

    def test_corrupt_cache_object_fails_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest = base / "cache.json"
            _manifest(manifest)
            cache = base / "seg-cache"
            cold = render_studio(load_studio(manifest, root=base),
                                 cache_dir=cache, supersample=1)
            output = Path(cold["output"])
            previous = output.read_bytes()
            # A cache entry damaged after publication must fail loudly and
            # leave the last good delivery untouched.
            for cached in cache.glob("*.mp4"):
                cached.write_bytes(b"corrupted-bytes-not-an-mp4")
            with self.assertRaises(RenderError):
                render_studio(load_studio(manifest, root=base),
                              cache_dir=cache, supersample=1)
            self.assertEqual(output.read_bytes(), previous)
            self.assertEqual(list(base.glob(".reels-studio-*")), [])

    def test_full_resolution_smoke_at_final_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest = base / "final.json"
            manifest.write_text(json.dumps({
                "name": "studio-final-smoke",
                "video": {"width": 1080, "height": 1920, "fps": 30},
                "scenes": [{"type": "statement", "duration": 1.2,
                            "headline": "PEŁNA ROZDZIELCZOŚĆ"}],
                "export": {"profile": "final"},
            }), encoding="utf-8")
            project = load_studio(manifest, root=base)
            result = render_studio(project, supersample=1)
            metadata = probe_output(Path(result["output"]))
            self.assertEqual((metadata["width"], metadata["height"]),
                             (1080, 1920))
            self.assertEqual(result["frames"], 36)
            self.assertEqual(result["export_quality"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
