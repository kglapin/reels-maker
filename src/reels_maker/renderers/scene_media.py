"""Rasterization of still-image, video and mesh scene nodes."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from ..core.scene_graph import Node
from . import canvas as cv


class SceneMediaRenderer:
    """Media-specific drawing that shares the parent renderer's bounded caches."""

    def __init__(self, owner):
        self.owner = owner

    def image(self, target: Image.Image, node: Node, dx: float, dy: float) -> None:
        owner = self.owner
        scale = owner.ss
        props = node.props
        path = Path(props["path"])
        if not path.is_file():
            raise ValueError(f"Missing image asset: {path}")
        stat = path.stat()
        source_key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
        source = owner._source(source_key, lambda: cv.load_image(path))
        x, y = (props["x"] + dx) * scale, (props["y"] + dy) * scale
        w, h = props["w"] * scale, props["h"] * scale
        if x + w <= 0 or y + h <= 0 or x >= owner.W or y >= owner.H:
            return
        zoom = float(props.get("zoom", 1.0))
        blur = float(props.get("blur", 0.0))
        if not math.isfinite(blur) or blur < 0:
            raise ValueError("Image blur radius must be finite and non-negative")
        blur_radius = min(blur, 24.0) * scale if blur > 0 else 0.0
        radius = float(props["radius"]) * scale if props.get("radius") else None
        width, height = int(max(1, w)), int(max(1, h))
        framed_key = (source_key, width, height, zoom,
                      float(props.get("pan_x", 0)),
                      float(props.get("pan_y", 0)), blur_radius, radius)
        image = owner._framed_images.get(framed_key)
        if image is not None:
            owner._framed_images.move_to_end(framed_key)
        else:
            image = cv.cover(
                source, width, height,
                cv.Camera(zoom=zoom,
                          x=float(props.get("pan_x", 0)),
                          y=float(props.get("pan_y", 0))))
            if blur_radius > 0:
                image = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            if radius is not None:
                mask = Image.new("L", image.size, 0)
                ImageDraw.Draw(mask).rounded_rectangle(
                    (0, 0, image.width - 1, image.height - 1),
                    radius=radius, fill=255)
                image.putalpha(Image.composite(
                    image.getchannel("A"), Image.new("L", image.size, 0), mask))
            image = image.convert("RGBA")
            owner._remember_framed_image(framed_key, image)
        target.alpha_composite(image, (int(x), int(y)))

    def video(self, target: Image.Image, node: Node, dx: float, dy: float) -> None:
        owner = self.owner
        scale = owner.ss
        props = node.props
        path = Path(props["path"])
        if not path.is_file():
            raise ValueError(f"Missing video asset: {path}")
        source = cv.load_video_frame(
            path, float(props.get("playback_time", 0.0)),
            trim_start=float(props.get("trim_start", 0.0)),
            trim_end=props.get("trim_end"))
        source = cv.crop_region(source, props.get("crop"))
        x, y = (props["x"] + dx) * scale, (props["y"] + dy) * scale
        w, h = props["w"] * scale, props["h"] * scale
        framed = cv.cover(
            source, int(max(1, w)), int(max(1, h)),
            cv.Camera(zoom=float(props.get("zoom", 1.0)),
                      x=float(props.get("pan_x", 0.0)),
                      y=float(props.get("pan_y", 0.0))))
        masked = cv.apply_shape_mask(
            framed, props.get("mask", "rounded"),
            radius=float(props.get("radius", 0.0)) * scale)
        target.alpha_composite(masked, (int(x), int(y)))

    def mesh3d(self, target: Image.Image, node: Node, dx: float, dy: float) -> None:
        from ..creative.pipeline import render_3d_product_frame

        owner = self.owner
        scale = owner.ss
        props = node.props
        x = int(round((props["x"] + dx) * scale))
        y = int(round((props["y"] + dy) * scale))
        width = int(max(4, round(props["w"] * scale)))
        height = int(max(4, round(props["h"] * scale)))
        rendered = render_3d_product_frame(
            dict(props.get("spec") or {}), width, height,
            time=float(props.get("playback_time", 0.0)))
        target.alpha_composite(rendered, (x, y))
