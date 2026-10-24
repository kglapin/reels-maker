"""Openverse audio search metadata; results are candidates, not cleared media.

This adapter only searches and returns source evidence. It never downloads audio
or treats Openverse's reported license as cross-platform rights clearance.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re
from typing import Any
from urllib.parse import urlencode

from .provider_client import DEFAULT_CLIENT, ProviderClient


def _plain_text(value: object) -> str:
    text = unescape(re.sub(r"<[^>]*>", " ", str(value or "")))
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True)
class OpenverseAudioResult:
    """Metadata for one Openverse audio result. No local media path is created."""

    provider: str
    asset_id: str
    title: str
    creator: str
    source_url: str
    audio_url: str
    license: str
    license_url: str
    attribution: str
    duration_seconds: float | None
    file_type: str
    checksum: str
    rights_status: str = "unknown"

    def provenance(self) -> dict[str, Any]:
        """Return source evidence without interpreting it as a rights decision."""
        return {
            "provider": self.provider,
            "asset_id": self.asset_id,
            "provider_url": "https://openverse.org",
            "title": self.title,
            "creator": self.creator,
            "source_url": self.source_url,
            "audio_url": self.audio_url,
            "license": self.license,
            "license_url": self.license_url,
            "attribution": self.attribution,
            "duration_seconds": self.duration_seconds,
            "file_type": self.file_type,
            "checksum": self.checksum,
            "rights_status": self.rights_status,
        }


def search_openverse_audio(query: str, *, per_page: int = 12,
                           client: ProviderClient | None = None
                           ) -> list[OpenverseAudioResult]:
    """Search official Openverse audio API using the shared OAuth-aware client.

    ``OPENVERSE_ACCESS_TOKEN`` must contain an operator-provisioned OAuth bearer
    token. The shared ProviderClient enforces this requirement and caches only
    search metadata. A license reported by Openverse is evidence for human review,
    not confirmation of reuse rights on any platform.
    """
    if not 1 <= per_page <= 20:
        raise ValueError("per_page must be 1..20")
    url = "https://api.openverse.org/v1/audio/?" + urlencode({
        "q": query, "page_size": per_page,
    })
    payload = (client or DEFAULT_CLIENT).get_json(
        "openverse", url,
        {"User-Agent": "reels-maker/1.0 (audio candidate search)"},
    )
    results = []
    for item in payload.get("results", []):
        duration = item.get("duration")
        try:
            duration = float(duration) if duration is not None else None
        except (TypeError, ValueError):
            duration = None
        results.append(OpenverseAudioResult(
            provider="openverse",
            asset_id=str(item.get("id", "")),
            title=_plain_text(item.get("title") or ""),
            creator=_plain_text(item.get("creator") or "Unknown"),
            source_url=str(item.get("foreign_landing_url") or ""),
            audio_url=str(item.get("url") or ""),
            license=str(item.get("license") or ""),
            license_url=str(item.get("license_url") or ""),
            attribution=_plain_text(item.get("attribution") or ""),
            duration_seconds=duration,
            file_type=str(item.get("filetype") or item.get("file_type") or ""),
            checksum=str(item.get("sha256") or item.get("checksum") or ""),
        ))
    return results
