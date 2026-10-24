"""MD-06 support: Pixabay audio acquisition is guarded and quarantine-first."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from reels_maker import pixabay
from reels_maker.pixabay import (PixabayError, download_candidates,
                                 parse_tracks, search_page_url)

MP3 = b"ID3\x03fake-audio-frame-fake-audio-frame"
A_HTML = ('<html><script>window.__NOTHING__=1</script>'
          'https://cdn.pixabay.com/download/audio/2022/03/15/'
          'audio_718d3a1081.mp3" '
          '"https://cdn.pixabay.com/audio/2022/03/15/'
          'audio_718d3a1081.mp3" '
          'https://cdn.pixabay.com/download/audio/2021/08/11/'
          'audio_0e0dfc1035.mp3"</html>')
BOOTSTRAP = json.dumps({"results": [
    {"id": 9, "title": "Calm Sunrise",
     "audio_url": "https://cdn.pixabay.com/audio/2022/a9.mp3",
     "duration": 95},
    {"id": 4, "title": "Uplift Pop",
     "audio_url": "https://cdn.pixabay.com/audio/2022/b8.mp3?x=1",
     "duration": 120},
]})
BOOTSTRAP_HTML = ('<html><script>window.__BOOTSTRAP_URL__='
                  '"/bootstrap.json"</script></html>')


class PixabayParsingTests(unittest.TestCase):
    def test_html_fallback_yields_deduplicated_candidates(self):
        tracks = parse_tracks(A_HTML, base_url=search_page_url("energetic"))
        self.assertEqual(len(tracks), 2)
        self.assertTrue(all(t["url"].endswith(".mp3") for t in tracks))
        self.assertEqual(tracks[0]["source"], "html-fallback")

    def test_bootstrap_json_carries_titles_and_clean_urls(self):
        original = pixabay.http_get

        def fake_http_get(url, *, cookies=None, timeout=30):
            assert url.endswith("/bootstrap.json")
            return BOOTSTRAP.encode()

        pixabay.http_get = fake_http_get
        try:
            tracks = parse_tracks(BOOTSTRAP_HTML,
                                  base_url="https://pixabay.com/pl/music/")
        finally:
            pixabay.http_get = original
        self.assertEqual([t["title"] for t in tracks],
                         ["Calm Sunrise", "Uplift Pop"])
        self.assertFalse(tracks[1]["url"].endswith("?x=1"))

    def test_real_bootstrap_shape_src_and_filename(self):
        """Verified live shape: items carry 'src' + readable 'filename'."""
        original = pixabay.http_get
        payload = json.dumps({"data": [
            {"src": "https://cdn.pixabay.com/audio/2022/03/15/audio_a7.mp3",
             "filename": "spy-always-dies-along-93740.mp3",
             "downloadUrl": "/pl/music/download/id-93740.mp3",
             "waveformUrl": "/pl/music/93740/waveform.json"},
            {"src": "https://cdn.pixabay.com/audio/2022/xx/audio_9z.mp3?x=1"},
        ]}).encode()

        def fake_http_get(url, *, cookies=None, timeout=30):
            return payload

        pixabay.http_get = fake_http_get
        try:
            tracks = parse_tracks(BOOTSTRAP_HTML.replace("bootstrap.json",
                                                         "ok.json"))
        finally:
            pixabay.http_get = original
        titles = [t["title"] for t in tracks]
        self.assertEqual(titles[0], "spy always dies along 93740")
        self.assertTrue(titles[1].startswith("audio 9z"))
        self.assertFalse(tracks[1]["url"].endswith("?x=1"))

    def test_track_list_tolerates_title_comments(self):
        source = ("# copied from devtools\n"
                  "https://cdn.pixabay.com/audio/2022/03/15/audio_a7.mp3 "
                  "# Spy Always Dies\n")
        tracks = pixabay.parse_track_list(source)
        self.assertEqual(tracks[0]["title"], "Spy Always Dies")

    def test_challenge_page_is_rejected_with_guidance(self):
        with self.assertRaises(PixabayError) as ctx:
            parse_tracks("<title>Just a moment...</title>")
        self.assertIn("challenge", str(ctx.exception))

    def test_http_403_challenge_emits_workaround_guidance(self):
        body = io.BytesIO(b"<html><title>Just a moment...</title></html>")
        error = HTTPError("https://pixabay.com/pl/music/search/x/", 403,
                          "Forbidden", {}, body)
        with patch("reels_maker.pixabay.urlopen", side_effect=error):
            with self.assertRaises(PixabayError) as ctx:
                pixabay.fetch_search_page("x")
        message = str(ctx.exception)
        self.assertIn("--page-file", message)
        self.assertIn("--tracks-file", message)
        self.assertIn("cf_clearance", message)

    def test_http_error_without_challenge_keeps_plain_status(self):
        body = io.BytesIO(b"server exploded")
        error = HTTPError("https://pixabay.com/x", 404, "Not Found", {}, body)
        with patch("reels_maker.pixabay.urlopen", side_effect=error):
            with self.assertRaises(PixabayError) as ctx:
                pixabay.http_get("https://pixabay.com/x")
        self.assertIn("HTTP 404", str(ctx.exception))

    def test_region_slugs(self):
        self.assertEqual(
            search_page_url("sloneczna energia", "sound-effects"),
            "https://pixabay.com/pl/sound-effects/search/sloneczna-energia/")

    def test_tracks_file_parse_builds_candidates(self):
        source = ("# copied from the browser network tab\n"
                  "https://cdn.pixabay.com/download/audio/2026/03/12/"
                  "audio_abc123.mp3?filename=test.mp3\n")
        tracks = pixabay.parse_track_list(source)
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0]["title"], "audio abc123")
        self.assertFalse(tracks[0]["url"].endswith("?filename=test.mp3"))
        with self.assertRaises(PixabayError):
            pixabay.parse_track_list("https://example.com/x.mp3")


class PixabayDownloadTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.tracks = parse_tracks(A_HTML)
        self.original = pixabay.http_get

    def tearDown(self):
        pixabay.http_get = self.original
        self._tmp.cleanup()

    def test_only_picked_files_land_in_imports_with_license_report(self):
        def fake_http_get(url, *, cookies=None, timeout=30):
            return MP3

        pixabay.http_get = fake_http_get
        destination = self.base / "brands" / "acme" / "imports" / "audio"
        report = download_candidates(self.tracks, destination, "2,1",
                                     kind="music")
        files = [Path(item["file"]) for item in report["files"]]
        self.assertEqual(len(files), 2)
        self.assertTrue(all(
            "imports" in path.parts and not any(p == "media" for p in path.parts)
            for path in files))
        self.assertEqual(report["editorial_state"], "quarantine")
        self.assertEqual(report["license"]["license"],
                         "Pixabay Content License")
        self.assertIn("Content ID", report["license"]["summary"])
        self.assertTrue(files[0].read_bytes().startswith(b"ID3"))

    def test_media_directory_is_forbidden_for_downloads(self):
        destination = self.base / "brands" / "acme" / "media" / "audio"
        with self.assertRaises(PixabayError) as ctx:
            download_candidates(self.tracks, destination, "1", kind="music")
        self.assertIn("imports", str(ctx.exception))

    def test_non_mp3_payload_is_rejected(self):
        pixabay.http_get = lambda url, *, cookies=None, timeout=30: b"<html>404"
        destination = self.base / "brands" / "acme" / "imports" / "audio"
        with self.assertRaises(PixabayError) as ctx:
            download_candidates(self.tracks, destination, "2", kind="music")
        self.assertIn("not MP3", str(ctx.exception))

    def test_out_of_range_pick_is_named(self):
        destination = self.base / "brands" / "acme" / "imports" / "audio"
        with self.assertRaises(PixabayError) as ctx:
            download_candidates(self.tracks, destination, "7", kind="music")
        self.assertIn("outside 1..2", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
