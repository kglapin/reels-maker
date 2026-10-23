"""Pre-render simple safe-zone typography once per distinct segment."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .ffmpeg import RenderError
from .spec import Project
from .typography import layout_runs
from .canvas_layout import design_scale, resolve_safe_areas


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
                if draw.textlength(word, font=face) > width:
                    raise RenderError(f"Single word too wide for frame: {word}")
                result.append(current)
                current = word
            else:
                raise RenderError(f"Single word too wide for frame: {word}")
        if current:
            result.append(current)
    return result


def resolve_title_style(project: Project, title: dict) -> dict:
    """Apply an opt-in, brand-owned creative profile to a single scene.

    Profiles avoid silently restyling existing videos; explicit scene settings
    always win. Unrecognized profile names are a hard failure, not a fallback.
    """
    name = title.get("profile")
    if name is None:
        return title
    profiles = project.branding.get("editorial_profiles", {})
    if not isinstance(profiles, dict) or name not in profiles:
        raise RenderError(f"Unknown editorial title profile: {name!r}")
    preset = profiles[name]
    if not isinstance(preset, dict):
        raise RenderError(f"Invalid editorial title profile: {name!r}")
    allowed = {"theme", "position", "headline_style", "backdrop", "logo", "accent_rule"}
    if set(preset) - allowed:
        raise RenderError("Editorial title profile has unsupported settings")
    return {**preset, **title}


def draw_card(project: Project, title: dict, logo: Path | None, target: Path,
              layers: list[dict] | None = None) -> bool:
    title = resolve_title_style(project, title)
    if title.get("logo", True) is False:
        logo = None
    if not any(title.get(k) for k in ("kicker", "headline", "body", "footer")) and logo is None:
        return False

    w, h = project.width, project.height
    scale = design_scale(w, h)
    margin, top_safe, bottom_safe = resolve_safe_areas(
        w, h, project.branding.get("safe_areas", {}))
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

    # Light editorial cards use dark ink on bright clean footage; dark cards
    # retain the familiar white-on-scrim treatment. Never apply a dark scrim
    # under a light-theme headline.
    theme = title.get("theme", "dark")
    if theme not in ("dark", "light"):
        raise RenderError("title.theme must be dark or light")
    backdrop = title.get("backdrop", "none" if theme == "light" else "soft")
    if backdrop not in ("soft", "strong", "none"):
        raise RenderError("title.backdrop must be soft, strong or none")
    if theme == "light" and backdrop != "none":
        raise RenderError("Light typography requires title.backdrop=none")
    if title and backdrop != "none":
        y0 = int(h * .38)
        gradient = Image.new("RGBA", (1, h - y0))
        px = gradient.load()
        max_alpha, gamma = ((180, .95) if backdrop == "soft"
                            else (222, .75))
        for yy in range(h - y0):
            t = yy / max(1, h - y0 - 1)
            # Neutral and smooth, with no colored glass or harsh rectangle.
            px[0, yy] = (0, 0, 0, int(max_alpha * t ** gamma))
        img.alpha_composite(gradient.resize((w, h - y0)), (0, y0))

    if logo:
        try:
            source = Image.open(logo).convert("RGBA")
            if source.width < 1 or source.height < 1:
                raise RenderError("Logo image has invalid dimensions")
            aspect = source.width / source.height
            # Responsive even on wide cinematic and square canvases:
            # bound mark width by both canvas width and available height.
            lw = max(1, round(min(w * 0.21, h * .15 * aspect)))
            lh = max(1, round(lw / aspect))
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
    # Supporting copy must remain readable on a phone. Scale via the
    # shorter canvas side rather than assuming a 9:16 output.
    # Editorial hero numbers need a larger but bounded primary headline.
    # The safe-zone check still fails rather than allowing clipped lettering.
    headline_base = 186 if title.get("headline_style") == "hero" else 74
    size = [round(v * scale) for v in (32, headline_base, 49, 29)]
    if (title.get("headline_style") == "hero"
            and isinstance(title.get("headline"), str)
            and title["headline"].strip()):
        # Premium hero numbers fill the text column without wrapping the amount
        # across different baselines. Keep at least standard headline size.
        probe_size = max(9, size[1])
        face = _font(probe_size, True, project.branding.get("font_bold"),
                     project.branding.get("font_family"))
        usable = w - 2 * margin - round(30 * scale)
        maximum = max((draw.textlength(line, font=face)
                       for line in title["headline"].splitlines()), default=0)
        if maximum > usable and usable > 0:
            size[1] = max(round(74 * scale),
                          int(probe_size * usable / maximum * .98))
    faces = [
        _font(max(9, n), i < 2,
              project.branding.get("font_bold" if i < 2 else "font_regular"),
              project.branding.get("font_family"))
        for i, n in enumerate(size)
    ]
    available = w - 2 * margin - round(30 * scale)
    if available <= 0:
        raise RenderError("Safe areas leave no room for text")
    lines = [_wrap(draw, s.upper() if i == 0 else s, f, available)
             for i, (s, f) in enumerate(zip(fields, faces))]
    accent = str(project.branding.get("accent", "#47A013"))
    rich_layout = (layout_runs(
        draw, headline_spec["runs"],
        lambda n, bold: _font(
            n, bold,
            project.branding.get("font_bold" if bold else "font_regular"),
            project.branding.get("font_family")),
        max(9, size[1]), available, accent,
        primary="#14221A" if theme == "light" else "#FFFFFF",
        muted="#546459" if theme == "light" else "#D6E5DD") if rich else None)
    if rich_layout:
        lines[1] = ["<rich>"]
    # Real glyph bounds replace fixed line-height guesses. A headline with
    # tall digits/diacritics can never swallow the following supporting copy.
    spacing = [
        max(round(nominal * scale),
            max((draw.textbbox((0, 0), line, font=face)[3] -
                 draw.textbbox((0, 0), line, font=face)[1]
                 for line in group if line != "<rich>"), default=0)
            + max(4, round(17 * scale)))
        for nominal, group, face in zip((46, 93, 64, 41), lines, faces)
    ]
    group_gap = max(7, round(23 * scale))
    block_height = sum((rich_layout.height if i == 1 and rich_layout
                        else len(group) * spacing[i])
                       for i, group in enumerate(lines))
    block_height += group_gap * sum(bool(group) for group in lines[1:])
    bottom = h - bottom_safe
    placement = title.get("position", "lower")
    if placement not in ("upper", "middle", "lower"):
        raise RenderError("title.position must be upper, middle or lower")
    top = max(top_safe, round(h * .29) if logo else round(h * .20))
    if placement == "upper":
        y = top
    elif placement == "middle":
        y = (top + bottom - block_height) // 2
    else:
        y = bottom - block_height
    if y < top_safe or y + block_height > bottom:
        raise RenderError("Title card exceeds safe text area; shorten its text")
    if placement == "lower" and y < max(top_safe, round(h * .32)):
        raise RenderError("Title card exceeds safe text area; shorten its text")
    accent_hex = str(project.branding.get("accent", "#47A013")).lstrip("#")
    try:
        accent = "#" + accent_hex if len(accent_hex) == 6 else "#47A013"
        Image.new("RGB", (1, 1), accent)
    except ValueError as exc:
        raise RenderError("Invalid branding.accent hex color") from exc
    colors = ([accent, "#14221A", "#34463A", "#546459"] if theme == "light"
              else [accent, "#FFFFFF", "#E5F3EA", "#C4D4CC"])
    stroke = max(1, round(scale))
    def draw_safe_text(layer_draw, xy, value, font, ink, *,
                       anchor=None) -> None:
        params = {"font": font}
        if anchor:
            params["anchor"] = anchor
        bounds = layer_draw.textbbox(xy, value, **params)
        # Pixel-accurate guard: no ascender, diacritic or long word may leave
        # the editorial safe area unnoticed.
        if (bounds[0] < margin - 2 or bounds[2] > w - margin + 2 or
                bounds[1] < top_safe - 2 or bounds[3] > bottom + 2):
            raise RenderError(
                f"Text exceeds safe zone: {str(value)[:48]!r}; "
                "shorten copy, reduce emphasis or adjust project safe areas")
        layer_draw.text(xy, value, fill=ink, stroke_width=stroke,
                        stroke_fill="#07110D", **params)
    if any(lines) and title.get("accent_rule", True):
        accent_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(accent_layer).rounded_rectangle(
            (margin, y, margin + max(3, round(6 * scale)),
             y + max(15, round(70 * scale))),
            radius=max(1, round(3 * scale)), fill=accent)
        store_layer(accent_layer, "accent")
    for i, (group, face, step, ink) in enumerate(zip(lines, faces, spacing, colors)):
        if i and group:
            y += group_gap
        if not group:
            continue
        element = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        element_draw = ImageDraw.Draw(element)
        if i == 1 and rich_layout:
            if layers is None:
                for token, token_face, token_ink, px, py, _ in rich_layout.parts:
                    draw_safe_text(
                        element_draw, (margin + round(25 * scale) + px, y + py),
                        token, token_face, token_ink, anchor="ls")
                store_layer(element, "headline")
            else:
                # A headline is not one flat bitmap: independent styled runs
                # can enter sequentially, but tokens in the same run stay together.
                runs = headline_spec["runs"]
                if len(runs) > 8:
                    raise RenderError("Animated headline supports at most eight runs")
                for run_index, run in enumerate(runs):
                    run_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                    run_draw = ImageDraw.Draw(run_layer)
                    for token, token_face, token_ink, px, py, token_run in rich_layout.parts:
                        if token_run == run_index:
                            draw_safe_text(
                                run_draw, (margin + round(25 * scale) + px, y + py),
                                token, token_face, token_ink, anchor="ls")
                    store_layer(run_layer, f"headline-{run_index}")
            y += rich_layout.height
        else:
            for line in group:
                draw_safe_text(element_draw, (margin + round(25 * scale), y),
                               line, face, ink)
                y += step
            store_layer(element, ("kicker", "headline", "body", "footer")[i])

    target.parent.mkdir(parents=True, exist_ok=True)
    img.save(target)
    return True
