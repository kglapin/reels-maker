"""Two-page, printable brandbook preview from a brand preset or website scan.

PDF generation is local and deterministic: it never downloads external images.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def _fonts() -> tuple[str, str]:
    regular = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    found = []
    for family, candidates in (("BrandbookRegular", regular), ("BrandbookBold", bold)):
        fontfile = next((p for p in candidates if Path(p).is_file()), None)
        if fontfile:
            try:
                pdfmetrics.registerFont(TTFont(family, fontfile))
                found.append(family)
                continue
            except Exception:
                pass
        found.append("Helvetica-Bold" if family.endswith("Bold") else "Helvetica")
    return tuple(found)


def _rgb(value: str) -> colors.Color:
    try:
        if isinstance(value, str) and len(value) == 7 and value[0] == "#":
            return colors.HexColor(value)
    except ValueError:
        pass
    return colors.HexColor("#47A013")


def _line(pdf: canvas.Canvas, x: float, y: float, text: str, *,
          font: str, size: float, ink: str = "#1F2933", limit: int = 84):
    pdf.setFont(font, size)
    pdf.setFillColor(_rgb(ink))
    value = (str(text).replace("\n", " ").strip())[:max(1, limit)]
    if len(str(text)) > limit:
        value = value[:-1] + "…"
    pdf.drawString(x, y, value)


def _block(pdf, text: str, x: float, y: float, width: float, *,
           font: str, size: int = 10, color: str = "#43525A",
           leading: int = 15, max_lines: int = 5) -> float:
    words = str(text).replace("\n", " ").split()
    lines: list[str] = []
    current = ""
    for word in words:
        next_line = (current + " " + word).strip()
        if pdfmetrics.stringWidth(next_line, font, size) > width and current:
            lines.append(current)
            current = word
        else:
            current = next_line
    if current:
        lines.append(current)
    for line in lines[:max_lines]:
        _line(pdf, x, y, line, font=font, size=size, ink=color, limit=160)
        y -= leading
    return y


def _page_bottom(pdf, number: int, font: str, *, draft: bool):
    pdf.setStrokeColor(_rgb("#E4E8EB"))
    pdf.line(44, 50, A4[0] - 44, 50)
    _line(pdf, 44, 32, "PROPOZYCJA DO WERYFIKACJI" if draft
          else "IDENTYFIKACJA WIZUALNA", font=font, size=8,
          ink="#5D6872")
    _line(pdf, A4[0] - 85, 32, f"{number} / 2", font=font, size=8,
          ink="#5D6872")


def _palette_from(profile: dict) -> dict:
    return profile.get("palette") or profile.get("identity", {}).get("palette") or {
        "primary": profile.get("branding", {}).get("accent", "#47A013"),
        "background": "#FFFFFF", "text": "#14221A", "neutral": "#2C3435"}


def _fonts_from(profile: dict) -> dict:
    return profile.get("typography") or profile.get("identity", {}).get("typography", {})


def _preview_image(profile: dict, root: Path | None) -> Path | None:
    for downloaded in profile.get("downloaded_logos", []):
        candidate = Path(downloaded.get("path", ""))
        if candidate.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and candidate.is_file():
            return candidate
    if root is not None:
        logo = profile.get("branding", {}).get("logo")
        if logo:
            candidate = Path(root) / str(logo)
            if candidate.suffix.lower() in (".png", ".jpg", ".jpeg") and candidate.is_file():
                return candidate
    return None


def make_brandbook(profile: dict, destination: Path, *, assets_root: Path | None = None,
                   draft: bool = False) -> Path:
    """Draw a compact printable PDF without requiring hosted services."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    regular, bold = _fonts()
    name = str(profile.get("name") or profile.get("id") or "Nowa marka")
    palette = _palette_from(profile)
    typography = _fonts_from(profile)
    accent = str(palette.get("primary", "#47A013"))
    body_font = str(typography.get("primary", "Do potwierdzenia"))
    fallback_font = str(typography.get("fallback", "DejaVu Sans"))
    source = str(profile.get("source_url") or profile.get("source", {}).get("website", ""))
    logo_img = _preview_image(profile, assets_root)
    w, h = A4
    c = canvas.Canvas(str(destination), pagesize=A4, pageCompression=1,
                      invariant=1)
    c.setTitle(f"Brandbook - {name}")
    c.setAuthor("Reels Maker")

    # Page 1 — identity and practical video preview.
    c.setFillColor(_rgb("#111F20"))
    c.rect(0, h - 235, w, 235, fill=1, stroke=0)
    c.setFillColor(_rgb(accent))
    c.rect(44, h - 85, 58, 5, fill=1, stroke=0)
    _line(c, 44, h - 62, "BRANDBOOK  /  REELS MAKER",
          font=bold, size=10, ink="#D8E5DF")
    _line(c, 44, h - 128, name, font=bold, size=27,
          ink="#FFFFFF", limit=29)
    _line(c, 44, h - 157, "Wytyczne wizualne dla wideo i materiałów digital",
          font=regular, size=11, ink="#C5D2D0")
    _line(c, 44, h - 194,
          "AUTOMATYCZNY SZKIC - SPRAWDŹ PRZED UŻYCIEM" if draft
          else "KONFIGURACJA MARKI", font=bold, size=9, ink="#E4F1EB")

    # Logo card.
    c.setFillColor(colors.white)
    c.roundRect(w - 228, h - 197, 180, 110, 10, fill=1, stroke=0)
    if logo_img:
        try:
            image = ImageReader(str(logo_img))
            iw, ih = image.getSize()
            iw = max(1, iw)
            ih = max(1, ih)
            ratio = min(145 / iw, 75 / ih)
            iw, ih = iw * ratio, ih * ratio
            c.drawImage(image, w - 138 - iw / 2, h - 139 - ih / 2,
                        width=iw, height=ih, mask="auto", preserveAspectRatio=True)
        except Exception:
            _line(c, w - 209, h - 145, "LOGO", font=bold, size=18, ink=accent)
    else:
        _line(c, w - 207, h - 142, "LOGO", font=bold, size=18, ink=accent)
        _line(c, w - 207, h - 162, "wymaga weryfikacji", font=regular,
              size=8, ink="#55636B")

    _line(c, 44, h - 274, "01   PALETA KOLORÓW", font=bold, size=13)
    chips = [
        ("GŁÓWNY", palette.get("primary", "#47A013")),
        ("TŁO", palette.get("background", "#FFFFFF")),
        ("TEKST", palette.get("text", "#14221A")),
        ("NEUTRALNY", palette.get("neutral", "#2C3435")),
    ]
    spacing = 13
    chip_w = (w - 88 - spacing * 3) / 4
    ychip = h - 392
    for i, (label, value) in enumerate(chips):
        x = 44 + i * (chip_w + spacing)
        c.setFillColor(_rgb(value))
        c.roundRect(x, ychip, chip_w, 84, 7, fill=1, stroke=0)
        c.setStrokeColor(_rgb("#DDE3E3"))
        c.roundRect(x, ychip, chip_w, 84, 7, fill=0, stroke=1)
        _line(c, x, ychip - 18, label, font=bold, size=8, ink="#56636A")
        _line(c, x, ychip - 37, value, font=bold, size=12)

    _line(c, 44, h - 469, "02   TYPOGRAFIA", font=bold, size=13)
    _line(c, 44, h - 497, f"Rekomendowany font: {body_font}", font=bold, size=11, limit=67)
    _line(c, 44, h - 517, f"Fallback: {fallback_font}", font=regular, size=10)
    _line(c, 44, h - 570, "Prosta energia. Spójna komunikacja.",
          font=bold, size=17, limit=42)
    _line(c, 44, h - 593, "Przykładowy nagłówek w bezpiecznej strefie kadru.",
          font=regular, size=10)
    _line(c, 44, h - 630,
          "Podgląd korzysta z lokalnego fontu PDF; nazwa fontu marki jest rekomendacją.",
          font=regular, size=8, ink="#687981", limit=110)
    _page_bottom(c, 1, regular, draft=draft)
    c.showPage()

    # Page 2 — video-safe usage and verification list.
    _line(c, 44, h - 62, "03   ZASTOSOWANIE W REELS", font=bold, size=14)
    safe = profile.get("identity", {}).get("safe_areas", {})
    top = int(safe.get("top_pixels", 190))
    bottom = int(safe.get("bottom_pixels", 290))
    horizontal = int(safe.get("horizontal_pixels", 88))
    # 9:16 stage with boundaries; frame is a conceptual preview, not screenshot.
    fx, fy, fw, fh = 44, h - 447, 180, 320
    c.setFillColor(_rgb("#14241E"))
    c.roundRect(fx, fy, fw, fh, 10, fill=1, stroke=0)
    c.setFillColor(_rgb(accent))
    c.roundRect(fx + 18, fy + 105, fw - 36, 5, 2, fill=1, stroke=0)
    _line(c, fx + 18, fy + 153, "TWOJA MARKA", font=bold, size=11, ink="#FFFFFF")
    _line(c, fx + 18, fy + 130, "Spójne wideo", font=regular, size=10, ink="#FFFFFF")
    c.setStrokeColor(_rgb("#B1DBC4"))
    c.setDash(4, 4)
    c.rect(fx + horizontal / 1080 * fw,
           fy + bottom / 1920 * fh,
           fw * (1 - 2 * horizontal / 1080),
           fh * (1 - (top + bottom) / 1920), fill=0, stroke=1)
    c.setDash()
    _line(c, 250, h - 145, "FORMAT I STREFY", font=bold, size=11)
    _block(c, "9:16  |  1080 × 1920 px", 250, h - 172, 288,
           font=regular, size=11)
    _block(c, f"Górna rezerwa: {top} px", 250, h - 205, 288,
           font=regular, size=10)
    _block(c, f"Dolna rezerwa: {bottom} px", 250, h - 230, 288,
           font=regular, size=10)
    _block(c, f"Boczne marginesy: {horizontal} px", 250, h - 255, 288,
           font=regular, size=10)
    _block(c, "Przy publikacji sprawdź strefy zajęte przez interfejs platformy.",
           250, h - 300, 281, font=regular, size=10, max_lines=3)

    _line(c, 44, h - 493, "04   POCHODZENIE I WERYFIKACJA", font=bold, size=13)
    y = h - 523
    if source:
        y = _block(c, "Źródło: " + source, 44, y, w - 88,
                   font=regular, size=9, leading=15, max_lines=2) - 12
    else:
        _line(c, 44, y, "Źródło: zapisana konfiguracja marki", font=regular, size=9)
        y -= 22
    suggestions = [
        "Kolory: porównaj z aktualną stroną i oficjalną księgą znaku.",
        "Logo: sprawdź wariant jasny / ciemny, tło i pole ochronne.",
        "Fonty: potwierdź krój, dostępne grubości i licencję.",
        "Film: przetestuj czytelność i kontrast na telefonie.",
    ]
    for item in suggestions:
        c.setFillColor(_rgb(accent))
        c.circle(49, y + 3, 3, stroke=0, fill=1)
        y = _block(c, item, 62, y, w - 110, font=regular,
                   size=9, max_lines=2) - 11

    c.setFillColor(_rgb("#EFF4F1"))
    c.roundRect(44, 106, w - 88, 67, 8, fill=1, stroke=0)
    _line(c, 58, 147, "STATUS: " + ("PROPOZYCJA Z WWW" if draft else "ZAPISANY PRESET"),
          font=bold, size=10, ink="#21392A")
    _line(c, 58, 125, "Nie zmieniaj produkcyjnego brand.json bez zatwierdzenia.",
          font=regular, size=9, ink="#44554A")
    _page_bottom(c, 2, regular, draft=draft)
    c.showPage()
    c.save()
    return destination


def saved_brandbook_data(brand_dir: Path) -> dict:
    """Load an accepted brand; no implicit web calls."""
    config = Path(brand_dir) / "brand.json"
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot load brand configuration: {config}") from exc
    if not isinstance(data, dict):
        raise ValueError("Brand configuration must be an object")
    return data
