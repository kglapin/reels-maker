"""Narrator + music technical mixing and independent track validation."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reels_maker.audio_mix import mux_audio
from reels_maker.brand import apply_brand
from reels_maker.ffmpeg import RenderError, execute, probe
from reels_maker.renderer import render
from reels_maker.spec import Project, ProjectError, load_project


class VoiceoverSchemaTests(unittest.TestCase):
    def test_accepts_explicit_audio_source_and_frame_aligned_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "script.json"
            path.write_text(json.dumps({
                "scenes": [{"file": "a.mp4", "duration": 3,
                            "title": {"headline": "ENERGY"},
                            "motion": {"preset": "fade_stagger",
                                       "cue_seconds": {"headline": 1.04}}}],
                "music": {"file": "music.wav", "ducking": "sidechain",
                          "volume": 0.35},
                "voiceover": {"file": "narrator.wav", "start": 0.1,
                              "offset_seconds": 0.15, "volume": 1.0}
            }))
            p = load_project(path)
            self.assertEqual(p.voiceover["offset_seconds"], 0.15)
            self.assertEqual(p.music["ducking"], "sidechain")

    def test_rejects_bad_voiceover_or_music_ducking(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "script.json"
            for extra in (
                {"voiceover": {"file": ""}},
                {"voiceover": {"file": "narrator.wav", "volume": -1}},
                {"voiceover": {"file": "narrator.wav", "volume": float("nan")}},
                {"voiceover": {"file": "narrator.wav", "volume": 5}},
                {"voiceover": {"file": "narrator.wav", "offset_seconds": 3}},
                {"voiceover": {"file": "narrator.wav", "start": "0.1"}},
                {"voiceover": {"file": "narrator.wav", "effect": "surprise"}},
                {"music": {"file": "music.wav", "ducking": "sidechain"}},
                {"music": {"file": "music.wav", "ducking": "extreme"}}
            ):
                with self.subTest(extra=extra):
                    path.write_text(json.dumps({
                        "scenes": [{"file": "a.mp4", "duration": 2}],
                        **extra
                    }))
                    with self.assertRaises(ProjectError):
                        load_project(path)

    def test_voiceover_is_scoped_to_its_brand(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "brands" / "demo").mkdir(parents=True)
            (root / "brands" / "demo" / "brand.json").write_text(
                json.dumps({"id": "demo", "branding": {}}))
            project = Project(
                name="voice", width=320, height=568, fps=25,
                scenes=[{"file": "media/shot.mp4", "duration": 3}],
                music=None, voiceover={"file": "media/audio/voice.wav"},
                branding={}, output="renders/voice.mp4", brand="demo")
            resolved = apply_brand(project, root)
            self.assertEqual(
                resolved.voiceover["file"],
                "brands/demo/media/audio/voice.wav")

    def test_sidechain_filter_requires_two_tracks(self):
        with patch("reels_maker.audio_mix.execute") as invoke:
            p = Project(
                name="mix", width=320, height=568, fps=25,
                scenes=[{"file": "a.mp4", "duration": 3}],
                music={"file": "music.wav", "ducking": "sidechain"},
                voiceover={"file": "vo.wav", "offset_seconds": .25},
                branding={}, output="out.mp4")
            result = mux_audio(
                p, Path("video.mp4"), Path("out.mp4"),
                Path("music.wav"), Path("vo.wav"), 3)
            args = invoke.call_args.args[0]
            graph = args[args.index("-filter_complex") + 1]
            self.assertIn("sidechaincompress=", graph)
            self.assertIn("adelay=250:all=1", graph)
            self.assertIn("alimiter=limit=0.95", graph)
            self.assertTrue(result["voiceover"])
            self.assertEqual(result["ducking"], "sidechain")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg/FFprobe required")
class VoiceoverRenderTests(unittest.TestCase):
    def test_voiceover_music_ducking_and_silence_pad(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            execute(["-f", "lavfi", "-i",
                     "color=c=gray:s=320x568:r=25:d=3",
                     "-an", "-c:v", "libx264",
                     str(root / "visual.mp4")])
            execute(["-f", "lavfi", "-i",
                     "sine=frequency=440:sample_rate=48000:duration=4",
                     "-c:a", "pcm_s16le", str(root / "music.wav")])
            execute(["-f", "lavfi", "-i",
                     "sine=frequency=880:sample_rate=48000:duration=0.8",
                     "-c:a", "pcm_s16le", str(root / "voice.wav")])
            path = root / "mixed.json"
            path.write_text(json.dumps({
                "video": {"width": 320, "height": 568, "fps": 25},
                "scenes": [{"file": "visual.mp4", "duration": 2.4}],
                "music": {
                    "file": "music.wav", "ducking": "sidechain",
                    "volume": 0.35, "fade_out": 0.15
                },
                "voiceover": {
                    "file": "voice.wav", "offset_seconds": 0.4,
                    "volume": 1.0
                },
                "output": "renders/mixed.mp4"
            }))
            project = load_project(path)
            result = render(project, root=root)
            self.assertTrue(result["audio_mix"]["voiceover"])
            self.assertEqual(result["audio_mix"]["ducking"], "sidechain")
            self.assertEqual(result["export_quality"]["frames_actual"], 60)
            metadata = probe(Path(result["output"]))
            audio = [s for s in metadata["streams"]
                     if s["codec_type"] == "audio"]
            self.assertEqual(len(audio), 1)
            self.assertEqual(audio[0]["codec_name"], "aac")
            self.assertEqual(int(audio[0]["sample_rate"]), 48000)
            warm = render(project, root=root)
            self.assertEqual(warm["scenes_encoded"], 0)

    def test_voiceover_only_has_one_valid_aac_track(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            execute(["-f", "lavfi", "-i",
                     "color=c=blue:s=160x288:r=12:d=2",
                     "-an", "-c:v", "libx264",
                     str(root / "visual.mp4")])
            execute(["-f", "lavfi", "-i",
                     "sine=frequency=330:sample_rate=48000:duration=1",
                     "-c:a", "pcm_s16le", str(root / "voice.wav")])
            path = root / "narrated.json"
            path.write_text(json.dumps({
                "video": {"width": 160, "height": 288, "fps": 12},
                "scenes": [{"file": "visual.mp4", "duration": 1.5}],
                "voiceover": {"file": "voice.wav", "offset_seconds": .25},
                "output": "renders/narrated.mp4"
            }))
            result = render(load_project(path), root=root)
            self.assertFalse(result["audio_mix"]["music"])
            self.assertTrue(result["audio_mix"]["voiceover"])
            self.assertEqual(result["export_quality"]["audio_streams"], 1)


if __name__ == "__main__":
    unittest.main()
