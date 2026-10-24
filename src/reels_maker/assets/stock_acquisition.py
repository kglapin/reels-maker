"""Rank stock-media candidates and safely acquire explicitly cleared assets.

Search metadata is never treated as rights clearance. Downloads are isolated in
brand imports quarantine and produce provenance; they do not approve media.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import urllib.error
import urllib.request
from typing import Callable, Iterable
from urllib.parse import urlsplit

from PIL import Image

from .stock_media import StockAsset, StockRendition


PROVIDER_HOSTS = {
    # Pexels' official video API returns MP4 renditions from Vimeo's external
    # media route in addition to its own image/video hosts.
    "pexels": frozenset({"images.pexels.com", "videos.pexels.com", "player.vimeo.com"}),
    "pixabay": frozenset({"cdn.pixabay.com", "pixabay.com"}),
    "unsplash": frozenset({"images.unsplash.com"}),
    "wikimedia_commons": frozenset({"upload.wikimedia.org"}),
    # Openverse indexes external works. Only commonly used, known media hosts
    # are supported; new hosts require an intentional code review.
    "openverse": frozenset({"upload.wikimedia.org", "images.unsplash.com",
                            "cdn.pixabay.com", "images.pexels.com"}),
}
MAX_DOWNLOAD_BYTES = 250 * 1024 * 1024
DOWNLOAD_TIMEOUT_SECONDS = 20
MAX_TRANSCODE_TIMEOUT_SECONDS = 180
MAX_VIDEO_DURATION_SECONDS = 120
MAX_IMAGE_PIXELS = 40_000_000
_SAFE_BRAND = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
SEARCH_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class DownloadResponse:
    final_url: str
    body: bytes | None
    content_type: str = ""


def candidate_record(asset: StockAsset) -> dict:
    """Serialize a provider result as an unapproved, portable candidate record."""
    return {
        "schema_version": SEARCH_SCHEMA_VERSION,
        "status": "candidate",
        "provider": asset.provider,
        "asset_id": asset.asset_id,
        "media_type": asset.media_type,
        "preview_url": asset.preview_url,
        "source_url": asset.source_url,
        "provider_url": asset.provider_url,
        "author": asset.author,
        "width": asset.width,
        "height": asset.height,
        "dimensions_verified": asset.width > 0 and asset.height > 0,
        "download_url": asset.download_url,
        "download_available": bool(asset.download_url),
        "local_download_supported": bool(asset.download_url)
            and asset.provider != "unsplash",
        "attribution_url": asset.attribution_url,
        "license": asset.license,
        "license_url": asset.license_url,
        "attribution": asset.attribution,
        "duration_seconds": asset.duration_seconds,
        "tracking_url": asset.tracking_url,
        "renditions": [
            {"url": item.url, "width": item.width, "height": item.height,
             "file_type": item.file_type, "quality": item.quality,
             "fps": item.fps, "size_bytes": item.size_bytes}
            for item in asset.renditions
        ],
        # Provider search can never grant clearance.
        "rights_status": "unknown",
    }


def candidate_asset(record: dict) -> StockAsset:
    """Load a candidate record without accepting embedded approval state."""
    required = ("provider", "asset_id", "media_type", "source_url",
                "download_url", "width", "height")
    if not isinstance(record, dict) or record.get("status") != "candidate" \
            or record.get("schema_version") != SEARCH_SCHEMA_VERSION:
        raise ValueError("Expected a schema-v1 media candidate record")
    if record.get("rights_status", "unknown") != "unknown":
        raise ValueError("Candidate records cannot embed rights clearance")
    if not all(isinstance(record.get(key), str) and record[key] for key in required[:5]) \
            or record.get("media_type") not in ("image", "video", "audio"):
        raise ValueError("Candidate is missing provider, id, type or source/download URLs")
    if any(type(record.get(key)) is not int or record[key] < 0
           for key in ("width", "height")):
        raise ValueError("Candidate dimensions must be non-negative integers; zero means unknown")
    renditions = record.get("renditions", [])
    if not isinstance(renditions, list):
        raise ValueError("Candidate renditions must be an array")
    parsed_renditions = []
    for item in renditions:
        if not isinstance(item, dict):
            raise ValueError("Candidate rendition must be an object")
        parsed_renditions.append(StockRendition(
            str(item.get("url", "")), int(item.get("width") or 0),
            int(item.get("height") or 0), str(item.get("file_type", "")),
            str(item.get("quality", "")), item.get("fps"), item.get("size_bytes"),
        ))
    return StockAsset(
        provider=record["provider"], asset_id=record["asset_id"],
        preview_url=str(record.get("preview_url", "")),
        source_url=record["source_url"], author=str(record.get("author", "Unknown")),
        width=record["width"], height=record["height"],
        download_url=record["download_url"],
        attribution_url=str(record.get("attribution_url", "")),
        media_type=record["media_type"], license=str(record.get("license", "")),
        license_url=str(record.get("license_url", "")),
        attribution=str(record.get("attribution", "")),
        tracking_url=str(record.get("tracking_url", "")),
        duration_seconds=record.get("duration_seconds"),
        renditions=tuple(parsed_renditions), rights_status="unknown",
        provider_url=str(record.get("provider_url", "")), rights_decision=None)


def rank_candidates(assets: Iterable[StockAsset], *, aspect: float,
                    min_width: int = 900, min_height: int = 900) -> list[StockAsset]:
    """Stable ranking independent of provider response/order, never rights-based."""
    if aspect <= 0 or min_width <= 0 or min_height <= 0:
        raise ValueError("aspect and minimum dimensions must be positive")
    import math

    def key(asset: StockAsset) -> tuple:
        ratio = asset.width / max(1, asset.height)
        crop = abs(math.log(ratio / aspect)) if ratio > 0 else 0.0
        resolution = (max(0, min_width - asset.width) / min_width
                      + max(0, min_height - asset.height) / min_height)
        return (crop + 2 * resolution, asset.provider, asset.asset_id,
                asset.width, asset.height, asset.download_url)
    return sorted(assets, key=key)


def search_with_fallback(query: str, providers: Iterable[Callable[[str], Iterable[StockAsset]]],
                         *, aspect: float, min_width: int = 900,
                         min_height: int = 900) -> tuple[list[StockAsset], list[dict]]:
    """Search each provider in order; a failed search does not suppress later providers."""
    found: list[StockAsset] = []
    outcomes: list[dict] = []
    for search in providers:
        name = getattr(search, "__name__", search.__class__.__name__)
        try:
            batch = list(search(query))
            found.extend(batch)
            outcomes.append({"provider": name, "status": "ok", "count": len(batch)})
        except Exception as exc:
            outcomes.append({"provider": name, "status": "failed",
                             "error": f"{type(exc).__name__}: {exc}"})
    return rank_candidates(found, aspect=aspect, min_width=min_width,
                           min_height=min_height), outcomes


def _validate_public_host(url: str, provider: str, *, resolve: Callable = socket.getaddrinfo,
                          approved_host: str | None = None) -> str:
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid download URL") from exc
    if (parsed.scheme != "https" or parsed.username or parsed.password or not host
            or port not in (None, 443) or parsed.fragment):
        raise ValueError("Download URL must be a credential-free HTTPS URL on port 443")
    allowlisted = PROVIDER_HOSTS.get(provider, frozenset())
    if host not in allowlisted and not (provider == "openverse" and approved_host == host):
        raise ValueError(f"Host is not allowlisted for provider {provider}")
    if provider == "pexels" and host == "player.vimeo.com" \
            and not (parsed.path or "").startswith("/external/"):
        raise ValueError("Only Pexels' documented Vimeo external-media path is allowed")
    try:
        records = resolve(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("Download host did not resolve safely") from exc
    if not records:
        raise ValueError("Download host did not resolve")
    for record in records:
        address = record[4][0].split("%", 1)[0]
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("Download host resolves to a private or non-public IP")
    return host


class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, provider: str, approved_host: str | None = None):
        super().__init__()
        self.provider = provider
        self.approved_host = approved_host

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_public_host(newurl, self.provider,
                              approved_host=self.approved_host)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _network_transport(url: str, *, provider: str, timeout: float,
                       max_bytes: int, destination: Path,
                       approved_host: str | None = None) -> DownloadResponse:
    opener = urllib.request.build_opener(_CheckedRedirect(provider, approved_host))
    request = urllib.request.Request(url, headers={"User-Agent": "reels-maker/1.0"})
    with opener.open(request, timeout=timeout) as response:
        final_url = response.geturl()
        _validate_public_host(final_url, provider, approved_host=approved_host)
        length = response.headers.get("Content-Length")
        if length and int(length) > max_bytes:
            raise ValueError("Provider media exceeds download byte limit")
        total = 0
        with destination.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("Provider media exceeds download byte limit")
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        return DownloadResponse(final_url, None, response.headers.get("Content-Type", ""))


def _ffprobe_metadata(path: Path, media_type: str,
                      probe: Callable[[Path, str], dict] | None) -> dict:
    if probe is not None:
        return probe(path, media_type)
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT_SECONDS)
    return json.loads(completed.stdout)


def _verify_file(path: Path, media_type: str,
                 probe: Callable[[Path, str], dict] | None) -> dict:
    if media_type == "image":
        with Image.open(path) as image:
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise ValueError(f"Image exceeds the {MAX_IMAGE_PIXELS}-pixel safety limit")
            image_format = image.format
            width, height = image.size
            image.verify()
        return {"format": image_format, "width": width, "height": height}
    if media_type not in ("video", "audio"):
        raise ValueError("Unsupported stock media type")
    metadata = _ffprobe_metadata(path, media_type, probe)
    streams = metadata.get("streams", [])
    if media_type == "audio":
        audio = next((stream for stream in streams
                      if stream.get("codec_type") == "audio"), None)
        if audio is None:
            raise ValueError("FFprobe did not verify a valid audio stream")
        raw_duration = metadata.get("format", {}).get("duration") or audio.get("duration")
        duration = float(raw_duration) if raw_duration not in (None, "N/A") else None
        sample_rate = audio.get("sample_rate")
        return {"format": metadata.get("format", {}).get("format_name", "unknown"),
                "codec": audio.get("codec_name", "unknown"),
                "duration_seconds": duration,
                "channels": audio.get("channels"),
                "sample_rate": int(sample_rate) if sample_rate else None}
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if not video or not int(video.get("width", 0)) or not int(video.get("height", 0)):
        raise ValueError("FFprobe did not verify a valid video stream")
    raw_duration = metadata.get("format", {}).get("duration") or video.get("duration")
    duration = float(raw_duration) if raw_duration not in (None, "N/A") else None
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    return {"format": metadata.get("format", {}).get("format_name", "unknown"),
            "width": int(video["width"]), "height": int(video["height"]),
            "codec": video.get("codec_name", "unknown"),
            "duration_seconds": duration,
            "fps": video.get("avg_frame_rate") or video.get("r_frame_rate"),
            "audio_streams": sum(stream.get("codec_type") == "audio" for stream in streams),
            "audio_codec": audio.get("codec_name") if audio else None}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _format_suffix(metadata: dict, media_type: str) -> str:
    if media_type == "image":
        suffix = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(metadata["format"])
        if suffix is None:
            raise ValueError("Image format is not in the supported safe-format set")
        return suffix
    formats = set(str(metadata.get("format", "")).lower().split(","))
    if media_type == "audio":
        for name, suffix in (("mp3", ".mp3"), ("wav", ".wav"), ("ogg", ".ogg"),
                             ("flac", ".flac"), ("m4a", ".m4a"), ("aac", ".aac"),
                             ("opus", ".opus"), ("webm", ".webm")):
            if name in formats:
                return suffix
        raise ValueError("Audio container is unsupported")
    if "mp4" in formats or "mov" in formats:
        return ".mp4"
    if "webm" in formats:
        return ".webm"
    if "matroska" in formats:
        return ".mkv"
    raise ValueError("Video container is unsupported; request explicit h264_mp4 transcode")


def _transcode_h264(source: Path, destination: Path, *, timeout: float) -> None:
    if not 0 < timeout <= MAX_TRANSCODE_TIMEOUT_SECONDS:
        raise ValueError("Transcode timeout may not exceed the safety limit")
    try:
        subprocess.run([
            "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(source),
            "-map", "0:v:0", "-map", "0:a?", "-map_metadata", "-1",
            "-vf", "scale=1920:1920:force_original_aspect_ratio=decrease:force_divisible_by=2",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-threads", "1", "-c:a", "aac",
            "-b:a", "128k", "-movflags", "+faststart", "-f", "mp4",
            str(destination),
        ], check=True, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise ValueError("FFmpeg is required for h264_mp4 transcode") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError("FFmpeg transcode exceeded the time limit") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError("FFmpeg could not transcode the verified source video") from exc


def download_cleared_asset(asset: StockAsset, *, brand: str, root: str | Path,
                           target_platform: str, transport: Callable | None = None,
                           probe: Callable[[Path, str], dict] | None = None,
                           resolve: Callable = socket.getaddrinfo,
                           max_bytes: int = MAX_DOWNLOAD_BYTES,
                           timeout: float = DOWNLOAD_TIMEOUT_SECONDS,
                           transcode_format: str | None = None,
                           transcode_timeout: float = MAX_TRANSCODE_TIMEOUT_SECONDS) -> dict:
    """Download one exactly-reviewed asset into imports quarantine atomically.

    No network activity occurs until the rights decision, provider, asset ID,
    and target platform have all been validated. No approval state is changed.
    """
    decision = asset.rights_decision
    if asset.provider == "unsplash":
        raise ValueError(
            "Unsplash results must use compliant API hotlinking; this local-media downloader does not implement that workflow")
    if not isinstance(target_platform, str) or not target_platform.strip():
        raise ValueError("A specific target platform is required")
    if (asset.rights_status != "cleared" or not isinstance(decision, dict)
            or decision.get("decision") != "cleared"
            or decision.get("provider") != asset.provider
            or str(decision.get("asset_id")) != asset.asset_id
            or decision.get("download_url") != asset.download_url
            or decision.get("source_url") != asset.source_url
            or target_platform not in decision.get("allowed_platforms", [])):
        raise ValueError("Download requires a rights decision bound to this exact source/URL/item and target platform")
    if not asset.download_url:
        raise ValueError("Asset has no download URL")
    if transcode_format not in (None, "h264_mp4"):
        raise ValueError("Supported transcode format is h264_mp4 or None")
    if transcode_format and asset.media_type != "video":
        raise ValueError("h264_mp4 transcode is available for video assets only")
    if not 0 < max_bytes <= MAX_DOWNLOAD_BYTES or not 0 < timeout <= DOWNLOAD_TIMEOUT_SECONDS:
        raise ValueError("Download byte and timeout bounds may not exceed the safety limits")
    if transcode_format and not 0 < transcode_timeout <= MAX_TRANSCODE_TIMEOUT_SECONDS:
        raise ValueError("Transcode timeout may not exceed the safety limit")
    approved_host = (urlsplit(asset.download_url).hostname
                     if asset.provider == "openverse" else None)
    _validate_public_host(asset.download_url, asset.provider, resolve=resolve,
                          approved_host=approved_host)

    base = Path(root).expanduser().resolve()
    if not _SAFE_BRAND.fullmatch(brand):
        raise ValueError("Invalid brand slug")
    brand_dir = base / "brands" / brand
    if brand_dir.is_symlink() or not brand_dir.is_dir() \
            or not brand_dir.resolve().is_relative_to(base):
        raise ValueError("Brand directory must exist and may not be a symlink")
    imports = brand_dir / "imports"
    if imports.is_symlink():
        raise ValueError("Brand imports directory may not be a symlink")
    imports.mkdir(mode=0o700, exist_ok=True)
    if imports.resolve() != (brand_dir / "imports").absolute():
        raise ValueError("Imports path escapes the selected brand")
    os.chmod(imports, 0o700)

    source_descriptor, source_temporary = tempfile.mkstemp(
        prefix=".stock-source-", suffix=".tmp", dir=imports)
    os.close(source_descriptor)
    source_path = Path(source_temporary)
    derivative_path: Path | None = None
    try:
        response = (transport(asset.download_url, provider=asset.provider, timeout=timeout,
                              max_bytes=max_bytes) if transport else
                    _network_transport(asset.download_url, provider=asset.provider,
                                       timeout=timeout, max_bytes=max_bytes,
                                       destination=source_path,
                                       approved_host=approved_host))
        _validate_public_host(response.final_url, asset.provider, resolve=resolve,
                              approved_host=approved_host)
        if response.body is not None:
            if not isinstance(response.body, bytes) or not response.body or len(response.body) > max_bytes:
                raise ValueError("Downloaded content is empty or exceeds the byte limit")
            with source_path.open("wb") as handle:
                handle.write(response.body)
                handle.flush()
                os.fsync(handle.fileno())
        source_bytes = source_path.stat().st_size
        if not source_bytes or source_bytes > max_bytes:
            raise ValueError("Downloaded content is empty or exceeds the byte limit")
        source_metadata = _verify_file(source_path, asset.media_type, probe)
        source_hash = _sha256(source_path)

        final_temporary = source_path
        final_metadata = source_metadata
        transform_recipe = "original"
        if transcode_format == "h264_mp4":
            duration = source_metadata.get("duration_seconds")
            if duration is None or not 0 < duration <= MAX_VIDEO_DURATION_SECONDS:
                raise ValueError(
                    f"h264_mp4 transcode requires verified duration 0–{MAX_VIDEO_DURATION_SECONDS}s")
            descriptor, temporary = tempfile.mkstemp(
                prefix=".stock-transcode-", suffix=".tmp.mp4", dir=imports)
            os.close(descriptor)
            derivative_path = Path(temporary)
            _transcode_h264(source_path, derivative_path, timeout=transcode_timeout)
            if derivative_path.stat().st_size > max_bytes:
                raise ValueError("Transcoded video exceeds the byte limit")
            final_metadata = _verify_file(derivative_path, "video", probe)
            result_duration = final_metadata.get("duration_seconds")
            if result_duration is None or abs(result_duration - duration) > 0.25:
                raise ValueError("Transcoded video duration differs from verified source")
            final_temporary = derivative_path
            transform_recipe = (
                "ffmpeg libx264 crf=23 yuv420p scale<=1920px preserve-aspect; "
                "optional AAC 128kbps, one thread"
            )

        final_hash = _sha256(final_temporary)
        suffix = ".mp4" if transcode_format == "h264_mp4" else _format_suffix(
            final_metadata, asset.media_type)
        final_path = imports / f"stock-{asset.provider}-{source_hash[:12]}-{final_hash[:12]}{suffix}"
        os.replace(final_temporary, final_path)
    except Exception:
        source_path.unlink(missing_ok=True)
        if derivative_path is not None:
            derivative_path.unlink(missing_ok=True)
        raise
    source_path.unlink(missing_ok=True)
    if derivative_path is not None:
        derivative_path.unlink(missing_ok=True)
    return {
        "status": "downloaded_to_quarantine", "approval": "not_approved",
        "path": str(final_path), "sha256": final_hash,
        "source_sha256": source_hash, "bytes": final_path.stat().st_size,
        "source_bytes": source_bytes,
        "provider": asset.provider, "asset_id": asset.asset_id,
        "requested_platform": target_platform, "source_url": asset.download_url,
        "provider_provenance": asset.provenance(),
        "final_url": response.final_url, "rights_decision": dict(decision),
        "transcode_format": transcode_format, "transform_recipe": transform_recipe,
        "derivative_paths": [final_path.relative_to(brand_dir).as_posix()],
        "source_verification": source_metadata, "verification": final_metadata,
    }
