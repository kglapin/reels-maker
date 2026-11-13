"""Original brand percussion bed: deterministic 110 s kit synthesis, no samples.

Every hit is synthesized from sine/noise primitives with a seeded RNG, so the
bed is an original work with no third-party rights attached. The arrangement
follows the film's 13-beat educational arc (sparse intro -> drive -> resolve).
"""
from __future__ import annotations

import hashlib
import io
import math
import wave
from array import array
from dataclasses import dataclass

import numpy as np

GENERATOR_VERSION = 1
SAMPLE_RATE = 48_000
DURATION = 110.0
SEED = 7


def _kick(sr, rng, vel=1.0):
    n = int(0.28 * sr)
    t = np.arange(n) / sr
    freq = 45 + 75 * np.exp(-28 * t)
    phase = np.cumsum(freq) / sr
    env = np.exp(-9 * t)
    click = rng.standard_normal(n) * np.exp(-220 * t) * 0.25
    return vel * (np.sin(2 * np.pi * phase) * env + click)


def _hat(sr, rng, open_=False, vel=1.0):
    dur = 0.30 if open_ else 0.05
    n = int(dur * sr)
    noise = rng.standard_normal(n)
    hp = np.diff(noise, prepend=noise[0])
    env = np.exp(-(90 if not open_ else 9) * np.arange(n) / sr)
    return vel * hp * env * 0.5


def _shaker(sr, rng, vel=1.0):
    n = int(0.09 * sr)
    t = np.arange(n) / sr
    noise = rng.standard_normal(n)
    bp = noise - np.concatenate(([0], noise[:-1]))
    return vel * bp * np.sin(np.pi * t / 0.09) ** 2 * 0.35


def _clap(sr, rng, vel=1.0):
    n = int(0.22 * sr)
    out = np.zeros(n)
    for k in range(3):
        start = int(k * 0.018 * sr)
        m = min(n - start, int(0.16 * sr))
        burst = rng.standard_normal(m) * np.exp(-22 * np.arange(m) / sr)
        out[start:start + m] += burst
    return vel * out * 0.5


def _bass(sr, vel=1.0):
    n = int(0.24 * sr)
    t = np.arange(n) / sr
    return vel * np.sin(2 * np.pi * 49 * t) * np.exp(-7 * t) * 0.8


def _tom(sr, vel=1.0, f0=180.0):
    n = int(0.32 * sr)
    t = np.arange(n) / sr
    freq = 90 + (f0 - 90) * np.exp(-12 * t)
    phase = np.cumsum(freq) / sr
    return vel * np.sin(2 * np.pi * phase) * np.exp(-8 * t) * 0.7


@dataclass(frozen=True)
class BedSpec:
    duration_seconds: float = DURATION
    sample_rate: int = SAMPLE_RATE
    seed: int = SEED
    peak: float = 0.89


def _section(u):
    if u < 15:
        return "intro"
    if u < 39:
        return "build"
    if u < 59:
        return "drive"
    if u < 66:
        return "lift"
    if u < 90:
        return "groove"
    if u < 100:
        return "tension"
    return "resolve"


def synthesize_percussion_bed(spec: BedSpec | None = None):
    """Render the full bed; returns (wav_bytes, provenance_report)."""
    spec = spec or BedSpec()
    sr = spec.sample_rate
    if sr != SAMPLE_RATE:
        raise ValueError("bed is mastered at 48000 Hz")
    total = int(spec.duration_seconds * sr)
    left = np.zeros(total, dtype=np.float64)
    right = np.zeros(total, dtype=np.float64)
    rng = np.random.default_rng(spec.seed)

    beat = 60.0 / 96.0
    beats = int(spec.duration_seconds / beat) + 2

    def add(buf_l, buf_r, pos, sig, pan=0.0):
        start = int(pos * sr)
        if start >= total:
            return
        end = min(total, start + len(sig))
        if end <= start:
            return
        seg = sig[: end - start]
        gl = math.cos((pan + 1) * math.pi / 4)
        gr = math.sin((pan + 1) * math.pi / 4)
        buf_l[start:end] += seg * gl
        buf_r[start:end] += seg * gr

    for b in range(beats):
        u = b * beat
        if u >= spec.duration_seconds:
            break
        sec = _section(u)
        bar = (b // 4) % 2
        vel = {"intro": 0.55, "build": 0.7, "drive": 0.9, "lift": 0.75,
               "groove": 1.0, "tension": 0.85, "resolve": 0.5}[sec]
        # Kick: four-floor, half-time in lift, sparse in resolve.
        if sec in ("intro", "build", "drive", "groove", "tension"):
            if b % 4 in (0, 2) or (sec in ("drive", "groove") and b % 4 == 3 and bar == 1):
                add(left, right, u, _kick(sr, rng, vel))
        elif sec == "lift" and b % 8 in (0, 5):
            add(left, right, u, _kick(sr, rng, vel))
        elif sec == "resolve" and b % 8 == 0:
            add(left, right, u, _kick(sr, rng, vel * 0.8))
        # Hats: 8ths, open on offbeats from build on.
        if b % 2 == 0:
            add(left, right, u, _hat(sr, rng, vel=vel * 0.7), pan=0.25)
        elif sec not in ("intro",):
            add(left, right, u, _hat(sr, rng, open_=True, vel=vel * 0.5), pan=0.25)
        # Shaker 16ths from build (quieter in resolve).
        if sec in ("build", "drive", "groove", "tension") or (sec == "resolve" and b % 2 == 0):
            for s in (0.0, 0.25, 0.5, 0.75):
                add(left, right, u + s * beat,
                      _shaker(sr, rng, vel=vel * (0.5 if sec != "resolve" else 0.35)), pan=-0.3)
        # Clap on 2 & 4 in drive/groove.
        if sec in ("drive", "groove") and b % 4 in (1, 3):
            add(left, right, u, _clap(sr, rng, vel=vel * 0.8), pan=-0.15)
        # Bass pulse 8ths in drive/tension.
        if sec in ("drive", "tension") and b % 2 == 0:
            add(left, right, u, _bass(sr, vel=vel * 0.6))
        # Tom fills into tile changes, obstacles and contact card.
        if (65.0 <= u < 67.0 and b % 2 == 0) or any(abs(u - mark) < 0.05 for mark in (72.0, 78.0, 84.0, 90.0)):
            add(left, right, u, _tom(sr, vel=0.7, f0=160 + 40 * ((b // 2) % 3)), pan=0.4)
        if 99.0 <= u < 100.2 and b % 2 == 0:
            add(left, right, u, _tom(sr, vel=0.6, f0=140), pan=-0.4)
    # Closing soft hit + tail.
    add(left, right, 108.0, _tom(sr, vel=0.5, f0=120))

    # Master: gentle glue, fade in, peak normalize.
    for buf in (left, right):
        np.tanh(buf * 1.1, out=buf)
    fade = int(0.5 * sr)
    ramp = np.linspace(0, 1, fade)
    left[:fade] *= ramp
    right[:fade] *= ramp
    peak = max(float(np.abs(left).max()), float(np.abs(right).max()), 1e-9)
    gain = spec.peak / peak
    frames = array("h")
    for l, r in zip(left * gain, right * gain):
        frames.append(max(-32768, min(32767, round(l * 32767))))
        frames.append(max(-32768, min(32767, round(r * 32767))))
    target = io.BytesIO()
    with wave.open(target, "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(sr)
        out.writeframes(frames.tobytes())
    content = target.getvalue()
    report = {
        "schema_version": 1,
        "provider": "reels-maker-original",
        "asset_id": f"bed-{hashlib.sha256(content).hexdigest()[:20]}",
        "media_type": "audio",
        "kind": "percussion-bed",
        "file_format": "WAV PCM-16 stereo",
        "sample_rate": sr,
        "channels": 2,
        "duration_seconds": round(total / sr, 3),
        "tempo_bpm": 96,
        "seed": spec.seed,
        "generator_version": GENERATOR_VERSION,
        "rights_status": "original synthesis, no third-party content",
        "editorial_state": "quarantine",
        "license": "original work created for ASTA Energy; human listening review required",
        "source": "deterministic in-repository synthesis (src/reels_maker/audio_bed.py)",
    }
    report["sha256"] = hashlib.sha256(content).hexdigest()
    return content, report
