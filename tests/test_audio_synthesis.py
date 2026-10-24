"""Deterministic procedural SFX creation is quarantined until rights review."""
import hashlib
import contextlib
import io
import json
import tempfile
import unittest
import wave
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from reels_maker.audio_synthesis import SFXSpec, SynthesisError, synthesize_sfx, write_procedural_sfx
from reels_maker.cli import main


class AudioSynthesisTests(unittest.TestCase):
    def test_synthetic_sfx_is_bit_reproducible_and_reports_recipe(self):
        spec = SFXSpec("whoosh", duration_seconds=0.4, sample_rate=22050, seed=42)
        first, report = synthesize_sfx(spec)
        second, other = synthesize_sfx(spec)
        self.assertEqual(first, second)
        self.assertEqual(report["sha256"], hashlib.sha256(first).hexdigest())
        self.assertEqual(report, other)
        with wave.open(BytesIO(first), "rb") as audio:
            self.assertEqual((audio.getnchannels(), audio.getsampwidth(), audio.getframerate()),
                             (2, 2, 22050))
            self.assertAlmostEqual(audio.getnframes()/audio.getframerate(), .4, places=3)
        self.assertEqual(report["rights_status"], "unknown")
        self.assertEqual(report["editorial_state"], "quarantine")

    def test_invalid_parameters_fail_closed(self):
        for spec in (SFXSpec("music"), SFXSpec("click", duration_seconds=4),
                     SFXSpec("hit", seed=True), SFXSpec("riser", peak=.9)):
            with self.subTest(spec=spec), self.assertRaises(SynthesisError):
                synthesize_sfx(spec)

    def test_writer_is_brand_scoped_and_creates_quarantine_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            brand = Path(temp) / "brands" / "demo"
            brand.mkdir(parents=True)
            report = write_procedural_sfx(SFXSpec("click", seed=5),
                                           brand="demo", root=temp)
            path = Path(report["file"])
            sidecar = Path(report["provenance_report"])
            self.assertEqual(path.parent, (brand / "imports" / "audio").resolve())
            self.assertEqual(report["quarantine_directory"], "imports/audio")
            self.assertTrue(path.is_file() and sidecar.is_file())
            self.assertEqual(json.loads(sidecar.read_text())["sha256"], report["sha256"])
            self.assertFalse((brand / "media" / "audio").exists())
            with self.assertRaisesRegex(SynthesisError, "brand must be"):
                write_procedural_sfx(SFXSpec("click"), brand="../outside", root=temp)

    def test_cli_exposes_explicit_sfx_quarantine_command(self):
        with tempfile.TemporaryDirectory() as temp:
            brand = Path(temp) / "brands" / "demo"
            brand.mkdir(parents=True)
            stdout = io.StringIO()
            args = ["reels-maker", "sfx-generate", "--brand", "demo", "--root", temp,
                    "--kind", "click", "--seed", "7", "--json"]
            with patch("sys.argv", args), contextlib.redirect_stdout(stdout):
                code = main()
            response = json.loads(stdout.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["audio"]["editorial_state"], "quarantine")
            self.assertEqual(response["audio"]["rights_status"], "unknown")


if __name__ == "__main__":
    unittest.main()
