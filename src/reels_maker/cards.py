"""Pre-render simple safe-zone typography once per distinct segment."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .ffmpeg import RenderError
from .spec import Project
from .typography import layout_runs


def _font(size: int, bold: bool, custom: str | None = None,
          family: str | None = None):
    choices = [custom]
    if family and family.lower().replace(" ", "") == "opensans":
        choices.extend([
            "OpenSans-Bold.ttf" if bold else "OpenSans-Regular.ttf",
            "/usr/share/fonts/truetype/open-sans/OpenSans-Bold.ttf" if bold else
            "/usr/share/fonts/truetype/open-sans/OpenSans-Regular.ttf",
        ])
    choices.extend([
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ])
    for name in choices:
        if name:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
    raise RenderError("No TrueType font available. Install DejaVu Sans or set branding fonts")


def _wrap(draw, value: str, face, width: int) -> list[str]:
    result = []
    for paragraph in value.splitlines():
        current = ""
        for word in paragraph.split():
            trial = (current + " " + word).strip()
            if draw.textlength(trial, font=face) <= width:
                current = trial
            elif current:
                result.append(current)
                current = word
            else:
                raise RenderError(f"Single word too wide for frame: {word}")
        if current:
            result.append(current)
    return result


def draw_card(project: Project, title: dict, logo: Path | None, target: Path,
              layers: list[dict] | None = None) -> bool:
    if not any(title.get(k) for k in ("kicker", "headline", "body", "footer")) and logo is None:
        return False

    w, h = project.width, project.height
    scale = w / 1080
    safe = project.branding.get("safe_areas", {})
    if not isinstance(safe, dict):
        raise RenderError("branding.safe_areas must be an object")
    margin = round(float(safe.get("horizontal_pixels", 97)) * w / 1080)
    top_safe = round(float(safe.get("top_pixels", 165)) * h / 1920)
    bottom_safe = round(float(safe.get("bottom_pixels", 250)) * h / 1920)
    if not (0 <= margin < w / 3 and 0 <= top_safe < h / 2 and
            0 <= bottom_safe < h / 2):
        raise RenderError("Safe-area values are invalid for the selected frame")
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    def store_layer(layer, role: str) -> None:
        """Save only non-transparent pixels to avoid huge full-frame RGBA inputs."""
        if layers is None:
            img.alpha_composite(layer)
            return
        bounds = layer.getbbox()
        if bounds is None:
            return
        file = target.parent / f"layer-{len(layers):02d}-{role}.png"
        file.parent.mkdir(parents=True, exist_ok=True)
        layer.crop(bounds).save(file)
        layers.append({"file": str(file), "x": bounds[0],
                       "y": bounds[1], "role": role})

    if title:
        y0 = int(h * 0.38)
        gradient = Image.new("RGBA", (1, h - y0))
        px = gradient.load()
        for y in range(h - y0):
            t = y / max(1, h - y0 - 1)
            px[0, y] = (5, 20, 13, int(225 * t * t))
        img.alpha_composite(gradient.resize((w, h - y0)), (0, y0))

    if logo:
        try:
            source = Image.open(logo).convert("RGBA")
            lw = round(w * 0.21)
            lh = round(lw * source.height / source.width)
            logo_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            logo_layer.alpha_composite(
                source.resize((lw, lh), Image.Resampling.LANCZOS),
                (margin, max(round(h * 0.075), top_safe)))
            store_layer(logo_layer, "logo")
        except (OSError, ValueError, ZeroDivisionError) as exc:
            raise RenderError(f"Could not load PNG logo: {logo}") from exc

    draw = ImageDraw.Draw(img)
    headline_spec = title.get("headline")
    rich = isinstance(headline_spec, dict)
    fields = [str(title.get(k, "")) if k != "headline" or not rich else ""
              for k in ("kicker", "headline", "body", "footer")]
    size = [round(v * scale) for v in (29, 69, 37, 25)]
    faces = [
        _font(max(9, n), i < 2,
              project.branding.get("font_bold" if i < 2 else "font_regular"),
              project.branding.get("font_family"))
        for i, n in enumerate(size)
    ]
    available = w - 2 * margin - round(22 * scale)
    lines = [_wrap(draw, s.upper() if i == 0 else s, f, available)
             for i, (s, f) in enumerate(zip(fields, faces))]
    spacing = [round(v * scale) for v in (44, 83, 55, 37)]
    accent = str(project.branding.get("accent", "#47A013"))
    rich_layout = (layout_runs(
        draw, headline_spec["runs"],
        lambda n, bold: _font(
            n, bold,
            project.branding.get("font_bold" if bold else "font_regular"),
            project.branding.get("font_family")),
        max(9, size[1]), available, accent) if rich else None)
    if rich_layout:
        lines[1] = ["<rich>"]
    block_height = sum((rich_layout.height if i == 1 and rich_layout
                        else len(line) * spacing[i])
                       for i, line in enumerate(lines))
    block_height += round(22 * scale) * sum(bool(line) for line in lines[1:])
    bottom = h - bottom_safe
    y = bottom - block_height
    if y < max(top_safe, round(h * 0.36)):
        raise RenderError("Title card exceeds safe text area; shorten its text")
    accent_hex = str(project.branding.get("accent", "#47A013")).lstrip("#")
    try:
        accent = "#" + accent_hex if len(accent_hex) == 6 else "#47A013"
        Image.new("RGB", (1, 1), accent)
    except ValueError as exc:
        raise RenderError("Invalid branding.accent hex color") from exc
    colors = [accent, "#FFFFFF", "#E5F3EA", "#C4D4CC"]
    if any(lines):
        accent_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(accent_layer).rectangle(
            (margin, y, margin + round(6 * scale), bottom), fill=accent)
        store_layer(accent_layer, "accent")
    for i, (group, face, step, ink) in enumerate(zip(lines, faces, spacing, colors)):
        if i and group:
            y += round(22 * scale)
        if not group:
            continue
        element = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        element_draw = ImageDraw.Draw(element)
        if i == 1 and rich_layout:
            for token, token_face, token_ink, px, py in rich_layout.parts:
                element_draw.text(
                    (margin + round(25 * scale) + px, y + py),
                    token, fill=token_ink, font=token_face, anchor="lt")
            y += rich_layout.height
        else:
            for line in group:
                element_draw.text((margin + round(25 * scale), y),
                                  line, fill=ink, font=face)
                y += step
        store_layer(element, ("kicker", "headline", "body", "footer")[i])

    target.parent.mkdir(parents=True, exist_ok=True)
    img.save(target)
    return True
