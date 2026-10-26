"""Video streaming decode must return the same frames as timestamp seeks."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from reels_maker.renderers.canvas import (
    clear_video_frame_cache,
    collect_video_decode_metrics,
    load_video_frame,
)


class VideoStreamDecodeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required")
    def test_stream_matches_legacy_seeks_for_trimmed_timestamp_sequence(self):
        with tempfile.TemporaryDirectory(prefix="video-stream-parity-") as temp:
            video = Path(temp) / "testsrc.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=30:duration=2",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p", str(video),
            ], check=True)
            timestamps = [0.0, .53, 1.47]
            clear_video_frame_cache()
            reference = [
                load_video_frame(video, timestamp, trim_start=.1, trim_end=1.9)
                for timestamp in timestamps
            ]

            clear_video_frame_cache()
            with collect_video_decode_metrics() as metrics:
                streamed = [
                    load_video_frame(video, timestamp,
                                     trim_start=.1, trim_end=1.9)
                    for timestamp in timestamps
                ]

            self.assertEqual([frame.tobytes() for frame in streamed],
                             [frame.tobytes() for frame in reference])
            self.assertEqual(metrics["video_decode_calls"], 1)
            self.assertEqual(metrics["video_decoder_processes"], 1)
            self.assertGreaterEqual(metrics["video_decoded_frames"], len(timestamps))


if __name__ == "__main__":
    unittest.main()
