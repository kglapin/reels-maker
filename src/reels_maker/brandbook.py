"""One-page PDF brandbook generated from the same JSON used by the renderer."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .brand import brand_directory
from .spec import ProjectError

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _color(value: str, fallback: str) -> str:
    return value if isinstance(value, str) and HEX.fullmatch(value) else fallback


def generate_brandbook(slug: str, root: Path, output: Path | None = None) -> dict:
    """Export a human-readable PDF without modifying the source brand preset."""
    try:
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise ProjectError("PDF support requires: pip install 'reels-maker[pdf]'") from exc

    folder = brand_directory(slug, root)
    source = folder / "brand.json"
    try:
        config = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProjectError(f"Cannot read brand configuration: {source}: {exc}") from exc
    if not isinstance(config, dict) or config.get("id") != slug:
        raise ProjectError(f"Invalid brand id in {source}")
    identity = config.get("identity", {})
    if not isinstance(identity, dict):
        raise ProjectError("Brand identity must be an object")
    palette = identity.get("palette", {})
    typography = identity.get("typography", {})
    safe = identity.get("safe_areas", {})
    motion = identity.get("motion", {})
    for field, value in (("palette", palette), ("typography", typography),
                         ("safe_areas", safe), ("motion", motion)):
        if not isinstance(value, dict):
            raise ProjectError(f"identity.{field} must be an object")

    destination = Path(output).resolve() if output else (
        Path(root).resolve() / "renders" / slug / "brandbook.pdf")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fonts = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/System/Library/Fonts/Supplemental/Arial.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ]
    regular, bold = "Helvetica", "Helvetica-Bold"
    for index, (normal, strong) in enumerate(fonts):
        if Path(normal).is_file() and Path(strong).is_file():
            regular, bold = f"BrandbookRegular{index}", f"BrandbookBold{index}"
            pdfmetrics.registerFont(TTFont(regular, normal))
            pdfmetrics.registerFont(TTFont(bold, strong))
            break

    w, h = A4
    pdf = canvas.Canvas(str(destination), pagesize=A4)
    pdf.setTitle(f"{config.get('name', slug)} — Brandbook")
    margin = 46
    green = _color(palette.get("primary"), "#47A013")
    pdf.setFillColor(HexColor("#14221A"))
    pdf.rect(0, h - 178, w, 178, stroke=0, fill=1)
    pdf.setFillColor(HexColor(green))
    pdf.rect(margin, h - 52, 58, 5, stroke=0, fill=1)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont(bold, 27)
    pdf.drawString(margin, h - 99, str(config.get("name", slug))[:30])
    pdf.setFont(regular, 12)
    pdf.drawString(margin, h - 125, "BRANDBOOK / VIDEO IDENTITY")
    pdf.setFont(regular, 9)
    pdf.drawString(margin, h - 153, f"Preset: {slug}   |   Version: {config.get('version', 1)}")

    y = h - 218
    def heading(label):
        nonlocal y
        pdf.setFillColor(HexColor("#14221A"))
        pdf.setFont(bold, 14)
        pdf.drawString(margin, y, label)
        y -= 22

    heading("Kolory marki")
    entries = [("Glowny", palette.get("primary", green)),
               ("Tlo", palette.get("background", "#FFFFFF")),
               ("Tekst", palette.get("text", "#FFFFFF")),
               ("Neutralny", palette.get("neutral", "#14221A"))]
    for i, (label, value) in enumerate(entries):
        value = _color(value, "#888888")
        x = margin + i * 128
        pdf.setFillColor(HexColor(value))
        pdf.roundRect(x, y - 45, 110, 43, 7, fill=1, stroke=0)
        pdf.setFillColor(HexColor("#14221A"))
        pdf.setFont(bold, 9)
        pdf.drawString(x, y - 61, label)
        pdf.setFont(regular, 9)
        pdf.drawString(x, y - 74, value.upper())
    y -= 114

    heading("Typografia")
    pdf.setFont(bold, 20)
    pdf.drawString(margin, y - 8, str(typography.get("primary", "Open Sans"))[:35])
    pdf.setFont(regular, 10)
    pdf.drawString(margin, y - 29, "Preferowany krój pisma")
    pdf.drawString(margin, y - 47, f"Fallback: {typography.get('fallback', 'DejaVu Sans')}")
    pdf.setFont(regular, 9)
    pdf.drawString(margin, y - 64, "Podglad korzysta z dostepnego fontu PDF, niekoniecznie z fontu marki.")
    y -= 103

    heading("Format i bezpieczne strefy")
    video = identity.get("format", {})
    if not isinstance(video, dict):
        video = {}
    rows = [
        f"Format: {video.get('default_width', 1080)} x {video.get('default_height', 1920)} px",
        f"FPS: {video.get('default_fps', 25)}",
        f"Gora: {safe.get('top_pixels', 190)} px",
        f"Dol: {safe.get('bottom_pixels', 290)} px",
        f"Boki: {safe.get('horizontal_pixels', 88)} px",
    ]
    pdf.setFont(regular, 11)
    for row in rows:
        pdf.drawString(margin, y, row)
        y -= 18
    y -= 18

    heading("Ruch i dzwiek")
    pdf.setFont(regular, 10)
    for line in (str(motion.get("style", "Minimal, purposeful"))[:90],
                 str(motion.get("audio", "As defined by each project"))[:90]):
        pdf.drawString(margin, y, line)
        y -= 19

    pdf.setFillColor(HexColor("#637168"))
    pdf.setFont(regular, 8)
    pdf.drawString(margin, 33, "Zrodlo: brand.json. Dokument generowany automatycznie.")
    pdf.save()
    return {"brand": slug, "output": str(destination),
            "source": str(source), "pages": 1}
