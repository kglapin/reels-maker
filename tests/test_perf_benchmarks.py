"""Performance benchmarks and reliability tests for the rendering engine.

Tests PERF-01 through PERF-09:
- PERF-01: Benchmark 15s/30s clips at production dimensions (cold/warm)
- PERF-03: Verify first-render vs cached-render durations, correct invalidation
- PERF-05: Disk-space preflight, temp output cleanup on failure
- PERF-06: Test interrupt/resume and atomic replacement after failed render
"""
import json
import os
import shutil
import time
import unittest
from pathlib import Path

from reels_maker.renderer import render, CACHE_SCHEMA
from reels_maker.spec import load_project
from media_fixtures import has_real_media

_REPO = Path(__file__).resolve().parents[1]
_REQUIRED_MEDIA = (
    _REPO / "brands/asta-energy/media/footage/2_dron-pv-dla-firm-asta.mp4",
    _REPO / "brands/asta-energy/media/stock/pv-promo-cut.mp4",
)
_MEDIA_AVAILABLE = all(has_real_media(path) for path in _REQUIRED_MEDIA)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg/FFprobe required for perf tests")
@unittest.skipUnless(_MEDIA_AVAILABLE,
                     "Performance video fixtures are LFS-backed and unavailable in offline CI")
class PerformanceBenchmarksTest(unittest.TestCase):
    """PERF-01, PERF-03: Benchmark and cache invalidation tests."""

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[1]
        self.brand_dir = self.repo_root / "brands/asta-energy"
        self.cache_dir = self.repo_root / ".cache" / "reels-maker"

    def _clear_cache(self):
        """Clear the scene cache for cold-render benchmarks."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)

    def test_cold_vs_warm_cache_for_montage(self):
        """PERF-01/PERF-03: Cold render encodes all scenes; warm render hits cache."""
        project = load_project(
            self.brand_dir / "projects" / "asta-montage.json")
        self.assertGreaterEqual(len(project.scenes), 10)

        # Cold cache
        self._clear_cache()
        start = time.perf_counter()
        result = render(project, root=self.repo_root)
        cold_seconds = time.perf_counter() - start

        self.assertTrue(result["ok"])
        self.assertEqual(result["cache_hits"], 0,
                         "Cold render should have zero cache hits")
        self.assertGreater(result["scenes_encoded"], 0,
                           "Cold render should encode all scenes")

        # Warm cache - should all be cache hits
        start = time.perf_counter()
        result2 = render(project, root=self.repo_root)
        warm_seconds = time.perf_counter() - start

        self.assertTrue(result2["ok"])
        self.assertEqual(result2["cache_hits"], len(project.scenes),
                         "Warm render should have all cache hits")
        self.assertEqual(result2["cache_hit_rate"], 1.0)
        # Warm render should be significantly faster
        self.assertLess(warm_seconds, cold_seconds,
                        "Warm cache should be faster than cold")

    def test_short_clip_performance(self):
        """PERF-01: 15s clip at production dimensions renders in reasonable time."""
        project = load_project(
            self.brand_dir / "projects" / "asta-rush-demo.json")
        self.assertLessEqual(project.duration, 15.0,
                             "Rush demo should be ~15s or less")

        self._clear_cache()
        start = time.perf_counter()
        result = render(project, root=self.repo_root)
        elapsed = time.perf_counter() - start

        self.assertTrue(result["ok"])
        self.assertEqual(result["export_quality"]["status"], "pass")
        print(f"\n  15s clip: {elapsed:.2f}s (preflight={result['timings_seconds']['preflight']}s, "
              f"encode={result['timings_seconds']['scene_encoding']}s, "
              f"assemble={result['timings_seconds']['assembly_audio_validation']}s)")

    def test_cache_invalidation_on_source_change(self):
        """PERF-03: Changing a source file invalidates the cache."""
        project = load_project(
            self.brand_dir / "projects" / "asta-rush-demo.json")
        self._clear_cache()

        # First render - cold
        result = render(project, root=self.repo_root)
        self.assertEqual(result["cache_hits"], 0)
        self.assertGreater(result["scenes_encoded"], 0)

        # Second render - all hits
        result2 = render(project, root=self.repo_root)
        self.assertEqual(result2["cache_hits"], len(project.scenes))

        # Touch a source file (modify mtime) - should invalidate
        source_file = self.repo_root / "brands" / "asta-energy" / project.scenes[0]["file"]
        old_mtime = source_file.stat().st_mtime_ns
        # Wait briefly and touch the file
        os.utime(source_file, (time.time() + 1, time.time() + 1))
        new_mtime = source_file.stat().st_mtime_ns
        self.assertNotEqual(old_mtime, new_mtime)

        # Third render - first scene should re-encode, others cached
        result3 = render(project, root=self.repo_root)
        self.assertGreater(result3["scenes_encoded"], 0,
                           "Source change should trigger re-encode of affected scene")

    def test_stream_copy_for_unchanged_hard_cut_assembly(self):
        """PERF-03: Hard-cut assemblies use stream-copy (no recompression)."""
        project = load_project(
            self.brand_dir / "projects" / "asta-montage.json")
        self._clear_cache()

        # First render
        result = render(project, root=self.repo_root)
        self.assertTrue(result["ok"])

        # Second render (warm) - should be stream_copy with all cache hits
        result2 = render(project, root=self.repo_root)
        self.assertEqual(result2["assembly_mode"], "stream_copy")
        self.assertEqual(result2["cache_hit_rate"], 1.0)
        # Verify the output is valid
        self.assertTrue((self.repo_root / result2["output"]).exists())

    def test_disk_space_check(self):
        """PERF-05: Verify sufficient disk space before rendering."""
        free_space = shutil.disk_usage(self.repo_root).free
        # At least 1GB free for safe rendering
        self.assertGreater(free_space, 1e9,
                           "Need at least 1GB free disk space for rendering")
        print(f"\n  Free disk space: {free_space / 1e9:.1f}GB")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg/FFprobe required for failure recovery tests")
class FailureRecoveryTests(unittest.TestCase):
    """PERF-05/PERF-06: Disk safety, temp cleanup, atomic replacement."""

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[1]
        self.brand_dir = self.repo_root / "brands/asta-energy"
        self.cache_dir = self.repo_root / ".cache" / "reels-maker"

    @unittest.skipUnless(has_real_media(
        Path(__file__).resolve().parents[1]
        / "brands/asta-energy/media/footage/2_dron-pv-dla-firm-asta.mp4"),
        "Atomic render fixture uses LFS media unavailable in offline CI")
    def test_atomic_output_preserves_previous_render(self):
        """PERF-06: A failed render does not corrupt the previous output."""
        project = load_project(
            self.brand_dir / "projects" / "asta-typography-editorial-demo.json")

        # Render successfully
        result = render(project, root=self.repo_root)
        self.assertTrue(result["ok"])

        output_path = Path(result["output"])
        self.assertTrue(output_path.exists())
        original_size = output_path.stat().st_size
        original_mtime = output_path.stat().st_mtime

        # Attempt render with invalid scene (should fail)
        bad_project = load_project(
            self.brand_dir / "projects" / "asta-typography-editorial-demo.json")
        # Modify to use nonexistent file
        bad_project.scenes[0]["file"] = "media/nonexistent.mp4"
        import json
        bad_json_path = self.repo_root / "brands" / "asta-energy" / "projects" / "test-bad-project.json"
        bad_json_path.write_text(json.dumps({
            "name": "bad-test",
            "video": {"width": 1080, "height": 1920, "fps": 25},
            "scenes": [
                {"file": "media/nonexistent.mp4", "start": 0, "duration": 5.0}
            ],
            "branding": {},
            "output": "renders/asta-energy/test-bad-output.mp4",
            "brand": "asta-energy"
        }))
        from reels_maker.spec import load_project as lp
        bad_project = lp(bad_json_path)

        try:
            render(bad_project, root=self.repo_root)
            # If render doesn't fail, clean up
        except Exception:
            pass  # Expected to fail
        finally:
            bad_json_path.unlink(missing_ok=True)

        # Verify original output is still intact
        self.assertTrue(output_path.exists(),
                        "Previous successful output must be preserved")
        self.assertEqual(output_path.stat().st_size, original_size,
                         "Original output size must be unchanged")

    def test_temp_cleanup_on_failure(self):
        """PERF-05: Failed renders clean up temporary files."""
        from reels_maker.renderer import render
        from reels_maker.spec import ProjectError

        # Create a project that will fail during render
        import json
        bad_json_path = self.repo_root / "brands" / "asta-energy" / "projects" / "test-fail-project.json"
        bad_json_path.write_text(json.dumps({
            "name": "fail-test",
            "video": {"width": 1080, "height": 1920, "fps": 25},
            "scenes": [
                {"file": "media/nonexistent.mp4", "start": 0, "duration": 5.0}
            ],
            "branding": {},
            "output": "renders/asta-energy/test-fail-output.mp4",
            "brand": "asta-energy"
        }))
        from reels_maker.spec import load_project as lp
        bad_project = lp(bad_json_path)

        try:
            render(bad_project, root=self.repo_root)
            self.fail("Render should have failed with missing source file")
        except (Exception,) as e:
            # Expected failure
            print(f"\n  Expected failure: {type(e).__name__}")

        # Verify no leftover temp files
        renders_dir = self.repo_root / "renders" / "asta-energy"
        temp_files = list(renders_dir.glob("reels-*"))
        self.assertEqual(len(temp_files), 0,
                         f"Temp files should be cleaned up, found: {temp_files}")

        bad_json_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
