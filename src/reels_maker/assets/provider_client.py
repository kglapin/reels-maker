"""Credential-aware, quota-limited and retry-bounded JSON provider client."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import hashlib
import json
import os
import threading
import time
from email.utils import parsedate_to_datetime
from datetime import timezone
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .search_cache import SEARCH_CACHE, SearchCache


@dataclass(frozen=True)
class ProviderPolicy:
    credential: str | None
    limit: int
    window_seconds: int
    cache_ttl: int = 900
    credential_required: bool = True


POLICIES = {
    "pexels": ProviderPolicy("PEXELS_API_KEY", 200, 3600),
    "pixabay": ProviderPolicy("PIXABAY_API_KEY", 100, 60, 86400),
    "unsplash": ProviderPolicy("UNSPLASH_ACCESS_KEY", 50, 3600),
    "wikimedia_commons": ProviderPolicy(None, 60, 60),
    # Openverse serves an anonymous tier (server-advertised 20/min burst,
    # 200/day). An operator-provisioned OAuth bearer raises those limits
    # upstream, but is not required; local quotas stay at the anonymous level.
    "openverse": ProviderPolicy("OPENVERSE_ACCESS_TOKEN", 20, 60,
                                credential_required=False),
}
# Long-window request ceilings on top of the per-minute policy above.
LONG_WINDOW_LIMITS = {"pexels": (20000, 30 * 24 * 3600),
                      "openverse": (200, 86400)}
MONTHLY_LIMITS = LONG_WINDOW_LIMITS  # backwards-compatible alias


class ProviderError(RuntimeError):
    pass


class RateLimitError(ProviderError):
    pass


def _retry_after_seconds(value: str | None, fallback: float) -> float:
    if value is None:
        return fallback
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, retry_at.timestamp() - time.time())
        except (TypeError, ValueError, OverflowError):
            return fallback


class ProviderClient:
    def __init__(self, *, cache: SearchCache = SEARCH_CACHE,
                 transport: Callable | None = None, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep, max_retries: int = 2,
                 backoff_base: float = 0.5, max_retry_delay: float = 30.0):
        self.cache, self.transport, self.clock, self.sleep = cache, transport, clock, sleep
        self.max_retries, self.backoff_base = max_retries, backoff_base
        self.max_retry_delay = max_retry_delay
        self._calls = defaultdict(deque)
        self._monthly_calls = defaultdict(deque)
        self._blocked_until = defaultdict(float)
        self._quota_lock = threading.Lock()

    def _authorize(self, provider: str, headers: dict[str, str]) -> dict[str, str]:
        policy = POLICIES[provider]
        result = dict(headers)
        if policy.credential:
            key = os.environ.get(policy.credential, "").strip()
            if not key:
                if policy.credential_required:
                    raise ProviderError(f"{policy.credential} is required for {provider}")
            elif provider == "openverse":
                result.setdefault("Authorization", "Bearer " + key)
            # Credentials embedded in URL query strings (Pixabay's API contract) are
            # supplied by the adapter, not copied into logs or cache keys.
        return result

    def _quota(self, provider: str) -> None:
        policy = POLICIES[provider]
        with self._quota_lock:
            now = self.clock()
            if self._blocked_until[provider] > now:
                wait = self._blocked_until[provider] - now
                raise RateLimitError(f"{provider} provider rate limit active; retry in {wait:.1f}s")
            calls = self._calls[provider]
            while calls and calls[0] <= now - policy.window_seconds:
                calls.popleft()
            if len(calls) >= policy.limit:
                wait = max(0.0, calls[0] + policy.window_seconds - now)
                raise RateLimitError(f"{provider} local request quota exhausted; retry in {wait:.1f}s")
            if provider in LONG_WINDOW_LIMITS:
                limit, window = LONG_WINDOW_LIMITS[provider]
                monthly = self._monthly_calls[provider]
                while monthly and monthly[0] <= now - window:
                    monthly.popleft()
                if len(monthly) >= limit:
                    raise RateLimitError(f"{provider} local long-window request quota exhausted")
            calls.append(now)
            if provider in LONG_WINDOW_LIMITS:
                self._monthly_calls[provider].append(now)

    def get_json(self, provider: str, url: str, headers: dict[str, str] | None = None,
                 *, cache_response: bool = True, retries: int | None = None) -> dict:
        if provider not in POLICIES:
            raise ValueError(f"Unknown stock provider: {provider}")
        headers = self._authorize(provider, headers or {})
        # urllib's default "Python-urllib/x.y" signature is bot-banned by the
        # CDN layer of several providers (HTTP 403, Cloudflare code 1010).
        headers.setdefault("User-Agent", "reels-maker/1.0")
        cache_key = hashlib.sha256((provider + "\0" + url).encode()).hexdigest()
        if cache_response:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        policy = POLICIES[provider]
        retry_count = self.max_retries if retries is None else retries
        if retry_count < 0:
            raise ValueError("retries must not be negative")
        for attempt in range(retry_count + 1):
            self._quota(provider)
            response_headers = {}
            try:
                if self.transport:
                    payload = self.transport(url, headers)
                else:
                    request = Request(url, headers=headers)
                    with urlopen(request, timeout=12) as response:
                        payload = json.load(response)
                        response_headers = response.headers
                if isinstance(payload, tuple):  # optional mock transport response headers
                    payload, response_headers = payload
                # Respect an authoritative provider cooldown when present. Pexels
                # exposes Unix reset time only on successful JSON responses.
                if provider == "pexels" and response_headers:
                    remaining = response_headers.get("X-Ratelimit-Remaining")
                    if remaining is not None and int(remaining) <= 0:
                        reset = response_headers.get("X-Ratelimit-Reset")
                        cooldown = max(0.0, float(reset) - time.time()) if reset else policy.window_seconds
                        with self._quota_lock:
                            self._blocked_until[provider] = max(
                                self._blocked_until[provider], self.clock() + cooldown)
                stored = self.cache.put(cache_key, payload, policy.cache_ttl) if cache_response else True
                if provider == "pixabay" and not stored:
                    raise ProviderError(
                        "Pixabay response exceeds the safe cache limit; refusing uncached results because the API requires 24-hour caching")
                return payload
            except HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt >= retry_count:
                    if exc.code == 429:
                        raise RateLimitError(f"{provider} returned HTTP 429") from exc
                    raise ProviderError(f"{provider} returned HTTP {exc.code}") from exc
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                delay = _retry_after_seconds(retry_after, self.backoff_base * (2 ** attempt))
                if delay > self.max_retry_delay:
                    raise RateLimitError(
                        f"{provider} requested a {delay:.1f}s retry delay, above the automatic retry cap of "
                        f"{self.max_retry_delay:.1f}s; retry manually later") from exc
                self.sleep(delay)
            except (URLError, TimeoutError, ConnectionError) as exc:
                if attempt >= retry_count:
                    raise ProviderError(f"{provider} request failed after retries") from exc
                self.sleep(self.backoff_base * (2 ** attempt))
        raise ProviderError(f"{provider} request failed")


DEFAULT_CLIENT = ProviderClient()


def provider_json(provider: str, url: str, headers: dict[str, str] | None = None,
                  *, cache_response: bool = True, retries: int | None = None) -> dict:
    return DEFAULT_CLIENT.get_json(provider, url, headers,
                                   cache_response=cache_response, retries=retries)
