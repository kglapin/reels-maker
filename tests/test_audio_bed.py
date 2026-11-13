"""Tests for the original brand percussion bed (deterministic synthesis)."""
from __future__ import annotations

import io
import unittest
import wave

import numpy as np

from reels_maker.audio_bed import BedSpec, synthesize_percussion_bed


class AudioBedTest(unittest.TestCase):
    def test_duration_and_format(self):
        wav, report = synthesize_percussion_bed()
        reader = wave.open(io.BytesIO(wav))
        self.assertEqual(reader.getnchannels(), 2)
        self.assertEqual(reader.getframerate(), 48_000)
        self.assertAlmostEqual(reader.getnframes() / 48_000, 110.0, places=2)
        self.assertEqual(report["duration_seconds"], 110.0)

    def test_deterministic(self):
        wav1, _ = synthesize_percussion_bed()
        wav2, _ = synthesize_percussion_bed(BedSpec(seed=7))
        self.assertEqual(wav1, wav2)

    def test_peak_bound_and_no_silence(self):
        wav, _ = synthesize_percussion_bed()
        raw = np.frombuffer(wav[44:], dtype=np.int16).astype(float) / 32768
        self.assertLessEqual(abs(raw).max(), 0.9001)
        # Every 10 s window carries signal (no dead air).
        window = 10 * 48_000 * 2
        for start in range(0, len(raw) - window, window):
            self.assertGreater(abs(raw[start:start + window]).max(), 0.01)


if __name__ == "__main__":
    unittest.main()
