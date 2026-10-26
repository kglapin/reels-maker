"""Shared segment assembly must preserve FFmpeg concat semantics."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reels_maker.ffmpeg import RenderError
from reels_maker.renderer import _join
from reels_maker.segment_assembly import join_segments


class SegmentAssemblyTests(unittest.TestCase):
    def test_builds_stream_copy_concat_command_and_quotes_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            scratch = Path(folder)
            first = scratch / "a'clip.mp4"
            second = scratch / "b clip.mp4"
            destination = scratch / "joined.mp4"
            with patch("reels_maker.segment_assembly.execute") as execute:
                join_segments([first, second], destination, scratch, max_frames=72)

            manifest = (scratch / "segments.txt").read_text(encoding="utf-8")
            self.assertEqual(
                manifest,
                "file '" + str(first).replace("'", "'\\''") + "'\n"
                + "file '" + str(second).replace("'", "'\\''") + "'\n",
            )
            command = execute.call_args.args[0]
            self.assertEqual(command[:8], [
                "-f", "concat", "-safe", "0", "-i",
                str(scratch / "segments.txt"), "-map", "0:v:0",
            ])
            self.assertIn("copy", command)
            self.assertEqual(command[-3:], ["-frames:v", "72", str(destination)])

    def test_frame_limit_validation_is_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            scratch = Path(folder)
            for value in (0, -1, True):
                with self.subTest(value=value):
                    with self.assertRaises(RenderError):
                        join_segments([], scratch / "out.mp4", scratch,
                                      max_frames=value)

    def test_classic_private_helper_remains_a_compatible_wrapper(self):
        parts = [Path("one.mp4")]
        destination = Path("out.mp4")
        scratch = Path("tmp")
        with patch("reels_maker.renderer.join_segments") as shared:
            _join(parts, destination, scratch, max_frames=12)
        shared.assert_called_once_with(parts, destination, scratch, max_frames=12)


if __name__ == "__main__":
    unittest.main()
