"""Software scene renderer for the retained graph.

Rendering and QA share the graph but not the pixels: QA samples the same graph
for geometry and (optionally) real frames for contrast. Supersampling keeps
rounded shapes, rings and small type crisp in final output.
"""
from __future__ import annotations

import math
import copy
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from ..components.base import BuiltScene
from ..core.scene_graph import Node
from ..core.transforms import Bounds, LocalSpace
from ..design.color import mix, parse_hex
from ..design.tokens import DesignTokens
from ..textkit.typesetter import FontBook, TextBlock
from . import canvas as cv
from .scene_media import SceneMediaRenderer
from .scene_transition import apply_scene_transition


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
    reuse_settled_frames: bool = True


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
        self._sources: OrderedDict[object, Image.Image] = OrderedDict()
        self._source_bytes = 0
        self._source_byte_budget = 256 * 1024 * 1024
        self._framed_images: OrderedDict[tuple, Image.Image] = OrderedDict()
        self._framed_image_bytes = 0
        self._framed_image_budget = 128 * 1024 * 1024
        self._settled_frame_times: dict[int, float | None] = {}
        self._settled_frames: OrderedDict[int, Image.Image] = OrderedDict()
        self._settled_frame_bytes = 0
        self._settled_frame_budget = 128 * 1024 * 1024
        self._media = SceneMediaRenderer(self)

    # ------------------------------------------------------------------ public
    def render(self, scene: BuiltScene, time: float) -> Image.Image:
        if not math.isfinite(time):
            raise ValueError("Render time must be finite")
        if time < 0 or time > scene.duration + 1e-6:
            raise ValueError("Render time is outside the scene")
        scene_key = id(scene)
        settled_at = self._settled_frame_time(scene)
        if (self.options.reuse_settled_frames and settled_at is not None
                and time >= settled_at):
            cached = self._settled_frames.get(scene_key)
            if cached is not None:
                self._settled_frames.move_to_end(scene_key)
                return cached.copy()
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
        image = image.convert("RGB")
        if (self.options.reuse_settled_frames and settled_at is not None
                and time >= settled_at):
            self._remember_settled_frame(scene_key, image)
        return image

    def _settled_frame_time(self, scene: BuiltScene) -> float | None:
        """Find when a scene becomes time-invariant, or return None if it never does."""
        key = id(scene)
        if key in self._settled_frame_times:
            return self._settled_frame_times[key]
        if scene.background.get("kind", "solid") not in ("solid", "gradient"):
            self._settled_frame_times[key] = None
            return None
        pending = list(scene.nodes)
        seen: set[int] = set()
        settled_at = 0.0
        while pending:
            node = pending.pop()
            if id(node) in seen:
                continue
            seen.add(id(node))
            if node.kind in ("video", "mesh3d"):
                self._settled_frame_times[key] = None
                return None
            pending.extend(node.children or [])
            if node.tracks:
                settled_at = max(settled_at, *(track.end
                                               for track in node.tracks.values()))
        transition = scene.meta.get("transition_in")
        if transition and transition != "cut":
            settled_at = max(
                settled_at, float(scene.meta.get("transition_duration", .30)))
        self._settled_frame_times[key] = settled_at
        return settled_at

    def _remember_settled_frame(self, key: int, image: Image.Image) -> None:
        size = image.width * image.height * len(image.getbands())
        if size > self._settled_frame_budget:
            return
        previous = self._settled_frames.pop(key, None)
        if previous is not None:
            self._settled_frame_bytes -= (
                previous.width * previous.height * len(previous.getbands()))
        cached = image.copy()
        self._settled_frames[key] = cached
        self._settled_frame_bytes += size
        while self._settled_frame_bytes > self._settled_frame_budget:
            _, evicted = self._settled_frames.popitem(last=False)
            self._settled_frame_bytes -= (
                evicted.width * evicted.height * len(evicted.getbands()))

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

    def _source(self, key: object, loader) -> Image.Image:
        """Load a source image through a byte-bounded LRU cache."""
        cached = self._sources.get(key)
        if cached is not None:
            self._sources.move_to_end(key)
            return cached
        image = loader()
        size = image.width * image.height * len(image.getbands())
        if size <= self._source_byte_budget:
            previous = self._sources.pop(key, None)
            if previous is not None:
                self._source_bytes -= (
                    previous.width * previous.height * len(previous.getbands()))
            self._sources[key] = image
            self._source_bytes += size
            while self._source_bytes > self._source_byte_budget:
                _, evicted = self._sources.popitem(last=False)
                self._source_bytes -= (
                    evicted.width * evicted.height * len(evicted.getbands()))
        return image

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
            source_path = Path(asset).resolve()
            source_stat = source_path.stat()
            source_key = (str(source_path), source_stat.st_mtime_ns,
                          source_stat.st_size)
            source = self._source(
                source_key, lambda: cv.load_image(source_path))
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
        if self._draw_local_layer(target, node, ox, oy, progress, rotation):
            return
        layer = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        # Primitive painters use node.opacity while drawing. The isolated
        # layer applies the node opacity below as a group property; clear it
        # only on the shallow drawing copy so animated opacity is applied once
        # rather than squared (e.g. .5 -> .25).
        draw_node = node
        if node.opacity < .999:
            draw_node = copy.copy(node)
            draw_node.opacity = 1.0
        self._content(layer, draw_node, ox, oy)
        layer = self._apply_node_state(layer, node, ox, oy, progress, rotation)
        target.alpha_composite(layer)

    def _draw_local_layer(self, target: Image.Image, node: Node,
                          ox: float, oy: float, progress: float,
                          rotation: float) -> bool:
        """Composite a transformed leaf through a padded, region-local layer.

        The full-frame fallback remains for clipping/reveal masks, 3D/media,
        and shadowed panels. For ordinary typography/vector leaves this avoids
        allocating and resampling a supersampled canvas for a small object.
        """
        if (node.kind not in {"rect", "block", "round", "circle", "ring",
                              "line", "path", "text", "number"}
                or node.clip is not None or progress < .999
                or (node.kind == "round" and node.props.get("shadow"))):
            return False
        base_bounds = node.base_bounds()
        if base_bounds is None:
            return False
        bounds = base_bounds
        if node.kind == "text":
            block = node.props.get("block")
            if isinstance(block, TextBlock):
                words = [word for line in block.lines for word in line.words]
                if words:
                    x, y = float(node.props.get("x", 0)), float(node.props.get("y", 0))
                    bounds = (
                        min(bounds[0], x + min(word.x for word in words)),
                        min(bounds[1], y),
                        max(bounds[2], x + max(word.x + word.width
                                               for word in words)),
                        max(bounds[3], y + block.height),
                    )
        mapped = node.local_to_parent_transform().map_bounds(
            Bounds[LocalSpace](*bounds))
        world = (mapped.left, mapped.top, mapped.right, mapped.bottom)

        scale = self.ss
        padding = 4 * scale
        source_left = math.floor((bounds[0] + node.dx + ox) * scale) - padding
        source_top = math.floor((bounds[1] + node.dy + oy) * scale) - padding
        source_right = math.ceil((bounds[2] + node.dx + ox) * scale) + padding
        source_bottom = math.ceil((bounds[3] + node.dy + oy) * scale) + padding
        if source_right <= source_left or source_bottom <= source_top:
            return True
        # Avoid pathological scratch images for malformed/oversized authored
        # geometry; the legacy clipped full-canvas path remains bounded.
        if (source_right - source_left > self.W * 2
                or source_bottom - source_top > self.H * 2):
            return False

        out_padding = 3 * scale
        output_left = max(0, math.floor((world[0] + ox) * scale) - out_padding)
        output_top = max(0, math.floor((world[1] + oy) * scale) - out_padding)
        output_right = min(self.W, math.ceil((world[2] + ox) * scale) + out_padding)
        output_bottom = min(self.H, math.ceil((world[3] + oy) * scale) + out_padding)
        if output_right <= output_left or output_bottom <= output_top:
            return True

        source = Image.new(
            "RGBA", (source_right - source_left, source_bottom - source_top),
            (0, 0, 0, 0))
        draw_node = node
        if node.opacity < .999:
            draw_node = copy.copy(node)
            draw_node.opacity = 1.0
        self._content(source, draw_node,
                      ox - source_left / scale,
                      oy - source_top / scale)
        if node.opacity < .999:
            source.putalpha(source.getchannel("A").point(
                lambda value: int(value * node.opacity)))

        if node.scale == 1 and abs(rotation) <= 1e-6:
            transformed = source
        else:
            anchor = node.anchor
            if anchor is None:
                anchor = ((base_bounds[0] + base_bounds[2]) / 2,
                          (base_bounds[1] + base_bounds[3]) / 2)
            # dx/dy are applied after scale/rotation in the shared scene-graph
            # transform, so the raster pivot includes the node's own offsets.
            ax = (anchor[0] + node.dx + ox) * scale
            ay = (anchor[1] + node.dy + oy) * scale
            angle = math.radians(rotation)
            cosine, sine = math.cos(angle), math.sin(angle)
            node_scale = node.scale
            if not math.isfinite(node_scale) or node_scale <= 0:
                raise ValueError("Animated node scale must remain finite and positive")
            inverse = (cosine / node_scale, sine / node_scale,
                       -sine / node_scale, cosine / node_scale)
            a, c, b, d = inverse
            e = ax - a * ax - c * ay
            f = ay - b * ax - d * ay
            # Pillow maps output coordinates back to source coordinates. Shift
            # that affine from full-canvas coordinates to the local source tile.
            matrix = (
                a, c,
                a * output_left + c * output_top + e - source_left,
                b, d,
                b * output_left + d * output_top + f - source_top,
            )
            transformed = source.transform(
                (output_right - output_left, output_bottom - output_top),
                Image.Transform.AFFINE, matrix,
                resample=Image.Resampling.BICUBIC)
        target.alpha_composite(transformed, (output_left, output_top))
        return True

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
            ax = (anchor[0] + node.dx + ox) * self.ss
            ay = (anchor[1] + node.dy + oy) * self.ss
            angle = math.radians(rotation)
            cosine, sine = math.cos(angle), math.sin(angle)
            scale = node.scale
            if not math.isfinite(scale) or scale <= 0:
                raise ValueError("Animated node scale must remain finite and positive")
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
            color=node.props.get("color"), scale=self.ss, skip_effects=True,
            character_progress=node.props.get("character_progress"))
        mask_layer = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        cv.text_block_mask(
            mask_layer, block, origin, self.fonts,
            tracking_offset=float(node.props.get("tracking_offset", 0)),
            scale=self.ss,
            character_progress=node.props.get("character_progress"))
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
                shadow_blur = float(props.get(
                    "shadow_blur", max(6, radius * .45) / s)) * s
                shadow_opacity = float(props.get("shadow_opacity", .42))
                shadow_dx = float(props.get("shadow_dx", 0.0)) * s
                shadow_dy = float(props.get("shadow_dy", 0.0)) * s
                if (not all(math.isfinite(value) for value in
                            (shadow_blur, shadow_opacity, shadow_dx, shadow_dy))
                        or shadow_blur < 0):
                    raise ValueError("Shadow parameters must be finite; blur must be non-negative")
                shadow_opacity = max(0.0, min(1.0, shadow_opacity))
                pad = int(math.ceil(max(
                    8, radius * .8,
                    shadow_blur * 1.5 + max(abs(shadow_dx), abs(shadow_dy)))))
                shadow_x = int(round(x + shadow_dx)) - pad
                shadow_y = int(round(y + shadow_dy)) - pad
                shadow_w, shadow_h = int(w) + pad * 2, int(h) + pad * 2
                if (shadow_x + shadow_w > 0 and shadow_y + shadow_h > 0
                        and shadow_x < self.W and shadow_y < self.H):
                    layer = Image.new("RGBA", (shadow_w, shadow_h),
                                      (0, 0, 0, 0))
                    cv.rounded(layer, (pad, pad, pad + w, pad + h), radius,
                               props.get("fill"), None, 1, opacity=1.0)
                    shadow = cv.shadow(layer, radius=max(1, shadow_blur),
                                       opacity=shadow_opacity)
                    target.alpha_composite(shadow, (shadow_x, shadow_y))
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
                          skip_effects=True,
                          character_progress=props.get("character_progress"))
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
        self._media.image(target, node, dx, dy)

    def _remember_framed_image(self, key: tuple, image: Image.Image) -> None:
        size = image.width * image.height * len(image.getbands())
        if size > self._framed_image_budget:
            return
        previous = self._framed_images.pop(key, None)
        if previous is not None:
            self._framed_image_bytes -= (
                previous.width * previous.height * len(previous.getbands()))
        self._framed_images[key] = image
        self._framed_image_bytes += size
        while self._framed_image_bytes > self._framed_image_budget:
            _, evicted = self._framed_images.popitem(last=False)
            self._framed_image_bytes -= (
                evicted.width * evicted.height * len(evicted.getbands()))

    def _video(self, target: Image.Image, node: Node, dx: float, dy: float) -> None:
        self._media.video(target, node, dx, dy)

    def _mesh3d(self, target: Image.Image, node: Node, dx: float, dy: float) -> None:
        self._media.mesh3d(target, node, dx, dy)

    # -------------------------------------------------------------- transitions
    def _transition(self, image: Image.Image, name: str, time: float,
                    duration: float) -> None:
        apply_scene_transition(
            image, name, time, duration, self.tokens.palette.accent)
