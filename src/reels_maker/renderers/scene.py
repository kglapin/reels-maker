"""Software scene renderer for the retained graph.

Rendering and QA share the graph but not the pixels: QA samples the same graph
for geometry and (optionally) real frames for contrast. Supersampling keeps
rounded shapes, rings and small type crisp in final output.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from ..components.base import BuiltScene
from ..core.scene_graph import Node
from ..design.color import mix, parse_hex
from ..design.tokens import DesignTokens
from ..textkit.typesetter import FontBook
from . import canvas as cv


def _rgb(value) -> tuple[int, int, int]:
    """Accept a hex string or an already parsed RGB triplet."""
    if isinstance(value, (tuple, list)) and len(value) == 3:
        channels = tuple(int(channel) for channel in value)
        if all(0 <= channel <= 255 for channel in channels):
            return channels
        raise ValueError(f"Invalid RGB colour: {value!r}")
    return parse_hex(value)


@dataclass(frozen=True)
class RenderOptions:
    supersample: int = 1
    background_blur: float = 0.0


class SceneRenderer:
    def __init__(self, width: int, height: int, tokens: DesignTokens,
                 fonts: FontBook, *, options: RenderOptions | None = None):
        if width < 2 or height < 2:
            raise ValueError("Canvas must be at least 2x2 pixels")
        self.width, self.height = width, height
        self.tokens = tokens
        self.fonts = fonts
        self.options = options or RenderOptions()
        if self.options.supersample not in (1, 2):
            raise ValueError("Supersample must be 1 or 2")
        self.ss = self.options.supersample
        self.W, self.H = width * self.ss, height * self.ss
        self._backgrounds: dict[tuple, Image.Image] = {}
        self._sources: dict[str, Image.Image] = {}

    # ------------------------------------------------------------------ public
    def render(self, scene: BuiltScene, time: float) -> Image.Image:
        if not math.isfinite(time):
            raise ValueError("Render time must be finite")
        if time < 0 or time > scene.duration + 1e-6:
            raise ValueError("Render time is outside the scene")
        image = self._background(scene, time)
        for node in scene.at(time):
            self._draw_node(image, node)
        transition = scene.meta.get("transition_in")
        if transition and transition != "cut":
            self._transition(image, transition, time,
                             scene.meta.get("transition_duration", .30))
        if self.ss > 1:
            image = image.resize((self.width, self.height),
                                 Image.Resampling.LANCZOS)
        return image.convert("RGB")

    def render_overlay(self, scene: BuiltScene, time: float) -> Image.Image:
        """Render scene nodes onto transparent RGBA for video composition."""
        if not math.isfinite(time):
            raise ValueError("Render time must be finite")
        if time < 0 or time > scene.duration + 1e-6:
            raise ValueError("Render time is outside the scene")
        image = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        for node in scene.at(time):
            self._draw_node(image, node)
        if self.ss > 1:
            image = image.resize((self.width, self.height),
                                 Image.Resampling.LANCZOS)
        return image

    def frame_bytes(self, scene: BuiltScene, time: float) -> bytes:
        return self.render(scene, time).convert("RGBA").tobytes("raw", "BGRA")

    # -------------------------------------------------------------- background
    def _background(self, scene: BuiltScene, time: float) -> Image.Image:
        spec = scene.background
        kind = spec.get("kind", "solid")
        key = (kind, tuple(sorted((str(k), str(v)) for k, v in spec.items()
                                  if k not in ("camera",))), self.W, self.H)
        if kind in ("solid", "gradient") and key in self._backgrounds:
            return self._backgrounds[key].copy()
        if kind == "solid":
            image = Image.new("RGBA", (self.W, self.H),
                              (*_rgb(spec.get("color", "#101A14")), 255))
        elif kind == "gradient":
            gradient = cv.gradient_image(
                self.W, self.H, _rgb(spec.get("from", "#101A14")),
                _rgb(spec.get("to", "#1A2E22")),
                float(spec.get("angle", 90)))
            image = gradient.convert("RGBA")
        elif kind == "photo":
            asset = spec.get("asset")
            if not asset:
                raise ValueError("Photo background requires an asset path")
            source_key = str(Path(asset).resolve())
            source = self._sources.get(source_key)
            if source is None:
                source = cv.load_image(asset)
                self._sources[source_key] = source
            camera_spec = spec.get("camera") or {}
            direction = camera_spec.get("direction", "push-in")
            intensity = float(camera_spec.get("intensity", .06))
            progress = min(1.0, max(0.0, time / max(1e-6, scene.duration)))
            if direction == "pull-out":
                zoom = 1 + intensity * (1 - progress)
            else:
                zoom = 1 + intensity * progress
            pan_x = (intensity * .35 * progress
                     if direction == "pan-right" else
                     -intensity * .35 * progress
                     if direction == "pan-left" else 0.0)
            pan_y = -intensity * .22 * progress if direction == "drift-up" else 0.0
            image = cv.cover(source, self.W, self.H,
                             cv.Camera(zoom=zoom, x=pan_x, y=pan_y)).convert("RGBA")
            if spec.get("tint"):
                image = cv.tint(image, _rgb(spec["tint"]),
                                float(spec.get("tint_amount", .14)))
            image = cv.scrim(image, float(spec.get("scrim", .55)))
        else:
            raise ValueError(f"Unknown background kind {kind!r}")
        if kind in ("solid", "gradient"):
            # The caller draws onto the returned surface. Cache a pristine
            # copy, never the surface that is about to be mutated.
            self._backgrounds[key] = image.copy()
        return image

    # ------------------------------------------------------------------- nodes
    def _draw_node(self, target: Image.Image, node: Node,
                   ox: float = 0.0, oy: float = 0.0) -> None:
        if not node.visible():
            return
        reveal = node.reveal or {}
        progress = float(reveal.get("progress", 1.0))
        if progress <= .001:
            return
        block = node.props.get("block") if node.kind == "text" else None
        if (block is not None
                and any(word.effect == "negative"
                        for line in block.lines for word in line.words)):
            self._draw_negative_text(target, node, ox, oy)
            return
        rotation = float(node.props.get(
            "_carousel_rotation", node.rotation))
        needs_layer = (node.opacity < .999 or node.scale != 1
                       or abs(rotation) > 1e-6
                       or node.clip is not None or progress < .999)
        if not needs_layer:
            self._content(target, node, ox, oy)
            return
        layer = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        self._content(layer, node, ox, oy)
        layer = self._apply_node_state(layer, node, ox, oy, progress, rotation)
        target.alpha_composite(layer)

    def _apply_node_state(self, layer: Image.Image, node: Node,
                          ox: float, oy: float, progress: float,
                          rotation: float | None = None) -> Image.Image:
        rotation = float(node.props.get(
            "_carousel_rotation",
            node.rotation if rotation is None else rotation))
        if node.clip is not None or progress < .999:
            visible = node.world_bounds()
            if visible is None:
                return layer
            mask = Image.new("L", (self.W, self.H), 0)
            draw = ImageDraw.Draw(mask)
            box = (round(visible[0] * self.ss), round(visible[1] * self.ss),
                   round(visible[2] * self.ss), round(visible[3] * self.ss))
            if box[2] > box[0] and box[3] > box[1]:
                draw.rectangle(box, fill=255)
            layer.putalpha(Image.composite(
                layer.getchannel("A"), Image.new("L", layer.size, 0), mask))
        if node.opacity < .999:
            alpha = node.opacity
            layer.putalpha(layer.getchannel("A").point(
                lambda value: int(value * alpha)))
        if node.scale != 1 or abs(rotation) > 1e-6:
            anchor = node.anchor
            if anchor is None:
                base = node.base_bounds()
                if base is None:
                    return layer
                anchor = ((base[0] + base[2]) / 2, (base[1] + base[3]) / 2)
            ax, ay = anchor[0] * self.ss + ox * self.ss, anchor[1] * self.ss + oy * self.ss
            angle = math.radians(rotation)
            cosine, sine = math.cos(angle), math.sin(angle)
            scale = node.scale if node.scale > 0 else 1e-6
            matrix = (cosine / scale, sine / scale,
                      ax - (cosine / scale) * ax - (sine / scale) * ay,
                      -sine / scale, cosine / scale,
                      ay + (sine / scale) * ax - (cosine / scale) * ay)
            layer = layer.transform((self.W, self.H), Image.Transform.AFFINE,
                                    matrix, resample=Image.Resampling.BICUBIC)
        return layer

    def _draw_negative_text(self, target: Image.Image, node: Node,
                            ox: float, oy: float) -> None:
        """Invert pixels only inside marked glyphs on an opaque scene surface."""
        if target.getchannel("A").getextrema()[0] < 255:
            raise ValueError(
                "Negative rich text must be a top-level scene element so it "
                "can sample the composed background")
        block = node.props["block"]
        origin = (node.props["x"] + node.dx + ox,
                  node.props["y"] + node.dy + oy)
        normal = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        cv.text_block(
            normal, block, origin, self.fonts,
            tracking_offset=float(node.props.get("tracking_offset", 0)),
            color=node.props.get("color"), scale=self.ss, skip_effects=True)
        mask_layer = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        cv.text_block_mask(
            mask_layer, block, origin, self.fonts,
            tracking_offset=float(node.props.get("tracking_offset", 0)),
            scale=self.ss)
        progress = float((node.reveal or {}).get("progress", 1.0))
        normal = self._apply_node_state(normal, node, ox, oy, progress)
        mask_layer = self._apply_node_state(mask_layer, node, ox, oy, progress)
        target.alpha_composite(normal)
        original = target.convert("RGB")
        negative = ImageOps.invert(original)
        result = Image.composite(negative, original, mask_layer.getchannel("A"))
        target.paste(result, (0, 0))

    def _content(self, target: Image.Image, node: Node,
                 ox: float = 0.0, oy: float = 0.0) -> None:
        dx = node.dx + ox
        dy = node.dy + oy
        if node.kind in ("group", "scene"):
            for child in node.children:
                self._draw_node(target, child, dx, dy)
            return
        self._primitive(target, node, dx, dy)

    def _primitive(self, target: Image.Image, node: Node,
                   dx: float, dy: float) -> None:
        props = node.props
        s = self.ss
        opacity = node.opacity
        kind = node.kind
        if kind in ("rect", "block"):
            x, y = (props["x"] + dx) * s, (props["y"] + dy) * s
            w, h = props["w"] * s, props["h"] * s
            ImageDraw.Draw(target, "RGBA").rectangle(
                (x, y, x + w, y + h), fill=cv._rgba(props.get("fill"), opacity))
            return
        if kind == "round":
            x, y = (props["x"] + dx) * s, (props["y"] + dy) * s
            w, h = props["w"] * s, props["h"] * s
            progress = props.get("progress")
            if progress is not None and node.role.startswith("bar"):
                w *= max(0.0, min(1.0, float(progress)))
            if w <= 0 or h <= 0:
                return
            radius = float(props.get("r", 0)) * s
            if props.get("shadow"):
                pad = int(max(8, radius * .8))
                layer = Image.new("RGBA", (int(w) + pad * 2,
                                           int(h) + pad * 2), (0, 0, 0, 0))
                cv.rounded(layer, (pad, pad, pad + w, pad + h), radius,
                           props.get("fill"), None, 1, opacity=1.0)
                shadow = cv.shadow(layer, radius=max(6, radius * .45),
                                   opacity=.42)
                target.alpha_composite(shadow, (int(x) - pad, int(y) - pad))
            cv.rounded(target, (x, y, x + w, y + h), radius,
                       props.get("fill"), props.get("border"),
                       int(props.get("border_width", 1) * s), opacity)
            return
        if kind == "circle":
            cv.circle(target, (props["cx"] + dx) * s, (props["cy"] + dy) * s,
                      props["r"] * s, props.get("fill"), props.get("border"),
                      int(props.get("border_width", 1) * s), opacity)
            return
        if kind == "ring":
            progress = float(props.get("progress", 1.0))
            cv.ring(target, (props["cx"] + dx) * s, (props["cy"] + dy) * s,
                    props["r"] * s, props["width"] * s, props["color"],
                    progress=progress,
                    start_angle=float(props.get("start_angle", -90)),
                    opacity=opacity)
            return
        if kind == "line":
            pts = [((props["x1"] + dx) * s, (props["y1"] + dy) * s),
                   ((props["x2"] + dx) * s, (props["y2"] + dy) * s)]
            if "progress" in props or "trim_start" in props:
                pts = cv.trim_polyline(
                    pts, float(props.get("progress", 1.0)),
                    start=float(props.get("trim_start", 0.0)),
                )
            if pts:
                cv.line(target, pts,
                        props.get("color", (255, 255, 255)),
                        props.get("width", 1) * s, opacity)
            return
        if kind == "path":
            points = [((x + dx) * s, (y + dy) * s) for x, y in props["points"]]
            if "progress" in props or "trim_start" in props:
                points = cv.trim_polyline(
                    points, float(props.get("progress", 1.0)),
                    start=float(props.get("trim_start", 0.0)),
                )
            if points:
                cv.line(target, points, props.get("color", (255, 255, 255)),
                        props.get("width", 1) * s, opacity,
                        closed=bool(props.get("closed")) and float(props.get("progress", 1.0)) >= .999,
                        fill=bool(props.get("fill")) and float(props.get("progress", 1.0)) >= .999)
            return
        if kind == "icon":
            self._icon(target, node, dx, dy)
            return
        if kind == "image":
            self._image(target, node, dx, dy)
            return
        if kind == "video":
            self._video(target, node, dx, dy)
            return
        if kind == "mesh3d":
            self._mesh3d(target, node, dx, dy)
            return
        if kind == "text":
            block = props["block"]
            cv.text_block(target, block, (props["x"] + dx, props["y"] + dy),
                          self.fonts,
                          tracking_offset=float(props.get("tracking_offset", 0)),
                          color=props.get("color"), opacity=opacity, scale=s,
                          skip_effects=True)
            return
        if kind == "number":
            cv.number(target, float(props.get("value", 0)),
                      (props["x"] + dx, props["y"] + dy,
                       props["w"], props["h"]),
                      self.fonts, fmt=props.get("format"),
                      size=int(props.get("size", 120)),
                      color=props.get("color", (255, 255, 255)),
                      align=props.get("align", "center"),
                      opacity=opacity,
                      tracking_offset=float(props.get("tracking_offset", 0)),
                      scale=s)
            return
        raise ValueError(f"Unknown primitive kind {kind!r}")

    def _icon(self, target: Image.Image, node: Node, dx: float, dy: float) -> None:
        """Rasterize a pinned icon SVG with per-size, colour and stroke cache."""
        from ..icon_library import raster
        props = node.props
        size = round(float(props["size"]) * self.ss)
        colour = props["color"]
        if isinstance(colour, (tuple, list)):
            colour = "#{:02X}{:02X}{:02X}".format(*(int(v) for v in colour))
        bitmap = raster(str(props["library"]), str(props["name"]), size,
                        str(colour), style=str(props.get("style", "outline")),
                        stroke_width=float(props.get("stroke_width", 0)),
                        cache_dir=props.get("cache_dir"),
                        offline=bool(props.get("offline", False)),
                        weight=props.get("weight", 400),
                        fill=props.get("fill", False),
                        grade=props.get("grade", 0),
                        optical_size=props.get("optical_size", 24))
        x = int(round((float(props["x"]) + dx) * self.ss))
        y = int(round((float(props["y"]) + dy) * self.ss))
        target.alpha_composite(bitmap, (x, y))

    def _image(self, target: Image.Image, node: Node, dx: float, dy: float) -> None:
        s = self.ss
        props = node.props
        path = Path(props["path"])
        if not path.is_file():
            raise ValueError(f"Missing image asset: {path}")
        cache_key = str(path.resolve())
        if cache_key not in self._sources:
            self._sources[cache_key] = cv.load_image(path)
        source = self._sources[cache_key]
        x, y = (props["x"] + dx) * s, (props["y"] + dy) * s
        w, h = props["w"] * s, props["h"] * s
        zoom = float(props.get("zoom", 1.0))
        image = cv.cover(source, int(max(1, w)), int(max(1, h)),
                         cv.Camera(zoom=zoom,
                                   x=float(props.get("pan_x", 0)),
                                   y=float(props.get("pan_y", 0))))
        blur = float(props.get("blur", 0.0))
        if not math.isfinite(blur) or blur < 0:
            raise ValueError("Image blur radius must be finite and non-negative")
        if blur > 0:
            image = image.filter(ImageFilter.GaussianBlur(
                radius=min(blur, 24.0) * s))
        if props.get("radius"):
            mask = Image.new("L", image.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, image.width - 1, image.height - 1),
                radius=float(props["radius"]) * s, fill=255)
            image.putalpha(Image.composite(
                image.getchannel("A"), Image.new("L", image.size, 0), mask))
        target.alpha_composite(image.convert("RGBA"), (int(x), int(y)))

    def _video(self, target: Image.Image, node: Node, dx: float, dy: float) -> None:
        s = self.ss
        props = node.props
        path = Path(props["path"])
        if not path.is_file():
            raise ValueError(f"Missing video asset: {path}")
        source = cv.load_video_frame(
            path,
            float(props.get("playback_time", 0.0)),
            trim_start=float(props.get("trim_start", 0.0)),
            trim_end=props.get("trim_end"),
        )
        source = cv.crop_region(source, props.get("crop"))
        x, y = (props["x"] + dx) * s, (props["y"] + dy) * s
        w, h = props["w"] * s, props["h"] * s
        zoom = float(props.get("zoom", 1.0))
        framed = cv.cover(
            source,
            int(max(1, w)),
            int(max(1, h)),
            cv.Camera(
                zoom=zoom,
                x=float(props.get("pan_x", 0.0)),
                y=float(props.get("pan_y", 0.0)),
            ),
        )
        masked = cv.apply_shape_mask(
            framed,
            props.get("mask", "rounded"),
            radius=float(props.get("radius", 0.0)) * s,
        )
        target.alpha_composite(masked, (int(x), int(y)))

    def _mesh3d(self, target: Image.Image, node: Node, dx: float, dy: float) -> None:
        from ..creative.pipeline import render_3d_product_frame

        s = self.ss
        props = node.props
        x, y = int(round((props["x"] + dx) * s)), int(round((props["y"] + dy) * s))
        w, h = int(max(4, round(props["w"] * s))), int(max(4, round(props["h"] * s)))
        rendered = render_3d_product_frame(
            dict(props.get("spec") or {}),
            w, h,
            time=float(props.get("playback_time", 0.0)),
        )
        target.alpha_composite(rendered, (x, y))

    # -------------------------------------------------------------- transitions
    def _transition(self, image: Image.Image, name: str, time: float,
                    duration: float) -> None:
        if duration <= 0:
            return
        progress = min(1.0, max(0.0, time / duration))
        if progress >= 1:
            return
        accent = self.tokens.palette.accent
        blend = .94
        if isinstance(name, dict):
            name = name.get("type", "cut")
        if name == "cut" or not name:
            return
        if name == "dip":
            overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
            alpha = int(255 * (1 - progress))
            ImageDraw.Draw(overlay).rectangle(
                (0, 0, image.width, image.height), fill=(5, 10, 7, alpha))
            image.alpha_composite(overlay)
            return
        if name not in ("wipe-left", "wipe-right", "wipe-up", "wipe-down"):
            raise ValueError(f"Unknown transition {name!r}")
        panel = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(panel)
        if name in ("wipe-left", "wipe-right"):
            width = image.width
            offset = width * progress
            if name == "wipe-left":
                box = (offset, 0, width, image.height)
            else:
                box = (0, 0, width - offset, image.height)
        else:
            height = image.height
            offset = height * progress
            if name == "wipe-up":
                box = (0, offset, image.width, image.height)
            else:
                box = (0, 0, image.width, height - offset)
        draw.rectangle(box, fill=(*accent, int(255 * blend)))
        # A thin bright edge gives the wipe a deliberate cut, not a glitch.
        edge = max(2, round(image.width * .004))
        if name == "wipe-left":
            draw.rectangle((box[0] - edge, 0, box[0], image.height),
                           fill=(255, 255, 255, 210))
        elif name == "wipe-right":
            draw.rectangle((box[2], 0, box[2] + edge, image.height),
                           fill=(255, 255, 255, 210))
        elif name == "wipe-up":
            draw.rectangle((0, box[1] - edge, image.width, box[1]),
                           fill=(255, 255, 255, 210))
        else:
            draw.rectangle((0, box[3], image.width, box[3] + edge),
                           fill=(255, 255, 255, 210))
        image.alpha_composite(panel)
