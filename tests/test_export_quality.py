"""Delivery checks: ffprobe metadata cannot silently hide missing frames."""
import json
import shutil
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from reels_maker.export_quality import verify_metadata, verify_export
from reels_maker.ffmpeg import RenderError, execute, probe
from reels_maker.spec import Project, load_project
from reels_maker.renderer import render


def example_project(*, music=None):
    return Project(name="qc",width=160,height=288,fps=12,
                   scenes=[{"file":"a.mp4","duration":1.0},
                           {"file":"b.mp4","duration":1.0}],
                   music=music,branding={},output="out.mp4")


def expected_meta():
    return {
        "streams":[{
            "codec_type":"video","codec_name":"h264","pix_fmt":"yuv420p",
            "width":160,"height":288,"avg_frame_rate":"12/1",
            "nb_frames":"24","duration":"2.000000"
        }],
        "format":{"duration":"2.000000"}
    }


class DeliveryMetadataTests(unittest.TestCase):
    def test_valid_output_passes(self):
        result=verify_metadata(expected_meta(),example_project())
        self.assertEqual(result["frames_actual"],24)
        self.assertEqual(result["status"],"pass")

    def test_rejects_wrong_dimensions_fps_frames_codec_and_duration(self):
        mutations=(
            ("width",190),("height",290),("codec_name","hevc"),
            ("pix_fmt","yuv444p"),("avg_frame_rate","30000/1001"),
            ("nb_frames","23"),("duration","1.800000"),
        )
        for field,value in mutations:
            with self.subTest(field=field):
                data=deepcopy(expected_meta())
                data["streams"][0][field]=value
                with self.assertRaises(RenderError):
                    verify_metadata(data,example_project())

    def test_audio_validation(self):
        p=example_project(music={"file":"music.wav"})
        with self.assertRaises(RenderError):
            verify_metadata(expected_meta(),p)
        data=expected_meta()
        data["streams"].append({"codec_type":"audio","codec_name":"aac"})
        self.assertEqual(verify_metadata(data,p)["audio_streams"],1)
        with self.assertRaises(RenderError):
            verify_metadata(data,example_project())


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg/FFprobe required")
class ActualExportTests(unittest.TestCase):
    def test_render_returns_verified_stream_details(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            execute(["-f","lavfi","-i",
                     "color=c=red:s=160x288:r=12:d=3",
                     "-an","-c:v","libx264",
                     str(root/"a.mp4")])
            manifest=root/"script.json"
            manifest.write_text(json.dumps({
                "video":{"width":160,"height":288,"fps":12},
                "scenes":[{"file":"a.mp4","duration":1}],
                "output":"renders/qc.mp4"
            }))
            project=load_project(manifest)
            report=render(project,root=root)
            self.assertEqual(report["export_quality"]["frames_actual"],12)
            self.assertEqual(report["export_quality"]["status"],"pass")
            existing=verify_export(project,Path(report["output"]))
            self.assertEqual(existing["frames_expected"],12)


if __name__=="__main__":
    unittest.main()
