"""SFX clip bounds and fade envelopes in the shared audio mixer."""
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from reels_maker.audio_mix import mux_audio
from reels_maker.ffmpeg import RenderError


class AudioMixTests(unittest.TestCase):
    def test_sfx_can_be_trimmed_and_faded_on_the_timeline(self):
        with tempfile.TemporaryDirectory(prefix="audio-sfx-bounds-") as temp:
            root = Path(temp)
            source = root / "source.mp3"
            source.write_bytes(b"fixture")
            captured = []
            with patch("reels_maker.audio_mix.execute",
                       side_effect=lambda args: captured.extend(args)):
                result = mux_audio(
                    SimpleNamespace(music=None, voiceover=None),
                    root / "silent.mp4", root / "mixed.mp4", None, None, 4.0,
                    sfx_tracks=[{
                        "file": str(source), "time": 1.2, "duration": .6,
                        "fade_out": .15, "gain_db": -18,
                    }],
                )
            filter_graph = captured[captured.index("-filter_complex") + 1]
            self.assertIn("atrim=duration=0.60000000", filter_graph)
            self.assertIn("afade=t=out:st=0.45000000:d=0.15000000", filter_graph)
            self.assertIn("adelay=1200:all=1", filter_graph)
            self.assertEqual(result["sfx"], 1)

    def test_sfx_clip_cannot_run_past_timeline_or_have_invalid_fade(self):
        with tempfile.TemporaryDirectory(prefix="audio-sfx-invalid-") as temp:
            source = Path(temp) / "source.mp3"
            source.write_bytes(b"fixture")
            for effect, message in (
                ({"file": str(source), "time": 3.8, "duration": .4},
                 "must be positive and fit"),
                ({"file": str(source), "time": 1.0, "duration": .6,
                  "fade_out": .7}, "fade_out"),
            ):
                with self.subTest(effect=effect), self.assertRaisesRegex(
                        RenderError, message):
                    mux_audio(SimpleNamespace(music=None, voiceover=None),
                              Path(temp) / "silent.mp4", Path(temp) / "mixed.mp4",
                              None, None, 4.0, sfx_tracks=[effect])


if __name__ == "__main__":
    unittest.main()
