"""ElevenLabs text-to-speech client writing into brand imports quarantine.

The module wraps the ElevenLabs REST API with the standard library only.
Authentication uses the ``ELEVENLABS_API_KEY`` environment variable (the CLI
also loads the repository-root ``.env`` before dispatch). Generated audio is
never written into approved ``media/`` directories: like procedural SFX, it
lands in ``brands/<slug>/imports/audio/`` with a provenance sidecar and stays
unreviewed until a human clears it.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile
import urllib.error
import urllib.request
import wave

API_KEY_ENV = "ELEVENLABS_API_KEY"
DEFAULT_BASE_URL = "https://api.elevenlabs.io"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
MAX_TEXT_CHARS = 5000
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_VOICE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_MODEL_ID = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_OUTPUT_FORMAT = re.compile(
    r"^(mp3|pcm|ulaw|alaw)_(8000|16000|22050|24000|44100|48000)"
    r"(_(8|16|24|32|44_1|48|64|96|128|192))?$")
_EXTENSIONS = {"mp3": "mp3", "pcm": "wav", "ulaw": "ulaw", "alaw": "alaw"}
_PCM_RATES = {"8000", "16000", "22050", "24000", "44100", "48000"}


class TtsError(ValueError):
    """Invalid request parameters, API failure or unsafe quarantine path."""


def _api_key(api_key: str | None) -> str:
    key = api_key or os.getenv(API_KEY_ENV)
    if not key or not key.strip():
        raise TtsError(f"{API_KEY_ENV} is not set; add it to .env or the environment")
    return key.strip()


def _base_url(base_url: str | None) -> str:
    url = (base_url or os.getenv("ELEVENLABS_BASE_URL")
           or DEFAULT_BASE_URL).rstrip("/")
    if not url.startswith("https://"):
        raise TtsError("ElevenLabs base URL must use https")
    return url


def _request(method: str, url: str, *, api_key: str, payload: bytes | None = None,
             timeout: float = 120.0) -> tuple[int, bytes, str]:
    headers = {"xi-api-key": api_key}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=payload, headers=headers,
                                     method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), \
                response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:500].decode("utf-8", "replace")
        raise TtsError(f"ElevenLabs API error {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TtsError(f"ElevenLabs request failed: {exc}") from exc


def _validate_text(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise TtsError("text must be a nonempty string")
    text = text.strip()
    if len(text) > MAX_TEXT_CHARS:
        raise TtsError(f"text exceeds {MAX_TEXT_CHARS} characters per request")
    return text


def _validate_voice(voice_id: str) -> str:
    if not isinstance(voice_id, str) or not _VOICE_ID.fullmatch(voice_id):
        raise TtsError("voice must be a valid ElevenLabs voice ID")
    return voice_id


def _validate_model(model_id: str) -> str:
    if not isinstance(model_id, str) or not _MODEL_ID.fullmatch(model_id):
        raise TtsError("model must be a valid ElevenLabs model ID")
    return model_id


def _validate_format(output_format: str) -> str:
    if not isinstance(output_format, str) or \
            not _OUTPUT_FORMAT.fullmatch(output_format):
        raise TtsError(f"unsupported output format: {output_format!r}")
    return output_format


def list_voices(*, api_key: str | None = None,
                base_url: str | None = None,
                query: str | None = None) -> list[dict]:
    """Return workspace voices, optionally filtered by name substring."""
    key = _api_key(api_key)
    _, body, _ = _request("GET", f"{_base_url(base_url)}/v1/voices",
                          api_key=key, timeout=30)
    try:
        voices = json.loads(body.decode("utf-8")).get("voices", [])
    except (json.JSONDecodeError, AttributeError) as exc:
        raise TtsError("ElevenLabs voices response was not valid JSON") from exc
    needle = (query or "").strip().lower()
    result = []
    for voice in voices:
        if not isinstance(voice, dict):
            continue
        name = str(voice.get("name", ""))
        if needle and needle not in name.lower():
            continue
        result.append({
            "voice_id": voice.get("voice_id"),
            "name": name,
            "category": voice.get("category"),
            "labels": voice.get("labels") or {},
            "preview_url": voice.get("preview_url"),
        })
    return result


def synthesize_speech(text: str, *, voice_id: str,
                      model_id: str = DEFAULT_MODEL_ID,
                      output_format: str = DEFAULT_OUTPUT_FORMAT,
                      with_timestamps: bool = False,
                      api_key: str | None = None,
                      base_url: str | None = None,
                      timeout: float = 120.0) -> tuple[bytes, dict | None]:
    """Synthesize *text* and return ``(audio_bytes, alignment_or_None)``.

    ``with_timestamps`` uses the ``/with-timestamps`` endpoint, which returns
    the audio base64-encoded next to character-level alignment. The alignment
    is the raw provider payload; use :func:`word_timings` to derive word
    onsets for ``voiceover.sync_marks`` review.
    """
    text = _validate_text(text)
    voice_id = _validate_voice(voice_id)
    model_id = _validate_model(model_id)
    output_format = _validate_format(output_format)
    key = _api_key(api_key)
    base = _base_url(base_url)

    body = json.dumps({
        "text": text,
        "model_id": model_id,
    }).encode("utf-8")
    suffix = "/with-timestamps" if with_timestamps else ""
    url = f"{base}/v1/text-to-speech/{voice_id}{suffix}" \
        f"?output_format={output_format}"

    _, payload, _ = _request("POST", url, api_key=key, payload=body,
                             timeout=timeout)
    if not with_timestamps:
        return payload, None
    try:
        document = json.loads(payload.decode("utf-8"))
        audio = base64.b64decode(document["audio_base64"])
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        raise TtsError("ElevenLabs timestamps response was malformed") from exc
    alignment = document.get("alignment") or document.get("normalized_alignment")
    return audio, alignment if isinstance(alignment, dict) else None


def word_timings(alignment: dict | None) -> list[dict]:
    """Derive ``[{word, start_seconds, end_seconds}]`` from char alignment."""
    if not isinstance(alignment, dict):
        return []
    characters = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    count = min(len(characters), len(starts), len(ends))
    words: list[dict] = []
    buffer: list[str] = []
    start = end = None
    for index in range(count):
        char, char_start, char_end = (characters[index], starts[index], ends[index])
        if isinstance(char_start, bool) or not isinstance(char_start, (int, float)) \
                or not math.isfinite(char_start):
            continue
        if char.isspace():
            if buffer:
                words.append({"word": "".join(buffer),
                              "start_seconds": round(start, 4),
                              "end_seconds": round(end, 4)})
                buffer, start, end = [], None, None
            continue
        if start is None:
            start = char_start
        buffer.append(char)
        end = char_end if isinstance(char_end, (int, float)) \
            and math.isfinite(char_end) else char_start
    if buffer:
        words.append({"word": "".join(buffer),
                      "start_seconds": round(start, 4),
                      "end_seconds": round(end, 4)})
    return words


def brand_tts_defaults(brand: str, root: str | Path) -> dict:
    """Read ``voiceover.elevenlabs`` defaults from ``brands/<slug>/brand.json``.

    Returns ``{}`` when the brand declares no ElevenLabs voice; malformed
    sections raise :class:`TtsError` so typos never silently fall back.
    """
    if not isinstance(brand, str) or not _SLUG.fullmatch(brand):
        raise TtsError("brand must be a lowercase slug")
    base = Path(root).expanduser().resolve()
    config_path = base / "brands" / brand / "brand.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise TtsError(f"Cannot load brand configuration {config_path}: {exc}") from exc
    section = config.get("voiceover") if isinstance(config, dict) else None
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise TtsError("brand.json voiceover must be an object")
    elevenlabs = section.get("elevenlabs")
    if elevenlabs is None:
        return {}
    if not isinstance(elevenlabs, dict):
        raise TtsError("brand.json voiceover.elevenlabs must be an object")
    defaults = {}
    if "voice_id" in elevenlabs:
        defaults["voice_id"] = _validate_voice(elevenlabs["voice_id"])
    if "model_id" in elevenlabs:
        defaults["model_id"] = _validate_model(elevenlabs["model_id"])
    if "output_format" in elevenlabs:
        defaults["output_format"] = _validate_format(elevenlabs["output_format"])
    return defaults


def _quarantine_dir(brand: str, root: str | Path) -> Path:
    if not isinstance(brand, str) or not _SLUG.fullmatch(brand):
        raise TtsError("brand must be a lowercase slug")
    base = Path(root).expanduser().resolve()
    brand_dir = base / "brands" / brand
    if brand_dir.is_symlink() or not brand_dir.is_dir() \
            or not brand_dir.resolve().is_relative_to(base):
        raise TtsError("brand directory must exist inside the selected repository root")
    imports = brand_dir / "imports"
    if imports.is_symlink():
        raise TtsError("brand imports directory may not be a symlink")
    audio = imports / "audio"
    if audio.is_symlink():
        raise TtsError("brand imports/audio directory may not be a symlink")
    audio.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not audio.resolve().is_relative_to(brand_dir.resolve()):
        raise TtsError("audio quarantine escapes brand directory")
    os.chmod(audio, 0o700)
    return audio


def _atomic_write(directory: Path, filename: str, content: bytes | str) -> Path:
    destination = directory / filename
    mode = "wb" if isinstance(content, bytes) else "w"
    kwargs = {} if isinstance(content, bytes) else {"encoding": "utf-8"}
    descriptor, temporary = tempfile.mkstemp(prefix=".tts-", dir=directory)
    try:
        with os.fdopen(descriptor, mode, **kwargs) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        if destination.exists():
            existing = destination.read_bytes() if isinstance(content, bytes) \
                else destination.read_text(encoding="utf-8")
            if existing != content:
                raise TtsError("content-addressed output collision; previous file preserved")
        os.replace(temporary, destination)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
    return destination


def _wrap_pcm_wav(pcm: bytes, output_format: str) -> bytes:
    """Wrap raw signed-16-bit mono PCM from the API into a WAV container."""
    parts = output_format.split("_")
    rate = int(parts[1])
    if parts[0] != "pcm" or str(rate) not in _PCM_RATES or len(pcm) % 2:
        raise TtsError("cannot wrap unexpected PCM payload into WAV")
    target = io.BytesIO()
    with wave.open(target, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)
    return target.getvalue()


def generate_voiceover(text: str, *, voice_id: str, brand: str,
                       root: str | Path,
                       model_id: str = DEFAULT_MODEL_ID,
                       output_format: str = DEFAULT_OUTPUT_FORMAT,
                       with_timestamps: bool = False,
                       api_key: str | None = None,
                       base_url: str | None = None,
                       timeout: float = 120.0) -> dict:
    """Synthesize and quarantine a voiceover with a provenance sidecar."""
    text = _validate_text(text)
    voice_id = _validate_voice(voice_id)
    model_id = _validate_model(model_id)
    output_format = _validate_format(output_format)
    directory = _quarantine_dir(brand, root)

    audio, alignment = synthesize_speech(
        text, voice_id=voice_id, model_id=model_id,
        output_format=output_format, with_timestamps=with_timestamps,
        api_key=api_key, base_url=base_url, timeout=timeout)
    if not audio:
        raise TtsError("ElevenLabs returned empty audio")
    if output_format.startswith("pcm_"):
        audio = _wrap_pcm_wav(audio, output_format)

    digest = hashlib.sha256(audio).hexdigest()
    extension = _EXTENSIONS[output_format.split("_", 1)[0]]
    filename = f"elevenlabs_{digest[:20]}.{extension}"
    destination = _atomic_write(directory, filename, audio)

    report = {
        "schema_version": 1,
        "provider": "elevenlabs",
        "asset_id": f"tts-{digest[:20]}",
        "media_type": "audio",
        "file_format": output_format,
        "voice_id": voice_id,
        "model_id": model_id,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text_characters": len(text),
        "sha256": digest,
        "rights_status": "unknown",
        "editorial_state": "quarantine",
        "license": "ElevenLabs generated speech; usage terms apply",
        "source": "ElevenLabs text-to-speech API",
        "note": "Not approved for publishing until human review and a library record.",
    }
    sidecar = _atomic_write(
        directory, f"{filename}.json",
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    report["file"] = str(destination)
    report["brand"] = brand
    report["quarantine_directory"] = "imports/audio"
    report["provenance_report"] = str(sidecar)

    if alignment is not None:
        timing = {
            "schema_version": 1,
            "provider": "elevenlabs",
            "audio_sha256": digest,
            "voice_id": voice_id,
            "model_id": model_id,
            "alignment": alignment,
            "words": word_timings(alignment),
            "note": "Provider-reported timings; verify spoken onsets on the actual "
                    "recording before writing voiceover.sync_marks.",
        }
        timing_path = _atomic_write(
            directory, f"{filename}.alignment.json",
            json.dumps(timing, ensure_ascii=False, indent=2) + "\n")
        report["alignment_report"] = str(timing_path)
        report["word_count"] = len(timing["words"])
    return report
