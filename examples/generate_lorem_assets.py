"""Generate original, deterministic, brand-neutral assets for the Lorem Ipsum demo.

These are *source assets* for the repository's actual studio renderer.
No copyrighted samples, web footage, proprietary brand assets or external APIs.
"""
from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

OUT = Path(__file__).resolve().parent / "media"
OUT.mkdir(exist_ok=True)
W, H = 1080, 1920
Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
xx = X / W
yy = Y / H
rng = np.random.default_rng(20261023)

def image(name: str, variant: int) -> None:
    if variant == 1:
        glow = np.exp(-((xx - .43)**2 / .27 + (yy - .39)**2 / .19))
        halo = np.sqrt(((xx - .52) / .36)**2 + ((yy - .52) / .22)**2)
        ring = np.exp(-((halo - 1.0) / .045)**2)
        ring2 = np.exp(-((halo - 1.25) / .065)**2)
        twist = .5 + .5 * np.sin(22 * xx + 13 * yy + 14 * xx * yy)
        r = 15 + 68 * glow + 105 * ring + 14 * ring2
        g = 12 + 28 * glow + 35 * ring + 22 * ring2
        b = 30 + 85 * glow + 115 * ring + 25 * ring2 + 8 * twist
    else:
        spine = .5 + .23 * np.sin(8 * yy + .6) + .09 * np.sin(21 * yy)
        distance = np.abs(xx - spine)
        sweep = np.exp(-(distance / .055)**2)
        glow = np.exp(-(distance / .19)**2)
        edge = np.exp(-((distance - .13) / .012)**2)
        haze = np.exp(-((yy - .62) / .35)**2)
        r = 12 + 145 * sweep * haze + 48 * glow + 36 * edge
        g = 12 + 30 * sweep + 28 * glow + 45 * edge
        b = 25 + 165 * sweep + 67 * glow + 70 * edge
    grain = rng.normal(0, 2.4, (H, W)).astype(np.float32)
    vignette = 1 - .53 * ((xx - .5)**2 * 2 + (yy - .5)**2 * 1.2)
    channels = [np.clip((c + grain) * vignette, 0, 255).astype(np.uint8)
                for c in (r, g, b)]
    picture = Image.fromarray(np.stack(channels, axis=2), mode="RGB")
    picture.save(OUT / name, optimize=True)
    print("Generated image", name)

def wav(name: str, signal: np.ndarray, sr: int = 32000) -> None:
    signal = np.nan_to_num(signal).astype(np.float32)
    peak = np.max(np.abs(signal)) or 1.
    signal = np.clip(signal / peak * .86, -1, 1)
    pcm = np.round(signal * 32767).astype("<i2")
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print("Generated audio", name)

def audio() -> None:
    sr = 32000
    duration = 35.7
    n = round(duration * sr)
    t = np.arange(n, dtype=np.float32) / sr
    tempo = 116
    beat = 60 / tempo
    result = np.zeros(n, dtype=np.float32)
    # Soft low-end pulse + airy, restrained electronic harmony.
    chord = [110., 130.813, 164.814, 220.]
    for k, frequency in enumerate(chord):
        result += (.034 / (1 + .25*k)) * np.sin(2*np.pi*frequency*t + .08*np.sin(2*np.pi*.21*t))
    result *= .66 + .24 * np.sin(2*np.pi*.37*t)
    for i in range(int(duration / beat) + 1):
        t0 = i * beat
        offset = round(t0*sr)
        length = min(int(.31*sr), n-offset)
        if length <= 0: break
        tau = np.arange(length, dtype=np.float32) / sr
        if i % 4 in (0, 2):
            frequency = 53 + 72 * np.exp(-tau * 33)
            phase = 2*np.pi * np.cumsum(frequency)/sr
            result[offset:offset+length] += .43*np.sin(phase)*np.exp(-tau*17)
        if i % 4 in (1, 3):
            clap = rng.normal(0, 1, length).astype(np.float32)
            # short sharp, layered snare with exponential tail
            result[offset:offset+length] += .085*clap*np.exp(-tau*35)
        if i % 2 == 1:
            bass = np.sin(2*np.pi * (55.0 if i%8<4 else 65.4) * tau)
            result[offset:offset+length] += .078 * bass * np.exp(-tau*12)
        for subdivision in (0, .5):
            pos = offset + int(subdivision*beat*sr)
            hlen = min(int(.075*sr), n-pos)
            if hlen <= 0: continue
            htau = np.arange(hlen, dtype=np.float32)/sr
            noise = rng.normal(0, 1, hlen).astype(np.float32)
            noise = np.r_[noise[0], np.diff(noise)]
            result[pos:pos+hlen] += .035*noise*np.exp(-htau*82)
    # Short melodic arpeggios and gentle fade.
    for i in range(int(duration / (beat/2))):
        pos = round(i * beat / 2 * sr)
        length = min(round(.31*sr), n-pos)
        if length <= 0: break
        tau = np.arange(length, dtype=np.float32) / sr
        note = [440, 523.25, 659.26, 783.99, 659.26, 523.25, 392.0, 523.25][i%8]
        result[pos:pos+length] += .026*np.sin(2*np.pi*note*tau)*np.exp(-tau*12)
    result *= np.minimum(1, t/.5) * np.minimum(1, (duration-t)/1.5)
    wav("showcase-score.wav", result, sr)
    d = .45
    tau = np.arange(round(d*sr),dtype=np.float32)/sr
    impact = .40*np.sin(2*np.pi*(72-25*tau)*tau)*np.exp(-tau*14)
    burst = rng.normal(0,1,len(tau)).astype(np.float32)
    impact += .14*burst*np.exp(-tau*42)
    wav("soft-hit.wav", impact, sr)

if __name__ == "__main__":
    image("abstract-orbit.png", 1)
    image("abstract-ribbon.png", 2)
    audio()
