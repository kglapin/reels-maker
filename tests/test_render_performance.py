"""Pixel-parity checks for exact render-path reuse optimizations."""
from __future__ import annotations

import io
import unittest
import copy
from collections import OrderedDict
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from PIL import Image, ImageDraw

from reels_maker.core.scene_graph import Node
from reels_maker.design.tokens import resolve_tokens
from reels_maker.motionkit.keyframes import Keyframe, Track
from reels_maker.renderers.camera_canvas import CameraCanvasRenderer
from reels_maker.renderers.scene import RenderOptions, SceneRenderer
from reels_maker.textkit.typesetter import FontBook
from reels_maker.textkit.typesetter import TextStyle, typeset
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


class SourceImageCacheTests(unittest.TestCase):
    def test_source_cache_is_lru_bounded_by_decoded_bytes(self):
        width, height = 8, 8
        renderer = object.__new__(SceneRenderer)
        renderer._sources = OrderedDict()
        renderer._source_bytes = 0
        renderer._source_byte_budget = width * height * 4 * 2
        first = Image.new("RGBA", (width, height), (10, 20, 30, 255))
        second = Image.new("RGBA", (width, height), (40, 50, 60, 255))
        calls = []

        def load(image):
            def inner():
                calls.append(image)
                return image
            return inner

        self.assertIs(renderer._source("first", load(first)), first)
        self.assertIs(renderer._source("second", load(second)), second)
        # Touch second so the first entry is the least-recently-used one.
        self.assertIs(renderer._source("second", load(first)), second)
        third = Image.new("RGBA", (width, height), (70, 80, 90, 255))
        self.assertIs(renderer._source("third", load(third)), third)
        self.assertNotIn("first", renderer._sources)
        self.assertIn("second", renderer._sources)
        self.assertIn("third", renderer._sources)
        self.assertEqual(renderer._source_bytes, width * height * 4 * 2)
        self.assertEqual(len(calls), 3)


class LocalLayerParityTests(unittest.TestCase):
    def test_local_transformed_layers_match_full_canvas_rasterization(self):
        width, height = 220, 176
        tokens = resolve_tokens("editorial-premium", width=width, height=height)
        fonts = FontBook()
        renderer = SceneRenderer(
            width, height, tokens, fonts,
            options=RenderOptions(supersample=2, reuse_settled_frames=False),
        )
        block = typeset("RUCH I CZYTELNOSC", TextStyle(size=24), 104, fonts)
        nodes = [
            Node(kind="rect", role="scaled-rect",
                 props={"x": 22, "y": 32, "w": 70, "h": 34,
                        "fill": "#47A013"},
                 dx=5.25, dy=-2.5, scale=.83, rotation=11, opacity=.62),
            Node(kind="text", role="scaled-text",
                 props={"x": 12, "y": 92, "w": 104, "h": block.height,
                        "block": block, "color": (255, 255, 255),
                        "tracking_offset": 0.0},
                 dx=-2.25, dy=1.5, scale=.91, rotation=-6, opacity=.73),
        ]
        background = Image.new("RGBA", (renderer.W, renderer.H),
                               (12, 24, 36, 255))
        for source_node in nodes:
            sampled = source_node.sample(.5)
            expected = background.copy()
            isolated = Image.new("RGBA", (renderer.W, renderer.H), (0, 0, 0, 0))
            draw_node = copy.copy(sampled)
            draw_node.opacity = 1.0
            renderer._content(isolated, draw_node)
            isolated = renderer._apply_node_state(
                isolated, sampled, 0.0, 0.0, 1.0, sampled.rotation)
            expected.alpha_composite(isolated)

            actual = background.copy()
            renderer._draw_node(actual, sampled)
            self.assertEqual(expected.tobytes(), actual.tobytes(), sampled.role)



class CameraCanvasSettledFrameTests(unittest.TestCase):
    def _renderer(self, *, video=False):
        renderer = object.__new__(CameraCanvasRenderer)
        renderer.scenes = [{
            **({"video": "moving.mp4"} if video else {}),
            "camera_canvas": {
                "reveal_delay": .1,
                "reveal_duration": .5,
                "typography_motion": "fade",
            },
        }]
        renderer.w = 8
        renderer.h = 8
        renderer.stops = [(8.0, 8.0, 0.0, 1.0)]
        renderer._base_world = Image.new("RGBA", (16, 16), (20, 30, 40, 255))
        renderer._active_stage_index = -1
        renderer._active_stage = None
        renderer.local_typography = [
            Image.new("RGBA", (8, 8), (0, 0, 0, 0))]
        renderer._settled_frames = OrderedDict()
        renderer._settled_frame_bytes = 0
        renderer._settled_frame_budget = 1024
        return renderer

    def test_static_camera_canvas_reuses_settled_pixels(self):
        renderer = self._renderer()
        calls = []

        def frame(world, stop):
            calls.append(stop)
            return Image.new("RGBA", (8, 8), (12, 34, 56, 255))

        renderer._frame = frame
        built = SimpleNamespace(index=0)

        first = renderer.render(built, .7)
        repeated = renderer.render(built, .9)

        self.assertIsNot(first, repeated)
        self.assertEqual(first.tobytes(), repeated.tobytes())
        self.assertEqual(len(calls), 1)
        self.assertEqual(renderer._settled_frame_bytes, 8 * 8 * 3)

    def test_video_camera_canvas_is_never_marked_as_settled(self):
        renderer = self._renderer(video=True)
        calls = []

        def frame(world, stop):
            calls.append(stop)
            return Image.new("RGBA", (8, 8), (12, 34, 56, 255))

        renderer._frame = frame
        renderer._tile = lambda scene, photo, playback_time=None: Image.new(
            "RGBA", (8, 8), (0, 0, 0, 0))
        renderer._paste = lambda world, tile, stop: None
        built = SimpleNamespace(index=0)

        renderer.render(built, .7)
        renderer.render(built, .8)

        self.assertEqual(len(calls), 2)
        self.assertEqual(len(renderer._settled_frames), 0)


class TransitionFrameReuseTests(unittest.TestCase):
    def test_incoming_scene_frame_is_rendered_once_per_transition(self):
        class RecordingRenderer:
            def __init__(self):
                self.calls = []

            def render(self, scene, time):
                self.calls.append((scene, time))
                return Image.new("RGB", (8, 8), scene.color)

        class MemoryInput(io.BytesIO):
            def __init__(self):
                super().__init__()
                self.closed_data = b""

            def close(self):
                self.closed_data = self.getvalue()
                super().close()

        class MemoryProcess:
            def __init__(self):
                self.stdin = MemoryInput()
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
                   return_value="ffmpeg"):
            with patch("reels_maker.renderers.studio.subprocess.Popen",
                       return_value=process) as popen:
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
        self.assertEqual(
            len(process.stdin.closed_data),
            project.width * project.height * 3 * timing.frames,
        )
        self.assertEqual(
            process.stdin.closed_data[:project.width * project.height * 3],
            bytes((0x15, 0x20, 0x23)) * (project.width * project.height),
        )
        command = popen.call_args.args[0]
        self.assertEqual(command[command.index("-pix_fmt") + 1], "rgb24")


if __name__ == "__main__":
    unittest.main()
