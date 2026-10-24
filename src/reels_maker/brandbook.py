"""Two-page, printable brandbook preview from a brand preset or website scan.

PDF generation is local and deterministic: it never downloads external images.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

# ReportLab is an optional extra. The video engine must import without it.
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
except ImportError:
    colors = ImageReader = pdfmetrics = TTFont = canvas = None
    A4 = None


def _fonts(preferred: str = "") -> tuple[str, str]:
    clean = str(preferred).replace(" ", "")
    open_sans = clean.lower() == "opensans"
    home_fonts = Path.home() / "Library/Fonts"
    regular = (
        ([str(home_fonts / f"{clean}-Regular.ttf"), f"/Library/Fonts/{clean}-Regular.ttf"] if clean else [])
        + (["/usr/share/fonts/truetype/open-sans/OpenSans-Regular.ttf"] if open_sans else [])
        + [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    )
    bold = (
        ([str(home_fonts / f"{clean}-Bold.ttf"), f"/Library/Fonts/{clean}-Bold.ttf"] if clean else [])
        + (["/usr/share/fonts/truetype/open-sans/OpenSans-Bold.ttf"] if open_sans else [])
        + [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]
    )
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
    """Resolve a real logo image; never silently replace a configured brand mark.

    For an accepted brand the paths are relative to that brand directory.
    Website-scan drafts may refer to separately downloaded candidate images.
    """
    for downloaded in profile.get("downloaded_logos", []):
        candidate = Path(downloaded.get("path", ""))
        if candidate.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and candidate.is_file():
            return candidate
    identity_logo = profile.get("identity", {}).get("logo", {})
    if not isinstance(identity_logo, dict):
        identity_logo = {}
    logo = (profile.get("branding", {}).get("logo") or
            identity_logo.get("render_png"))
    if logo and root is not None:
        relative = Path(str(logo))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Brand logo path must stay inside brand directory: {logo}")
        candidate = (Path(root) / relative).resolve()
        if not candidate.is_relative_to(Path(root).resolve()):
            raise ValueError(f"Brand logo escapes brand directory: {logo}")
        if candidate.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            raise ValueError(f"PDF logo must be a raster image: {candidate}")
        if not candidate.is_file():
            raise ValueError(f"Brand logo is missing: {candidate}. Restore assets before exporting PDF.")
        return candidate
    return None


def _draw_logo(pdf, logo: Path, x: float, y: float,
               width: float, height: float) -> None:
    """Place the authentic mark on its intended background without distortion."""
    try:
        image = ImageReader(str(logo))
        iw, ih = image.getSize()
        if iw <= 0 or ih <= 0:
            raise ValueError("Logo image has invalid dimensions")
        scale = min(width / iw, height / ih)
        draw_w, draw_h = iw * scale, ih * scale
        pdf.drawImage(image, x + (width - draw_w) / 2,
                      y + (height - draw_h) / 2,
                      width=draw_w, height=draw_h,
                      mask="auto", preserveAspectRatio=True)
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot embed brand logo {logo}: {exc}") from exc


def make_brandbook(profile: dict, destination: Path, *, assets_root: Path | None = None,
                   draft: bool = False) -> Path:
    """Draw a compact printable PDF without requiring hosted services."""
    if canvas is None:
        from .spec import ProjectError
        raise ProjectError("PDF generation requires: pip install 'reels-maker[pdf]'")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    name = str(profile.get("name") or profile.get("id") or "Nowa marka")
    palette = _palette_from(profile)
    typography = _fonts_from(profile)
    regular, bold = _fonts(str(typography.get("primary", "")))
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
    neutral_dark = str(palette.get("neutral", "#111F20"))
    c.setFillColor(_rgb(neutral_dark))
    c.rect(0, h - 235, w, 235, fill=1, stroke=0)
    c.setFillColor(_rgb(accent))
    c.rect(44, h - 85, 58, 5, fill=1, stroke=0)
    _line(c, 44, h - 62, "BRANDBOOK  /  REELS MAKER",
          font=bold, size=10, ink="#E4E8EB")
    _line(c, 44, h - 128, name, font=bold, size=27,
          ink="#FFFFFF", limit=29)
    _line(c, 44, h - 157, "Wytyczne wizualne dla wideo i materiałów digital",
          font=regular, size=11, ink="#D5DCE2")
    _line(c, 44, h - 194,
          "AUTOMATYCZNY SZKIC - SPRAWDŹ PRZED UŻYCIEM" if draft
          else "KONFIGURACJA MARKI", font=bold, size=9, ink="#F0F4F8")

    # Logo preview background can be chosen per brand for proper contrast.
    logo_settings = profile.get("identity", {}).get("logo", {})
    background = logo_settings.get("preview_background", "#FFFFFF") if isinstance(logo_settings, dict) else "#FFFFFF"
    c.setFillColor(_rgb(background))
    c.roundRect(w - 228, h - 197, 180, 110, 10, fill=1, stroke=0)
    if logo_img:
        _draw_logo(c, logo_img, w - 210, h - 179, 145, 75)
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
    _line(c, 44, h - 593, "Przykładowy nagłówek zgodny z identyfikacją marki.",
          font=regular, size=10)
    _line(c, 44, h - 630,
          "Podgląd korzysta z lokalnego fontu PDF; nazwa fontu marki jest rekomendacją.",
          font=regular, size=8, ink="#687981", limit=110)
    _page_bottom(c, 1, regular, draft=draft)
    c.showPage()

    # Page 2 — aspect-ratio independent applications of the visual identity.
    # Neither sizes nor platform-specific safe areas belong in a brandbook.
    _line(c, 44, h - 62, "03   ZASTOSOWANIE IDENTYFIKACJI", font=bold, size=14)
    _block(c, "Ta sama identyfikacja działa niezależnie od wielkości "
           "i proporcji materiału. Kolory, logo i typografia pozostają wspólne.",
           44, h - 91, w - 88, font=regular, size=10, max_lines=3)

    # Two wide, format-neutral style swatches—not fixed-aspect-ratio video mockups.
    card_width = (w - 100) / 2
    x_light, x_dark = 44, 56 + card_width
    card_y, card_h = h - 370, 208
    c.setFillColor(_rgb(str(palette.get("background", "#FFFFFF"))))
    c.roundRect(x_light, card_y, card_width, card_h, 9, fill=1, stroke=0)
    c.setStrokeColor(_rgb("#DDE3E3"))
    c.roundRect(x_light, card_y, card_width, card_h, 9, fill=0, stroke=1)
    c.setFillColor(_rgb(neutral_dark))
    c.roundRect(x_dark, card_y, card_width, card_h, 9, fill=1, stroke=0)
    dark_logo_rel = profile.get("branding", {}).get("logo_dark_bg")
    dark_logo_img = ((Path(assets_root) / dark_logo_rel).resolve()
                     if dark_logo_rel and assets_root and (Path(assets_root) / dark_logo_rel).is_file()
                     else logo_img)
    light_preview = str(background).upper() in ("#FFFFFF", "#F7F5FB", "#FFF9F1")
    for x, dark_mode in ((x_light, False), (x_dark, True)):
        c.setFillColor(_rgb(accent))
        c.roundRect(x + 20, card_y + card_h - 40, 45, 4, 2, fill=1, stroke=0)
        fg = "#FFFFFF" if dark_mode else str(palette.get("ink", "#14221A"))
        sub = "#E0E4EC" if dark_mode else "#43525A"
        _line(c, x + 20, card_y + card_h - 73, name, font=bold,
              size=14, ink=fg, limit=21)
        _line(c, x + 20, card_y + card_h - 97, "Spójny styl marki",
              font=regular, size=10, ink=sub, limit=26)
        if dark_mode and dark_logo_img:
            _draw_logo(c, dark_logo_img, x + 20, card_y + 58,
                       card_width - 40, 42)
        elif (not dark_mode) and light_preview and logo_img:
            _draw_logo(c, logo_img, x + 20, card_y + 58,
                       card_width - 40, 42)
        _line(c, x + 20, card_y + 35,
              "WARIANT CIEMNY" if dark_mode else "WARIANT JASNY",
              font=bold, size=9, ink=sub)

    _line(c, 44, h - 402, "Wspólne: paleta, krój pisma, logo i zasady komunikacji.",
          font=regular, size=10)
    _line(c, 44, h - 424, "Układ, rozdzielczość i kadrowanie ustala osobny projekt.",
          font=regular, size=10, ink="#687981")

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
        "Publikacja: sprawdź kontrast i czytelność w docelowym medium.",
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


def generate_brandbook(slug: str, root: Path, output: Path | None = None) -> dict:
    """Stable CLI adapter for the printable two-page brandbook implementation."""
    from .brand import brand_directory
    from .spec import ProjectError

    directory = brand_directory(slug, root)
    try:
        profile = saved_brandbook_data(directory)
    except ValueError as exc:
        raise ProjectError(str(exc)) from exc
    if profile.get("id") != slug:
        raise ProjectError(f"brand.json must declare id={slug!r}")
    filename = (Path(output) if output else
                Path(root).resolve() / "renders" / slug / "brandbook.pdf")
    if filename.suffix.lower() != ".pdf":
        raise ProjectError("Brandbook output must end with .pdf")
    output_path = make_brandbook(profile, filename, assets_root=directory)
    return {
        "brand": slug,
        "output": str(output_path.resolve()),
        "source": str(directory / "brand.json"),
        "pages": 2,
        "logo_included": _preview_image(profile, directory) is not None,
        "preferred_font": str(_fonts_from(profile).get("primary", "")),
    }


