import os
import hashlib
from email.message import Message
from email.utils import formatdate
import stat
import unittest
from collections import deque
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch
from urllib.error import HTTPError

from reels_maker.assets.provider_client import ProviderClient, ProviderError, RateLimitError
from reels_maker.assets.search_cache import SearchCache


class ProviderClientTests(unittest.TestCase):
    def test_credentials_required_and_pixabay_key_not_sent_as_header(self):
        client = ProviderClient(cache=SearchCache(), transport=lambda *_: {})
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ProviderError, "PEXELS_API_KEY"):
                client.get_json("pexels", "https://api.pexels.com/search")
        with patch.dict(os.environ, {"PIXABAY_API_KEY": "test-key"}):
            seen = []
            client = ProviderClient(cache=SearchCache(), transport=lambda url, headers: seen.append((url, headers)) or {})
            client.get_json("pixabay", "https://pixabay.com/api/?key=test-key")
            self.assertEqual(seen[0][1], {"User-Agent": "reels-maker/1.0"})
            self.assertNotIn("test-key", repr(client.cache._entries))

    def test_cache_is_ttl_bounded_and_pixabay_ttl_is_at_least_24h(self):
        now = [10.0]
        cache = SearchCache(1, clock=lambda: now[0])
        calls = []
        client = ProviderClient(cache=cache, transport=lambda *_: calls.append(1) or {"results": []},
                                clock=lambda: now[0])
        with patch.dict(os.environ, {"PIXABAY_API_KEY": "abc"}):
            url = "https://pixabay.com/api/?key=abc&q=tree"
            client.get_json("pixabay", url)
            client.get_json("pixabay", url)
            self.assertEqual(len(calls), 1)
            self.assertGreaterEqual(next(iter(cache._entries.values())).expires_at - now[0], 86400)
        cache.put("second", {}, 10)
        self.assertEqual(len(cache._entries), 1)
        now[0] += 11
        self.assertIsNone(cache.get("second"))

    def test_persistent_pixabay_cache_survives_client_restart_and_is_private(self):
        now = [1000.0]
        with TemporaryDirectory() as directory, patch.dict(os.environ, {"PIXABAY_API_KEY": "secret-key"}):
            calls = []
            url = "https://pixabay.com/api/?key=secret-key&q=solar"
            first = ProviderClient(
                cache=SearchCache(directory=directory, clock=lambda: now[0]),
                transport=lambda *_: calls.append(1) or {"hits": [{"id": 1}]},
                clock=lambda: now[0],
            )
            self.assertEqual(first.get_json("pixabay", url), {"hits": [{"id": 1}]})
            second = ProviderClient(
                cache=SearchCache(directory=directory, clock=lambda: now[0]),
                transport=lambda *_: calls.append(2) or {"hits": []},
                clock=lambda: now[0],
            )
            self.assertEqual(second.get_json("pixabay", url), {"hits": [{"id": 1}]})
            self.assertEqual(calls, [1])
            paths = list(Path(directory).glob("*.json"))
            self.assertEqual(len(paths), 1)
            self.assertNotIn("secret-key", paths[0].name)
            self.assertNotIn("secret-key", paths[0].read_text())
            self.assertEqual(stat.S_IMODE(paths[0].stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(Path(directory).stat().st_mode), 0o700)
            now[0] += 86_401
            self.assertIsNone(SearchCache(directory=directory, clock=lambda: now[0]).get(
                hashlib.sha256(("pixabay\0" + url).encode()).hexdigest()))

    def test_oversized_pixabay_results_fail_closed_when_cache_cannot_store(self):
        key = "PIXABAY_API_KEY"
        cache = SearchCache(max_entry_bytes=64)
        client = ProviderClient(cache=cache, transport=lambda *_: {"hits": ["x" * 100]})
        with patch.dict(os.environ, {key: "test"}):
            with self.assertRaisesRegex(ProviderError, "24-hour caching"):
                client.get_json("pixabay", "https://pixabay.com/api/?key=test")

    def test_retry_backoff_then_success_and_429_exhaustion(self):
        sleeps = []
        sequence = deque([HTTPError("url", 503, "busy", {}, None), {"ok": True}])
        def transport(*_):
            result = sequence.popleft()
            if isinstance(result, Exception):
                raise result
            return result
        client = ProviderClient(cache=SearchCache(), transport=transport, sleep=sleeps.append,
                                max_retries=1, backoff_base=0.25)
        with patch.dict(os.environ, {"OPENVERSE_ACCESS_TOKEN": "mock-token"}):
            self.assertEqual(client.get_json("openverse", "https://api.openverse.org/a"), {"ok": True})
        self.assertEqual(sleeps, [0.25])

        exhausted = ProviderClient(cache=SearchCache(), transport=lambda *_: (_ for _ in ()).throw(
            HTTPError("url", 429, "limited", {}, None)), sleep=lambda _: None, max_retries=1)
        with patch.dict(os.environ, {"OPENVERSE_ACCESS_TOKEN": "mock-token"}):
            with self.assertRaises(RateLimitError):
                exhausted.get_json("openverse", "https://api.openverse.org/b")

    def test_long_retry_after_is_not_followed_automatically(self):
        headers = Message()
        headers["Retry-After"] = formatdate(time.time() + 120, usegmt=True)
        sleeps = []
        client = ProviderClient(
            cache=SearchCache(),
            transport=lambda *_: (_ for _ in ()).throw(
                HTTPError("url", 429, "limited", headers, None)),
            sleep=sleeps.append, max_retries=2, max_retry_delay=5)
        with patch.dict(os.environ, {"OPENVERSE_ACCESS_TOKEN":"mock-token"}):
            with self.assertRaisesRegex(RateLimitError, "above the automatic retry cap"):
                client.get_json("openverse", "https://api.openverse.org/rate-limited")
        self.assertEqual(sleeps, [])

    def test_pexels_reset_headers_pause_later_provider_calls(self):
        now = [10.0]
        client = ProviderClient(
            cache=SearchCache(),
            transport=lambda *_: ({"photos": []}, {
                "X-Ratelimit-Remaining": "0",
                "X-Ratelimit-Reset": str(time.time() + 60),
            }),
            clock=lambda: now[0],
        )
        with patch.dict(os.environ, {"PEXELS_API_KEY":"test"}):
            client.get_json("pexels", "https://api.pexels.com/v1/search?q=one")
            with self.assertRaisesRegex(RateLimitError, "provider rate limit active"):
                client.get_json("pexels", "https://api.pexels.com/v1/search?q=two")

    def test_local_window_quota_fails_closed_without_sleeping(self):
        now = [0.0]
        client = ProviderClient(cache=SearchCache(), transport=lambda *_: {}, clock=lambda: now[0])
        from reels_maker.assets.provider_client import POLICIES
        original = POLICIES["openverse"]
        POLICIES["openverse"] = type(original)(None, 1, 60)
        try:
            client.get_json("openverse", "https://api.openverse.org/one")
            with self.assertRaises(RateLimitError):
                client.get_json("openverse", "https://api.openverse.org/two")
        finally:
            POLICIES["openverse"] = original

    def test_openverse_anonymous_tier_and_optional_bearer_header(self):
        seen = []
        client = ProviderClient(cache=SearchCache(), transport=lambda url, headers: seen.append(headers) or {})
        with patch.dict(os.environ, {}, clear=True):
            client.get_json("openverse", "https://api.openverse.org/v1/images/?q=anon",
                            cache_response=False)
        self.assertNotIn("Authorization", seen[-1])
        with patch.dict(os.environ, {"OPENVERSE_ACCESS_TOKEN": "mock-token"}):
            client.get_json("openverse", "https://api.openverse.org/v1/images/?q=test")
        self.assertEqual(seen[-1], {"Authorization": "Bearer mock-token",
                                    "User-Agent": "reels-maker/1.0"})


if __name__ == "__main__":
    unittest.main()
