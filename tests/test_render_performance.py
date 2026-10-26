"""Pixel-parity checks for exact render-path reuse optimizations."""
from __future__ import annotations

import io
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from PIL import Image, ImageDraw

from reels_maker.core.scene_graph import Node
from reels_maker.design.tokens import resolve_tokens
from reels_maker.motionkit.keyframes import Keyframe, Track
from reels_maker.renderers.scene import RenderOptions, SceneRenderer
from reels_maker.textkit.typesetter import FontBook
from reels_maker.renderers.studio import _encode_studio_scene


class SettledFrameReuseTests(unittest.TestCase):
    def test_settled_animation_frame_reuse_is_pixel_identical(self):
        width, height = 240, 320
        tokens = resolve_tokens("editorial-premium", width=width, height=height)
        fonts = FontBook()
        moving = Node(
            kind="rect", role="moving-accent",
            props={"x": 40, "y": 70, "w": 90, "h": 30, "fill": "#72D18A"},
        )
        moving.track("dx", Track([
            Keyframe(0.0, -30.0, "smooth"),
            Keyframe(0.4, 0.0, "smooth"),
        ]))
        static = Node(
            kind="circle", role="static-dot",
            props={"cx": 170, "cy": 210, "r": 22, "fill": "#FFCB66"},
        )
        nodes = [moving, static]
        scene = SimpleNamespace(
            duration=2.0,
            background={"kind": "gradient", "from": "#101A14",
                        "to": "#26382D", "angle": 90},
            meta={},
            nodes=nodes,
            at=lambda time: [node.sample(time) for node in nodes],
        )
        cached = SceneRenderer(
            width, height, tokens, fonts,
            options=RenderOptions(supersample=2, reuse_settled_frames=True),
        )
        uncached = SceneRenderer(
            width, height, tokens, fonts,
            options=RenderOptions(supersample=2, reuse_settled_frames=False),
        )

        # The frame at 0.5s is rasterized once; later settled frames use its
        # exact pixels while preserving fresh image objects for callers.
        reference = uncached.render(scene, 0.8)
        first = cached.render(scene, 0.5)
        repeated = cached.render(scene, 0.8)
        self.assertIsNot(first, repeated)
        self.assertEqual(reference.tobytes(), first.tobytes())
        self.assertEqual(reference.tobytes(), repeated.tobytes())
        self.assertEqual(len(cached._settled_frames), 1)

    def test_video_scene_is_never_marked_as_settled(self):
        width, height = 240, 320
        renderer = SceneRenderer(
            width, height,
            resolve_tokens("editorial-premium", width=width, height=height),
            FontBook(),
        )
        scene = SimpleNamespace(
            duration=2.0,
            background={"kind": "solid", "color": "#101A14"},
            meta={},
            nodes=[Node(kind="video", props={"path": "clip.mp4"})],
        )
        self.assertIsNone(renderer._settled_frame_time(scene))


class FramedImageCacheTests(unittest.TestCase):
    def test_processed_still_image_is_reused_without_pixel_changes(self):
        width, height = 240, 320
        tokens = resolve_tokens("editorial-premium", width=width, height=height)
        fonts = FontBook()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "source.png"
            source = Image.new("RGBA", (96, 72), (24, 90, 155, 255))
            draw = ImageDraw.Draw(source)
            draw.ellipse((8, 5, 66, 63), fill=(245, 190, 42, 190))
            draw.rectangle((50, 24, 95, 71), fill=(218, 62, 72, 220))
            source.save(path)

            image = Node(
                kind="image", role="moving-photo",
                props={"path": str(path), "x": 20, "y": 30, "w": 180,
                       "h": 230, "zoom": 1.12, "pan_x": .2,
                       "blur": .35, "radius": 18},
            )
            image.track("opacity", Track([
                Keyframe(0.0, .35), Keyframe(.6, 1.0),
            ]))
            image.track("dx", Track([
                Keyframe(0.0, -12.0), Keyframe(.6, 0.0),
            ]))
            nodes = [image]
            scene = SimpleNamespace(
                duration=2.0,
                background={"kind": "solid", "color": "#101A14"},
                meta={}, nodes=nodes,
                at=lambda time: [node.sample(time) for node in nodes],
            )

            cached = SceneRenderer(
                width, height, tokens, fonts,
                options=RenderOptions(supersample=2),
            )
            uncached = SceneRenderer(
                width, height, tokens, fonts,
                options=RenderOptions(supersample=2),
            )
            uncached._framed_image_budget = 0

            for time in (.1, .3, .5):
                expected = uncached.render(scene, time)
                actual = cached.render(scene, time)
                self.assertEqual(expected.tobytes(), actual.tobytes())

            self.assertEqual(len(cached._framed_images), 1)



class TransitionFrameReuseTests(unittest.TestCase):
    def test_incoming_scene_frame_is_rendered_once_per_transition(self):
        class RecordingRenderer:
            def __init__(self):
                self.calls = []

            def render(self, scene, time):
                self.calls.append((scene, time))
                return Image.new("RGB", (8, 8), scene.color)

        class MemoryProcess:
            def __init__(self):
                self.stdin = io.BytesIO()
                self.stderr = io.BytesIO()

            def wait(self):
                return 0

            def poll(self):
                return 0

            def kill(self):
                pass

        renderer = RecordingRenderer()
        process = MemoryProcess()
        outgoing = SimpleNamespace(index=0, duration=1.0, color="#152023")
        incoming = SimpleNamespace(index=1, duration=1.0, color="#47A013")
        project = SimpleNamespace(width=8, height=8, fps=4)
        timing = SimpleNamespace(frames=4)

        with patch("reels_maker.renderers.studio.require_tool",
                   return_value="ffmpeg"), \\
             patch("reels_maker.renderers.studio.subprocess.Popen",
                   return_value=process):
            written = _encode_studio_scene(
                project, renderer, outgoing, timing, Path("unused.mp4"),
                codec="libx264", crf=17, preset="slow", frames_done=0,
                total_frames=4, progress=None, next_scene=incoming,
                transition={"duration": .5, "type": "radial-reveal"},
            )

        incoming_calls = [call for call in renderer.calls
                          if call[0] is incoming]
        self.assertEqual(written, timing.frames)
        self.assertEqual(len(incoming_calls), 1)


if __name__ == "__main__":
    unittest.main()
