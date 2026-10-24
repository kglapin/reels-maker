"""No-network integration tests for public media search/download CLI wiring."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reels_maker.assets.stock_acquisition import candidate_record
from reels_maker.assets.stock_media import StockAsset
from reels_maker.cli import main


class MediaCliTests(unittest.TestCase):
    def call_cli(self, argv):
        output = io.StringIO()
        with patch("sys.argv", ["reels-maker", *argv]), contextlib.redirect_stdout(output):
            code = main()
        return code, json.loads(output.getvalue())

    def test_media_search_writes_ranked_candidate_report_without_approval(self):
        asset = StockAsset(
            "wikimedia_commons", "file-123", "https://upload.wikimedia.org/thumb",
            "https://commons.wikimedia.org/wiki/File:Demo.jpg", "Demo author",
            1600, 900, "https://upload.wikimedia.org/file.jpg",
            "https://commons.wikimedia.org/wiki/File:Demo.jpg",
            license="CC BY 4.0", license_url="https://creativecommons.org/licenses/by/4.0/",
            provider_url="https://commons.wikimedia.org")
        with tempfile.TemporaryDirectory() as temp:
            report_path = Path(temp) / "search.json"
            with patch("reels_maker.assets.stock_media.search_wikimedia_commons",
                       return_value=[asset]) as search:
                code, response = self.call_cli([
                    "media-search", "solar farm", "--provider", "wikimedia_commons",
                    "--kind", "image", "--output", str(report_path), "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["candidate_count"], 1)
            self.assertEqual(response["candidates"][0]["rights_status"], "unknown")
            self.assertEqual(response["providers"][0]["status"], "ok")
            self.assertTrue(report_path.is_file())
            self.assertEqual(json.loads(report_path.read_text())["candidate_count"], 1)
            search.assert_called_once_with("solar farm", per_page=12,
                                           media_type="image")

    def test_video_search_all_means_only_video_capable_providers(self):
        pexels = StockAsset(
            "pexels", "video-p", "thumb", "https://www.pexels.com/video/1", "Creator",
            1920, 1080, "https://videos.pexels.com/clip.mp4", "https://www.pexels.com",
            media_type="video")
        pixabay = StockAsset(
            "pixabay", "video-x", "thumb", "https://pixabay.com/videos/1", "Creator",
            1920, 1080, "https://cdn.pixabay.com/video.mp4", "https://pixabay.com",
            media_type="video")
        commons = StockAsset(
            "wikimedia_commons", "video-w", "thumb",
            "https://commons.wikimedia.org/wiki/File:Demo.webm", "Creator",
            1920, 1080, "https://upload.wikimedia.org/video.webm",
            "https://commons.wikimedia.org/wiki/File:Demo.webm",
            media_type="video")
        with patch("reels_maker.assets.stock_media.search_pexels_videos",
                   return_value=[pexels]) as pexels_search, \
                patch("reels_maker.assets.stock_media.search_pixabay_videos",
                      return_value=[pixabay]) as pixabay_search, \
                patch("reels_maker.assets.stock_media.search_wikimedia_commons",
                      return_value=[commons]) as commons_search:
            code, response = self.call_cli([
                "media-search", "wind farm", "--provider", "all", "--kind", "video",
                "--aspect", "1.777", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual([item["provider"] for item in response["candidates"]],
                         ["pexels", "pixabay", "wikimedia_commons"])
        self.assertEqual([item["provider"] for item in response["providers"]],
                         ["pexels", "pixabay", "wikimedia_commons"])
        pexels_search.assert_called_once_with("wind farm", per_page=12,
                                              orientation="landscape")
        pixabay_search.assert_called_once_with("wind farm", per_page=12)
        commons_search.assert_called_once_with("wind farm", per_page=12,
                                               media_type="video")

    def test_audio_search_uses_keyless_and_oauth_audio_providers(self):
        commons = StockAsset(
            "wikimedia_commons", "audio-1", "https://upload.wikimedia.org/a.ogg",
            "https://commons.wikimedia.org/wiki/File:A.ogg", "Creator", 0, 0,
            "https://upload.wikimedia.org/a.ogg",
            "https://commons.wikimedia.org/wiki/File:A.ogg",
            media_type="audio", duration_seconds=3)
        from reels_maker.assets.openverse_audio import OpenverseAudioResult
        openverse = OpenverseAudioResult(
            provider="openverse", asset_id="ov-9", title="Wind loop",
            creator="Mixer", source_url="https://openverse.org/audio/ov-9",
            audio_url="https://upload.wikimedia.org/wind.mp3",
            license="cc0", license_url="https://creativecommons.org/publicdomain/zero/1.0/",
            attribution="Mixer, CC0", duration_seconds=5.5,
            file_type="mp3", checksum="abc")
        with patch("reels_maker.assets.stock_media.search_wikimedia_commons",
                   return_value=[commons]) as commons_search, \
                patch("reels_maker.assets.openverse_audio.search_openverse_audio",
                      return_value=[openverse]) as openverse_search:
            code, response = self.call_cli([
                "media-search", "wind whoosh", "--provider", "all",
                "--kind", "audio", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(response["search_status"], "ok")
        self.assertEqual({item["provider"] for item in response["providers"]},
                         {"wikimedia_commons", "openverse"})
        self.assertEqual({item["media_type"] for item in response["candidates"]},
                         {"audio"})
        ov = next(item for item in response["candidates"]
                  if item["provider"] == "openverse")
        self.assertEqual(ov["download_url"], "https://upload.wikimedia.org/wind.mp3")
        self.assertEqual(ov["rights_status"], "unknown")
        commons_search.assert_called_once_with("wind whoosh", per_page=12,
                                               media_type="audio")
        openverse_search.assert_called_once_with("wind whoosh", per_page=12)

    def test_audio_search_rejects_visual_only_providers(self):
        output = io.StringIO()
        argv = ["reels-maker", "media-search", "sfx", "--provider", "unsplash",
                "--kind", "audio", "--json"]
        with patch("sys.argv", argv), contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = main()
        self.assertEqual(code, 2)
        self.assertIn("audio search is supported only by", stderr.getvalue())

    def test_provider_failure_is_visible_and_not_reported_as_empty_success(self):
        with patch("reels_maker.assets.stock_media.search_wikimedia_commons",
                   side_effect=RuntimeError("offline")):
            code, response = self.call_cli([
                "media-search", "solar", "--provider", "wikimedia_commons", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(response["search_status"], "unavailable")
        self.assertEqual(response["candidate_count"], 0)
        self.assertEqual(response["providers"][0]["status"], "failed")
        self.assertIn("offline", response["providers"][0]["error"])

    def test_media_download_binds_exact_candidate_and_stages_only_quarantine(self):
        asset = StockAsset(
            "wikimedia_commons", "file-456", "preview",
            "https://commons.wikimedia.org/wiki/File:Demo.jpg", "Demo author",
            1600, 900, "https://upload.wikimedia.org/file.jpg", "source",
            license="CC BY 4.0", license_url="https://creativecommons.org/licenses/by/4.0/",
            provider_url="https://commons.wikimedia.org")
        with tempfile.TemporaryDirectory() as temp:
            candidate_path = Path(temp) / "candidate.json"
            candidate_path.write_text(json.dumps({"candidates": [candidate_record(asset)]}))
            decision_path = Path(temp) / "decision.json"
            decision_path.write_text(json.dumps({
                "provider": asset.provider, "asset_id": asset.asset_id,
                "source_url": asset.source_url, "download_url": asset.download_url,
                "decision": "cleared", "reviewer": "Human reviewer",
                "review_date": "2026-10-24", "evidence": "rights-review-17",
                "attribution": "Demo author, CC BY 4.0",
                "license": asset.license, "license_url": asset.license_url,
                "allowed_platforms": ["instagram_reels"],
            }))
            with patch("reels_maker.assets.stock_acquisition.download_cleared_asset",
                       return_value={"status": "downloaded_to_quarantine",
                                     "approval": "not_approved"}) as download:
                code, response = self.call_cli([
                    "media-download", str(candidate_path), "--provider", asset.provider,
                    "--asset-id", asset.asset_id, "--rights-decision", str(decision_path),
                    "--brand", "synthetic", "--root", temp,
                    "--target-platform", "instagram_reels", "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["download"]["approval"], "not_approved")
            passed = download.call_args.args[0]
            self.assertEqual(passed.rights_status, "cleared")
            self.assertEqual(passed.rights_decision["download_url"], asset.download_url)
            self.assertEqual(download.call_args.kwargs["target_platform"], "instagram_reels")

    def test_media_download_rejects_url_tampering_in_rights_decision(self):
        asset = StockAsset("wikimedia_commons", "tamper", "preview", "source", "author",
                           100, 100, "https://upload.wikimedia.org/a.jpg", "source",
                           license="CC0", license_url="https://creativecommons.org/publicdomain/zero/1.0/")
        with tempfile.TemporaryDirectory() as temp:
            candidate_path = Path(temp) / "candidate.json"
            candidate_path.write_text(json.dumps(candidate_record(asset)))
            decision_path = Path(temp) / "decision.json"
            decision_path.write_text(json.dumps({
                "provider": asset.provider, "asset_id": asset.asset_id,
                "source_url": asset.source_url, "download_url": "https://upload.wikimedia.org/other.jpg",
                "decision": "cleared", "reviewer": "Human reviewer",
                "review_date": "2026-10-24", "evidence": "review",
                "attribution": "Creator, CC0",
                "license": "CC0", "license_url": asset.license_url,
                "allowed_platforms": ["instagram_reels"],
            }))
            output = io.StringIO()
            argv = ["reels-maker", "media-download", str(candidate_path),
                    "--provider", asset.provider, "--asset-id", asset.asset_id,
                    "--rights-decision", str(decision_path), "--brand", "synthetic",
                    "--root", temp, "--target-platform", "instagram_reels", "--json"]
            with patch("sys.argv", argv), contextlib.redirect_stderr(io.StringIO()) as stderr:
                code = main()
            self.assertEqual(code, 2)
            self.assertIn("exact source and download URL", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
