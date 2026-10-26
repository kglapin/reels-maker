"""Pixel-parity checks for exact render-path reuse optimizations."""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from reels_maker.core.scene_graph import Node
from reels_maker.design.tokens import resolve_tokens
from reels_maker.motionkit.keyframes import Keyframe, Track
from reels_maker.renderers.scene import RenderOptions, SceneRenderer
from reels_maker.textkit.typesetter import FontBook


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


if __name__ == "__main__":
    unittest.main()
