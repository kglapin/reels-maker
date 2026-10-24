"""Deterministic procedural SFX prototypes staged as unreviewed quarantine.

The samples are generated from simple numeric oscillators/noise here; they do
not bundle external recordings. They are not automatically cleared for any
platform and are never written directly into ``media/``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import tempfile
import wave
from array import array

KINDS = ("click", "whoosh", "riser", "hit")
GENERATOR_VERSION = 1
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class SynthesisError(ValueError):
    """An invalid synthesis recipe or unsafe quarantine destination."""


@dataclass(frozen=True)
class SFXSpec:
    kind: str
    duration_seconds: float = 0.45
    sample_rate: int = 48_000
    seed: int = 0
    peak: float = 0.20


def _validated(spec: SFXSpec) -> tuple[int, int]:
    if not isinstance(spec, SFXSpec):
        raise SynthesisError("spec must be an SFXSpec")
    if spec.kind not in KINDS:
        raise SynthesisError(f"kind must be one of {KINDS}")
    if isinstance(spec.duration_seconds, bool) or not isinstance(spec.duration_seconds, (int, float)) \
            or not math.isfinite(spec.duration_seconds) or not 0.03 <= spec.duration_seconds <= 3.0:
        raise SynthesisError("duration_seconds must be finite and between 0.03 and 3.0")
    if type(spec.sample_rate) is not int or spec.sample_rate not in (22_050, 44_100, 48_000):
        raise SynthesisError("sample_rate must be 22050, 44100, or 48000")
    if type(spec.seed) is not int or not 0 <= spec.seed < 2**31:
        raise SynthesisError("seed must be a non-negative integer below 2^31")
    if isinstance(spec.peak, bool) or not isinstance(spec.peak, (int, float)) \
            or not math.isfinite(spec.peak) or not 0.01 <= spec.peak <= 0.50:
        raise SynthesisError("peak must be finite and between 0.01 and 0.50 linear amplitude")
    return spec.sample_rate, max(1, round(spec.duration_seconds * spec.sample_rate))


def synthesize_sfx(spec: SFXSpec) -> tuple[bytes, dict]:
    """Generate a repeatable stereo PCM-16 WAV and a machine provenance report."""
    sample_rate, count = _validated(spec)
    rng = random.Random(spec.seed)
    frames = array("h")
    phase = 0.0
    filtered_noise = 0.0
    peak = 0.0
    samples: list[float] = []

    for index in range(count):
        progress = index / max(1, count - 1)
        elapsed = index / sample_rate
        noise = rng.random() * 2.0 - 1.0
        filtered_noise += 0.12 * (noise - filtered_noise)
        if spec.kind == "click":
            frequency = 2100.0 - 500.0 * progress
            phase += 2.0 * math.pi * frequency / sample_rate
            envelope = math.exp(-34.0 * progress)
            value = envelope * (0.78 * math.sin(phase) + 0.22 * noise)
        elif spec.kind == "whoosh":
            frequency = 180.0 + 720.0 * progress
            phase += 2.0 * math.pi * frequency / sample_rate
            envelope = math.sin(math.pi * progress) ** 1.4
            value = envelope * (0.82 * filtered_noise + 0.18 * math.sin(phase))
        elif spec.kind == "riser":
            frequency = 110.0 * (12.0 ** progress)
            phase += 2.0 * math.pi * frequency / sample_rate
            envelope = min(1.0, progress * 1.5) * min(1.0, (1.0 - progress) * 10.0)
            value = envelope * (0.9 * math.sin(phase) + 0.1 * filtered_noise)
        else:  # short, damped low-frequency hit with a brief noise transient
            frequency = 105.0 - 55.0 * progress
            phase += 2.0 * math.pi * frequency / sample_rate
            envelope = math.exp(-10.0 * progress)
            value = envelope * (0.85 * math.sin(phase) + 0.15 * noise * math.exp(-55.0 * progress))
        samples.append(value)
        peak = max(peak, abs(value))

    if peak <= 0:
        raise SynthesisError("generated waveform unexpectedly contains no signal")
    gain = spec.peak / peak
    for value in samples:
        sample = max(-32768, min(32767, round(value * gain * 32767)))
        frames.extend((sample, sample))
    if frames.itemsize != 2:
        raise SynthesisError("platform does not provide 16-bit sample storage")
    if os.sys.byteorder != "little":
        frames.byteswap()
    import io
    target = io.BytesIO()
    with wave.open(target, "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(frames.tobytes())
    content = target.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    report = {
        "schema_version": 1,
        "provider": "reels-maker-procedural",
        "asset_id": f"sfx-{digest[:20]}",
        "media_type": "audio",
        "kind": spec.kind,
        "file_format": "WAV PCM-16 stereo",
        "sample_rate": sample_rate,
        "channels": 2,
        "duration_seconds": count / sample_rate,
        "peak_dbfs": round(20 * math.log10(spec.peak), 2),
        "sha256": digest,
        "generator_version": GENERATOR_VERSION,
        "recipe": asdict(spec),
        "rights_status": "unknown",
        "editorial_state": "quarantine",
        "license": "unknown pending human rights review",
        "source": "deterministic in-repository procedural synthesis",
        "note": "Not approved for publishing or mixing until human review and a library record.",
    }
    return content, report


def write_procedural_sfx(spec: SFXSpec, *, brand: str, root: str | Path) -> dict:
    """Write generated WAV and provenance only to a brand's ignored imports/audio."""
    _validated(spec)
    if not isinstance(brand, str) or not _SLUG.fullmatch(brand):
        raise SynthesisError("brand must be a lowercase slug")
    base = Path(root).expanduser().resolve()
    brand_dir = base / "brands" / brand
    if brand_dir.is_symlink() or not brand_dir.is_dir() or not brand_dir.resolve().is_relative_to(base):
        raise SynthesisError("brand directory must exist inside the selected repository root")
    imports = brand_dir / "imports"
    if imports.is_symlink():
        raise SynthesisError("brand imports directory may not be a symlink")
    audio = imports / "audio"
    if audio.is_symlink():
        raise SynthesisError("brand imports/audio directory may not be a symlink")
    audio.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not audio.resolve().is_relative_to(brand_dir.resolve()):
        raise SynthesisError("audio quarantine escapes brand directory")
    os.chmod(audio, 0o700)

    content, report = synthesize_sfx(spec)
    filename = f"procedural_{spec.kind}_{report['sha256'][:20]}.wav"
    destination = audio / filename
    descriptor, temporary = tempfile.mkstemp(prefix=".sfx-", suffix=".tmp", dir=audio)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        if destination.exists() and destination.read_bytes() != content:
            raise SynthesisError("content-addressed output collision; previous file preserved")
        os.replace(temporary, destination)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
    report["file"] = str(destination)
    report["brand"] = brand
    report["quarantine_directory"] = "imports/audio"
    sidecar = destination.with_suffix(".wav.json")
    descriptor, temporary = tempfile.mkstemp(prefix=".sfx-report-", suffix=".tmp", dir=audio)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, sidecar)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
    report["provenance_report"] = str(sidecar)
    return report
