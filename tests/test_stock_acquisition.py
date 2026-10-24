import hashlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from reels_maker.assets.stock_media import StockAsset, apply_reviewed_rights_decision
from reels_maker.assets.stock_acquisition import (
    DownloadResponse, _validate_public_host, candidate_asset, candidate_record,
    download_cleared_asset, rank_candidates, search_with_fallback,
)


def public_dns(host, port, *, type):
    return [(None, None, None, None, ("93.184.216.34", port))]


def image_bytes():
    stream = io.BytesIO()
    Image.new("RGB", (12, 8), "red").save(stream, format="PNG")
    return stream.getvalue()


class StockAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.asset = StockAsset("openverse", "item-1", "preview", "source", "author",
                                12, 8, "https://upload.wikimedia.org/file", "source")

    def cleared(self, asset=None, platforms=None):
        asset = asset or self.asset
        return apply_reviewed_rights_decision(asset, {
            "provider": asset.provider, "asset_id": asset.asset_id,
            "source_url": asset.source_url, "download_url": asset.download_url,
            "decision": "cleared", "reviewer": "human", "review_date": "2026-10-23",
            "evidence": "review-1", "attribution": "author, CC BY 4.0",
            "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "allowed_platforms": platforms or ["instagram_reels"],
        })

    def test_missing_or_nonmatching_rights_refuses_before_transport(self):
        called = []
        with tempfile.TemporaryDirectory() as temp:
            brand = Path(temp) / "brands" / "demo"
            brand.mkdir(parents=True)
            for candidate in (self.asset, self.cleared(platforms=["youtube"])):
                with self.assertRaises(ValueError):
                    download_cleared_asset(candidate, brand="demo", root=temp,
                                           target_platform="instagram_reels",
                                           transport=lambda *args, **kwargs: called.append(1),
                                           resolve=public_dns)
        self.assertEqual(called, [])

    def test_verified_download_is_atomic_quarantined_and_reports_provenance(self):
        asset = self.cleared()
        content = image_bytes()
        calls = []

        def transport(url, **kwargs):
            calls.append((url, kwargs))
            return DownloadResponse(url, content, "image/png")

        with tempfile.TemporaryDirectory() as temp:
            brand = Path(temp) / "brands" / "demo"
            brand.mkdir(parents=True)
            report = download_cleared_asset(asset, brand="demo", root=temp,
                                            target_platform="instagram_reels",
                                            transport=transport, resolve=public_dns)
            path = Path(report["path"])
            self.assertEqual(path.parent, (brand / "imports").resolve())
            self.assertEqual(path.suffix, ".png")
            self.assertEqual(path.read_bytes(), content)
            self.assertEqual(report["sha256"], hashlib.sha256(content).hexdigest())
            self.assertEqual(report["approval"], "not_approved")
            self.assertEqual(report["verification"], {"format": "PNG", "width": 12, "height": 8})
            self.assertEqual(report["rights_decision"]["asset_id"], "item-1")
            self.assertEqual(len(calls), 1)
            self.assertFalse(list((brand / "imports").glob(".stock-*.tmp")))

    def test_host_allowlist_redirect_destination_and_byte_bound_fail_closed(self):
        asset = self.cleared()
        with tempfile.TemporaryDirectory() as temp:
            brand = Path(temp) / "brands" / "demo"
            brand.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "allowlisted"):
                download_cleared_asset(asset, brand="demo", root=temp,
                    target_platform="instagram_reels",
                    transport=lambda url, **kw: DownloadResponse("https://evil.example/a", image_bytes()),
                    resolve=public_dns)
            with self.assertRaisesRegex(ValueError, "private"):
                download_cleared_asset(asset, brand="demo", root=temp,
                    target_platform="instagram_reels",
                    transport=lambda url, **kw: DownloadResponse(url, image_bytes()),
                    resolve=lambda *args, **kw: [(None, None, None, None, ("127.0.0.1", 443))])
            with self.assertRaisesRegex(ValueError, "byte limit"):
                download_cleared_asset(asset, brand="demo", root=temp, max_bytes=10,
                    target_platform="instagram_reels",
                    transport=lambda url, **kw: DownloadResponse(url, image_bytes()),
                    resolve=public_dns)
            self.assertEqual(list((brand / "imports").iterdir()), [])

    def test_only_documented_pexels_vimeo_external_media_path_is_allowed(self):
        self.assertEqual(_validate_public_host(
            "https://player.vimeo.com/external/123/video.mp4", "pexels",
            resolve=public_dns), "player.vimeo.com")
        with self.assertRaisesRegex(ValueError, "external-media path"):
            _validate_public_host("https://player.vimeo.com/admin", "pexels",
                                  resolve=public_dns)

    def test_openverse_external_host_requires_exact_human_approved_item_url(self):
        url = "https://live.staticflickr.com/123/photo.jpg"
        with self.assertRaisesRegex(ValueError, "not allowlisted"):
            _validate_public_host(url, "openverse", resolve=public_dns)
        self.assertEqual(_validate_public_host(
            url, "openverse", resolve=public_dns,
            approved_host="live.staticflickr.com"), "live.staticflickr.com")

    def test_candidate_json_round_trip_cannot_smuggle_clearance(self):
        record = candidate_record(self.asset)
        self.assertEqual(record["rights_status"], "unknown")
        self.assertIsNone(candidate_asset(record).rights_decision)
        tampered = {**record, "rights_status": "cleared"}
        with self.assertRaisesRegex(ValueError, "cannot embed rights clearance"):
            candidate_asset(tampered)

    def test_unsplash_candidate_exposes_hotlink_only_download_limitation(self):
        unsplash = StockAsset("unsplash", "photo-1", "preview", "source", "author",
                              800, 600, "https://images.unsplash.com/photo.jpg", "source")
        record = candidate_record(unsplash)
        self.assertTrue(record["download_available"])
        self.assertFalse(record["local_download_supported"])

    def test_unknown_provider_dimensions_are_allowed_but_unavailable_urls_are_not(self):
        unknown = StockAsset("openverse", "no-dimensions", "preview", "source",
                             "author", 0, 0, "https://upload.wikimedia.org/file.jpg", "source")
        loaded = candidate_asset(candidate_record(unknown))
        self.assertEqual((loaded.width, loaded.height), (0, 0))
        missing_url = candidate_record(unknown)
        missing_url["download_url"] = ""
        with self.assertRaisesRegex(ValueError, "source/download URLs"):
            candidate_asset(missing_url)

    def test_failed_probe_or_invalid_image_leaves_no_partial_file(self):
        video = self.cleared(StockAsset("pexels", "vid", "preview", "source", "author",
            12, 8, "https://videos.pexels.com/file", "source", media_type="video"))
        with tempfile.TemporaryDirectory() as temp:
            brand = Path(temp) / "brands" / "demo"
            brand.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "FFprobe"):
                download_cleared_asset(video, brand="demo", root=temp,
                    target_platform="instagram_reels",
                    transport=lambda url, **kw: DownloadResponse(url, b"not-video"),
                    probe=lambda path, kind: {"streams": []}, resolve=public_dns)
            self.assertEqual(list((brand / "imports").iterdir()), [])

    def test_explicit_h264_transcode_is_verified_and_kept_in_quarantine(self):
        source = self.cleared(StockAsset("pexels", "synthetic-video", "preview", "source",
            "author", 320, 240, "https://videos.pexels.com/clip.mp4", "source",
            media_type="video"))
        with tempfile.TemporaryDirectory() as temp:
            original = Path(temp) / "synthetic.mp4"
            subprocess.run([
                "ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi",
                "-i", "color=c=green:s=320x240:d=1:r=24", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", str(original),
            ], check=True, capture_output=True, timeout=30)
            content = original.read_bytes()
            brand = Path(temp) / "brands" / "demo"
            brand.mkdir(parents=True)
            result = download_cleared_asset(
                source, brand="demo", root=temp, target_platform="instagram_reels",
                transcode_format="h264_mp4",
                transport=lambda url, **kwargs: DownloadResponse(url, content, "video/mp4"),
                resolve=public_dns,
            )
            output = Path(result["path"])
            self.assertEqual(output.parent, (brand / "imports").resolve())
            self.assertEqual(output.suffix, ".mp4")
            self.assertEqual(result["source_sha256"], hashlib.sha256(content).hexdigest())
            self.assertNotEqual(result["sha256"], result["source_sha256"])
            self.assertEqual(result["verification"]["codec"], "h264")
            self.assertIn("ffmpeg libx264", result["transform_recipe"])
            self.assertEqual(result["approval"], "not_approved")
            self.assertEqual(len(list((brand / "imports").glob("stock-*.mp4"))), 1)

    def test_unsupported_transcode_fails_before_network(self):
        asset = self.cleared()
        calls = []
        with tempfile.TemporaryDirectory() as temp:
            brand = Path(temp) / "brands" / "demo"
            brand.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "h264_mp4 or None"):
                download_cleared_asset(
                    asset, brand="demo", root=temp,
                    target_platform="instagram_reels", transcode_format="wav",
                    transport=lambda *args, **kwargs: calls.append(1), resolve=public_dns)
        self.assertEqual(calls, [])

    def test_search_falls_back_and_ranking_is_stable_across_input_order(self):
        a = StockAsset("pixabay", "same", "p", "s", "a", 1000, 1600, "u", "s")
        b = StockAsset("pexels", "same", "p", "s", "a", 1000, 1600, "u", "s")
        def failing(_):
            raise RuntimeError("offline")
        def succeeding(_):
            return [a, b]
        ranked, outcomes = search_with_fallback("query", [failing, succeeding], aspect=9/16)
        self.assertEqual([item.provider for item in ranked], ["pexels", "pixabay"])
        self.assertEqual(outcomes[0]["status"], "failed")
        self.assertEqual(outcomes[1]["count"], 2)
        self.assertEqual(rank_candidates([a, b], aspect=9/16),
                         rank_candidates([b, a], aspect=9/16))


if __name__ == "__main__":
    unittest.main()
