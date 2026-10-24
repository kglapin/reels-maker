"""Bounded TTL cache for provider search metadata, never media files."""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
import json
import hashlib
import os
from pathlib import Path
import tempfile
import time
from typing import Callable

@dataclass
class _Entry:
    expires_at: float
    value: dict


class SearchCache:
    """Small LRU/TTL metadata cache with optional private, persistent storage."""

    def __init__(self, max_entries: int = 256, *,
                 directory: str | Path | None = None,
                 max_entry_bytes: int = 4 * 1024 * 1024,
                 clock: Callable[[], float] = time.time):
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        if max_entry_bytes < 1:
            raise ValueError("max_entry_bytes must be positive")
        self.max_entries = max_entries
        self.max_entry_bytes = max_entry_bytes
        self.directory = Path(directory).expanduser() if directory is not None else None
        self._clock = clock
        self._entries: OrderedDict[str, _Entry] = OrderedDict()

    def _path(self, key: str) -> Path:
        if not isinstance(key, str):
            raise ValueError("cache key must be a string")
        if self.directory is None:
            raise ValueError("persistent cache directory is not configured")
        return self.directory / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"

    def _delete_file(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    def get(self, key: str) -> dict | None:
        entry = self._entries.get(key)
        if entry is not None:
            if entry.expires_at <= self._clock():
                del self._entries[key]
                if self.directory is not None:
                    self._delete_file(self._path(key))
                return None
            self._entries.move_to_end(key)
            return deepcopy(entry.value)
        if self.directory is None:
            return None
        path = self._path(key)
        if path.is_symlink() or not path.is_file():
            return None
        try:
            if path.stat().st_size > self.max_entry_bytes:
                self._delete_file(path)
                return None
            record = json.loads(path.read_text(encoding="utf-8"))
            expiry = float(record["expires_at"])
            value = record["value"]
            if not isinstance(value, dict):
                raise ValueError("cached metadata is not an object")
            if expiry <= self._clock():
                self._delete_file(path)
                return None
            self._entries[key] = _Entry(expiry, value)
            self._entries.move_to_end(key)
            os.utime(path, None)
            return deepcopy(value)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            self._delete_file(path)
            return None

    def put(self, key: str, value: dict, ttl_seconds: float) -> bool:
        if not isinstance(key, str):
            raise ValueError("cache key must be a string")
        if ttl_seconds <= 0:
            raise ValueError("cache TTL must be positive")
        if not isinstance(value, dict):
            raise ValueError("only JSON metadata objects can be cached")
        expires_at = self._clock() + ttl_seconds
        try:
            payload = json.dumps({"expires_at": expires_at, "value": value},
                                 ensure_ascii=False, separators=(",", ":"),
                                 allow_nan=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"provider response is not cacheable JSON: {exc}") from exc
        if len(payload) > self.max_entry_bytes:
            return False
        self._entries[key] = _Entry(expires_at, deepcopy(value))
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)
        if self.directory is None:
            return True

        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.directory.is_symlink():
            raise OSError("provider metadata cache directory must not be a symlink")
        os.chmod(self.directory, 0o700)
        target = self._path(key)
        descriptor, temporary = tempfile.mkstemp(prefix=".search-", suffix=".tmp",
                                                  dir=self.directory)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, target)
            os.chmod(target, 0o600)
        except OSError:
            try:
                os.close(descriptor)
            except OSError:
                pass
            Path(temporary).unlink(missing_ok=True)
            return False

        files = sorted((item for item in self.directory.glob("*.json")
                        if item.is_file() and not item.is_symlink()),
                       key=lambda item: item.stat().st_mtime)
        for item in files[:-self.max_entries]:
            self._delete_file(item)
        return True


SEARCH_CACHE = SearchCache(directory=Path.home() / ".cache" / "reels-maker" / "provider-search")
