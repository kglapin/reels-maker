"""ElevenLabs TTS stays in brand quarantine until human review."""
import base64
import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from reels_maker.tts_elevenlabs import (
    TtsError, brand_tts_defaults, generate_voiceover, list_voices,
    synthesize_speech, word_timings, _wrap_pcm_wav)
from reels_maker.cli import main


def _fake_response(payload: bytes, content_type: str = "audio/mpeg"):
    class _Response:
        status = 200
        headers = {"Content-Type": content_type}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return payload

    return _Response()


class TtsElevenLabsTests(unittest.TestCase):
    def test_synthesize_posts_expected_request(self):
        seen = {}

        def fake_urlopen(request, timeout=0):
            seen["url"] = request.full_url
            seen["key"] = request.headers.get("Xi-api-key")
            seen["body"] = json.loads(request.data.decode("utf-8"))
            return _fake_response(b"ID3-audio")

        with patch("reels_maker.tts_elevenlabs.urllib.request.urlopen",
                   side_effect=fake_urlopen):
            audio, alignment = synthesize_speech(
                "Dzień dobry", voice_id="voice123", api_key="test-key")
        self.assertEqual(audio, b"ID3-audio")
        self.assertIsNone(alignment)
        self.assertIn("/v1/text-to-speech/voice123?", seen["url"])
        self.assertEqual(seen["key"], "test-key")
        self.assertEqual(seen["body"]["text"], "Dzień dobry")

    def test_timestamps_endpoint_decodes_audio_and_alignment(self):
        alignment = {"characters": ["cześć"],
                     "character_start_times_seconds": [0.0],
                     "character_end_times_seconds": [0.5]}
        payload = json.dumps({
            "audio_base64": base64.b64encode(b"PCM").decode(),
            "alignment": alignment}).encode()

        def fake_urlopen(request, timeout=0):
            self.assertIn("with-timestamps", request.full_url)
            return _fake_response(payload, "application/json")

        with patch("reels_maker.tts_elevenlabs.urllib.request.urlopen",
                   side_effect=fake_urlopen):
            audio, result = synthesize_speech(
                "cześć", voice_id="v1", with_timestamps=True, api_key="k")
        self.assertEqual(audio, b"PCM")
        self.assertEqual(result, alignment)

    def test_word_timings_groups_characters(self):
        alignment = {
            "characters": list("dwa wyrazy"),
            "character_start_times_seconds": [i * 0.1 for i in range(11)],
            "character_end_times_seconds": [(i + 1) * 0.1 for i in range(11)],
        }
        words = word_timings(alignment)
        self.assertEqual([w["word"] for w in words], ["dwa", "wyrazy"])
        self.assertAlmostEqual(words[0]["start_seconds"], 0.0)
        self.assertAlmostEqual(words[1]["end_seconds"], 1.0)
        self.assertEqual(word_timings(None), [])

    def test_pcm_payload_is_wrapped_as_wav(self):
        pcm = b"\x00\x00" * 100
        wrapped = _wrap_pcm_wav(pcm, "pcm_44100")
        with wave.open(io.BytesIO(wrapped), "rb") as audio:
            self.assertEqual((audio.getnchannels(), audio.getsampwidth(),
                              audio.getframerate()), (1, 2, 44100))
            self.assertEqual(audio.readframes(100), pcm)
        with self.assertRaises(TtsError):
            _wrap_pcm_wav(b"odd", "pcm_44100")

    def test_invalid_parameters_fail_closed(self):
        base = {"voice_id": "v1", "api_key": "k"}
        for overrides in ({"voice_id": "bad id!"},
                          {"model_id": "bad/model"},
                          {"output_format": "flac_44100"}):
            with self.subTest(overrides=overrides), self.assertRaises(TtsError):
                synthesize_speech("tekst", **{**base, **overrides})
        with self.assertRaises(TtsError):
            synthesize_speech("x" * 5001, **base)
        with self.assertRaises(TtsError):
            synthesize_speech("   ", **base)
        with self.assertRaises(TtsError):
            synthesize_speech("tekst", voice_id="v1", api_key=None,
                              base_url="http://insecure")

    def test_generate_voiceover_writes_quarantine_and_provenance(self):
        audio = b"ID3-fake-mp3"

        def fake_urlopen(request, timeout=0):
            return _fake_response(audio)

        with tempfile.TemporaryDirectory() as temp:
            brand = Path(temp) / "brands" / "demo"
            brand.mkdir(parents=True)
            with patch("reels_maker.tts_elevenlabs.urllib.request.urlopen",
                       side_effect=fake_urlopen):
                report = generate_voiceover(
                    "Witaj świecie", voice_id="voice123", brand="demo",
                    root=temp, api_key="k")
            path = Path(report["file"])
            self.assertEqual(path.parent,
                             (brand / "imports" / "audio").resolve())
            self.assertEqual(path.read_bytes(), audio)
            self.assertEqual(report["provider"], "elevenlabs")
            self.assertEqual(report["voice_id"], "voice123")
            self.assertEqual(report["editorial_state"], "quarantine")
            self.assertEqual(report["rights_status"], "unknown")
            sidecar = json.loads(
                Path(report["provenance_report"]).read_text())
            self.assertEqual(sidecar["text_sha256"], report["text_sha256"])
            self.assertNotIn("tekst", json.dumps(sidecar))
            with self.assertRaisesRegex(TtsError, "brand must be"):
                generate_voiceover("x", voice_id="v", brand="../out",
                                   root=temp, api_key="k")

    def test_brand_tts_defaults_reads_brand_json(self):
        with tempfile.TemporaryDirectory() as temp:
            brand = Path(temp) / "brands" / "demo"
            brand.mkdir(parents=True)
            self.assertEqual(brand_tts_defaults("demo", temp), {})
            (brand / "brand.json").write_text(json.dumps({
                "id": "demo",
                "voiceover": {"elevenlabs": {
                    "voice_id": "voiceABC_123",
                    "model_id": "eleven_v3",
                    "output_format": "pcm_44100"}}}))
            defaults = brand_tts_defaults("demo", temp)
            self.assertEqual(defaults["voice_id"], "voiceABC_123")
            self.assertEqual(defaults["model_id"], "eleven_v3")
            self.assertEqual(defaults["output_format"], "pcm_44100")
            (brand / "brand.json").write_text('{"id": "demo", "voiceover": 5}')
            with self.assertRaises(TtsError):
                brand_tts_defaults("demo", temp)

    def test_list_voices_filters_by_query(self):
        payload = json.dumps({"voices": [
            {"voice_id": "a1", "name": "Adam", "category": "premade"},
            {"voice_id": "b2", "name": "Bella", "category": "premade"},
        ]}).encode()

        def fake_urlopen(request, timeout=0):
            self.assertTrue(request.full_url.endswith("/v1/voices"))
            return _fake_response(payload, "application/json")

        with patch("reels_maker.tts_elevenlabs.urllib.request.urlopen",
                   side_effect=fake_urlopen):
            voices = list_voices(api_key="k", query="bel")
        self.assertEqual([v["voice_id"] for v in voices], ["b2"])

    def test_cli_tts_generate_uses_brand_default_voice(self):
        audio = b"ID3-cli"

        def fake_urlopen(request, timeout=0):
            return _fake_response(audio)

        with tempfile.TemporaryDirectory() as temp:
            brand = Path(temp) / "brands" / "demo"
            brand.mkdir(parents=True)
            (brand / "brand.json").write_text(json.dumps({
                "id": "demo",
                "voiceover": {"elevenlabs": {"voice_id": "brandvoice1"}}}))
            stdout = io.StringIO()
            import contextlib
            args = ["reels-maker", "tts-generate", "--brand", "demo",
                    "--root", temp, "--text", "Cześć", "--json"]
            with patch("reels_maker.tts_elevenlabs.urllib.request.urlopen",
                       side_effect=fake_urlopen), \
                    patch("sys.argv", args), \
                    contextlib.redirect_stdout(stdout):
                code = main()
            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["voiceover"]["voice_id"], "brandvoice1")


if __name__ == "__main__":
    unittest.main()
