"""Explicitly opt-in live-provider smoke tests for MD-106.

The default CI/local suite never contacts providers. To run the search-only
check, set REELS_MAKER_LIVE_MEDIA_TESTS=1 and a provider plus valid credentials.
To test a real quarantine download as well, also set
REELS_MAKER_LIVE_MEDIA_DOWNLOAD=1, REELS_MAKER_LIVE_ASSET_ID and
REELS_MAKER_LIVE_RIGHTS_DECISION to a human-reviewed, exact-URL decision file.
Downloads use a TemporaryDirectory and are never added to the repository.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


OPT_IN = os.environ.get("REELS_MAKER_LIVE_MEDIA_TESTS") == "1"
PROVIDER = os.environ.get("REELS_MAKER_LIVE_PROVIDER", "wikimedia_commons")
QUERY = os.environ.get("REELS_MAKER_LIVE_QUERY", "wind turbines")
ASSET_ID = os.environ.get("REELS_MAKER_LIVE_ASSET_ID", "")
RIGHTS_FILE = os.environ.get("REELS_MAKER_LIVE_RIGHTS_DECISION", "")
PLATFORM = os.environ.get("REELS_MAKER_LIVE_PLATFORM", "instagram_reels")
DOWNLOAD_OPT_IN = os.environ.get("REELS_MAKER_LIVE_MEDIA_DOWNLOAD") == "1"


@unittest.skipUnless(OPT_IN,
                     "Set REELS_MAKER_LIVE_MEDIA_TESTS=1 to enable external API smoke tests")
class LiveMediaSmokeTests(unittest.TestCase):
    def test_search_returns_candidates_not_automatic_rights_clearance(self):
        with tempfile.TemporaryDirectory(prefix="reels-live-search-") as directory:
            report_path = Path(directory) / "candidates.json"
            command = [
                sys.executable, "-m", "reels_maker.cli", "media-search", QUERY,
                "--provider", PROVIDER, "--kind", "image", "--limit", "2",
                "--output", str(report_path), "--json",
            ]
            completed = subprocess.run(command, text=True, capture_output=True,
                                       check=False, timeout=60)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            envelope = json.loads(completed.stdout)
            self.assertEqual(envelope["status"], "ok")
            self.assertEqual(envelope["search_status"], "ok")
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertGreater(len(report["candidates"]), 0)
            self.assertTrue(all(item["rights_status"] == "unknown"
                                for item in report["candidates"]))

    @unittest.skipUnless(OPT_IN and DOWNLOAD_OPT_IN and ASSET_ID and RIGHTS_FILE
                         and PROVIDER != "unsplash",
        "Real media download additionally requires explicit opt-in, asset ID, reviewed rights JSON, and a supported local-download provider")
    def test_reviewed_item_download_stays_in_temporary_quarantine(self):
        rights_path = Path(RIGHTS_FILE).expanduser().resolve()
        decision = json.loads(rights_path.read_text(encoding="utf-8"))
        self.assertEqual(decision.get("provider"), PROVIDER)
        self.assertEqual(str(decision.get("asset_id")), ASSET_ID)
        with tempfile.TemporaryDirectory(prefix="reels-live-download-") as directory:
            root = Path(directory)
            brand = "live-smoke"
            (root / "brands" / brand).mkdir(parents=True)
            candidate_path = root / "candidates.json"
            search = subprocess.run([
                sys.executable, "-m", "reels_maker.cli", "media-search", QUERY,
                "--provider", PROVIDER, "--kind", "image", "--limit", "2",
                "--output", str(candidate_path), "--json",
            ], text=True, capture_output=True, check=False, timeout=60)
            self.assertEqual(search.returncode, 0, search.stderr)
            download = subprocess.run([
                sys.executable, "-m", "reels_maker.cli", "media-download",
                str(candidate_path), "--provider", PROVIDER, "--asset-id", ASSET_ID,
                "--rights-decision", str(rights_path), "--brand", brand,
                "--root", str(root), "--target-platform", PLATFORM, "--json",
            ], text=True, capture_output=True, check=False, timeout=180)
            self.assertEqual(download.returncode, 0, download.stderr)
            response = json.loads(download.stdout)
            staged = Path(response["download"]["path"]).resolve()
            self.assertTrue(staged.is_relative_to((root / "brands" / brand / "imports").resolve()))
            self.assertEqual(response["download"]["approval"], "not_approved")
            self.assertFalse((root / "brands" / brand / "media").exists())


if __name__ == "__main__":
    unittest.main()
