"""Read-only LUFS and true-peak measurements from the final audio stream."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reels_maker.audio_qc import analyze_audio_loudness, _measure
from reels_maker.cli import main
from reels_maker.ffmpeg import RenderError, execute


class AudioMeterUnitTests(unittest.TestCase):
    def test_extracts_original_loudness_before_normalization(self):
        response = '''
        [Parsed_loudnorm_0]
        {
          "input_i" : "-18.90",
          "input_tp" : "-1.45",
          "input_lra" : "2.90",
          "output_i" : "-15.98",
          "output_tp" : "-1.38"
        }
        '''
        self.assertEqual(_measure(response), (-18.90, -1.45, 2.90))

    def test_malformed_loudness_is_rejected(self):
        with self.assertRaises(RenderError):
            _measure('{"output_i": "-16.1"}')

    def test_reference_range_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "empty.mp4"
            source.write_bytes(b"")
            for value in (True, -35, 0, float("nan"), float("inf")):
                with self.subTest(value=value), self.assertRaises(RenderError):
                    analyze_audio_loudness(source, reference_lufs=value)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg and FFprobe required")
class AudioMeterFFmpegTests(unittest.TestCase):
    def test_actual_aac_loudness_is_measured_without_reencoding(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sine.m4a"
            execute([
                "-f", "lavfi", "-i",
                "sine=frequency=660:sample_rate=48000:duration=1.5",
                "-c:a", "aac", "-b:a", "128k", str(source)
            ])
            before = source.read_bytes()
            report = analyze_audio_loudness(source, reference_lufs=-16)
            self.assertEqual(report["measurement"], "ebu_r128_loudnorm_first_pass")
            self.assertEqual(report["file"], str(source))
            self.assertIsInstance(report["integrated_lufs"], float)
            self.assertIsInstance(report["true_peak_dbtp"], float)
            self.assertIsInstance(report["difference_from_reference_lu"], float)
            self.assertTrue(report["manual_listening_required"])
            self.assertEqual(before, source.read_bytes())

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                exit_code = main(["audio-qc", str(source), "--json"])
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(out.getvalue())["measurement"],
                             "ebu_r128_loudnorm_first_pass")

    def test_audio_qc_refuses_silent_video_without_audio_track(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "silent.mp4"
            execute([
                "-f", "lavfi", "-i",
                "color=c=black:s=160x288:r=12:d=1",
                "-an", "-c:v", "libx264", str(source)
            ])
            with self.assertRaisesRegex(RenderError, "exactly one audio"):
                analyze_audio_loudness(source)


if __name__ == "__main__":
    unittest.main()
