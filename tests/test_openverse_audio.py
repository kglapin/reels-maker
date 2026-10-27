import os
import unittest
from unittest.mock import patch

from reels_maker.assets.openverse_audio import search_openverse_audio
from reels_maker.assets.provider_client import ProviderClient, ProviderError
from reels_maker.assets.search_cache import SearchCache


class OpenverseAudioTests(unittest.TestCase):
    def test_search_uses_shared_client_bearer_and_preserves_item_evidence(self):
        seen = []
        payload = {"results": [{
            "id": "audio-123", "title": "Soft wind", "creator": "<b>A. Maker</b>",
            "foreign_landing_url": "https://source.example/audio-123",
            "url": "https://cdn.example/audio-123.ogg",
            "license": "cc-by", "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "attribution": "Soft wind by A. Maker",
            "duration": 18250, "filetype": "ogg", "sha256": "abc123",
        }]}
        client = ProviderClient(cache=SearchCache(), transport=lambda url, headers: (
            seen.append((url, headers)) or payload))
        with patch.dict(os.environ, {"OPENVERSE_ACCESS_TOKEN": "mock-token"}):
            results = search_openverse_audio("soft wind", per_page=4, client=client)
            cached_results = search_openverse_audio("soft wind", per_page=4, client=client)

        self.assertEqual(len(results), 1)
        self.assertEqual(cached_results, results)
        self.assertEqual(len(seen), 1)
        item = results[0]
        self.assertEqual(item.creator, "A. Maker")
        self.assertEqual(item.source_url, "https://source.example/audio-123")
        self.assertEqual(item.license, "cc-by")
        self.assertEqual(item.license_url, "https://creativecommons.org/licenses/by/4.0/")
        self.assertEqual(item.attribution, "Soft wind by A. Maker")
        self.assertEqual(item.duration_seconds, 18.25)
        self.assertEqual(item.file_type, "ogg")
        self.assertEqual(item.checksum, "abc123")
        self.assertEqual(item.rights_status, "unknown")
        self.assertEqual(item.provenance()["rights_status"], "unknown")
        self.assertEqual(item.provenance()["audio_url"], "https://cdn.example/audio-123.ogg")
        self.assertEqual(item.provenance()["provider_url"], "https://openverse.org")
        self.assertIn("/v1/audio/?q=soft+wind&page_size=4", seen[0][0])
        self.assertEqual(seen[0][1]["Authorization"], "Bearer mock-token")

    def test_missing_token_uses_anonymous_tier_without_auth_header(self):
        seen = []
        client = ProviderClient(cache=SearchCache(), transport=lambda url, headers: (
            seen.append(headers) or {"results": []}))
        with patch.dict(os.environ, {}, clear=True):
            search_openverse_audio("ambient", client=client)
        self.assertEqual(len(seen), 1)
        self.assertNotIn("Authorization", seen[0])

    def test_optional_evidence_and_duration_are_safe_when_absent_or_malformed(self):
        client = ProviderClient(cache=SearchCache(), transport=lambda *_: {
            "results": [{"id": "minimal", "duration": "unknown"}]
        })
        with patch.dict(os.environ, {"OPENVERSE_ACCESS_TOKEN": "mock-token"}):
            item = search_openverse_audio("ambient", client=client)[0]
        self.assertEqual(item.creator, "Unknown")
        self.assertIsNone(item.duration_seconds)
        self.assertEqual(item.file_type, "")
        self.assertEqual(item.checksum, "")
        self.assertEqual(item.rights_status, "unknown")

    def test_page_size_bounds(self):
        with self.assertRaises(ValueError):
            search_openverse_audio("ambient", per_page=21)


if __name__ == "__main__":
    unittest.main()
