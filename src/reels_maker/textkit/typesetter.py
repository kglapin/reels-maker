"""Premium text typesetting: real font metrics, balanced wrapping and runs.

The typesetter measures every token before any frame is rendered. It protects
numbers and units from being split, supports Polish diacritics through real
TrueType fonts, and returns word-level geometry so kinetic typography can
animate words without re-measuring text per frame.
"""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Mapping

from PIL import ImageFont
from .models import Line, Run, TextBlock, TextStyle, Word

NBSP = "\u00a0"
UNIT_PROTECTION = re.compile(
    r"(?<=\d)[ \u00a0]+(?=(?:zł|pln|%|kW|kWh|kWp|m2|m²|lat|dni|godzin|godz\.?))",
    re.IGNORECASE)
THOUSANDS = re.compile(r"(?<=\d)[ \u00a0](?=\d{3}(?!\d))")
DATE = re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b")
WORD = re.compile(r"[^ \t]+")


class TextOverflow(ValueError):
    """Raised when copy cannot fit without violating a hard constraint."""


DEFAULT_CANDIDATES = {
    "regular": [
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/open-sans/OpenSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ],
    "bold": [
        "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/open-sans/OpenSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ],
}

FAMILY_CANDIDATES = {
    "opensans": {
        "regular": ["OpenSans-Regular.ttf",
                    "/usr/share/fonts/truetype/open-sans/OpenSans-Regular.ttf",
                    "/Library/Fonts/OpenSans-Regular.ttf",
                    str(Path.home() / "Library/Fonts/OpenSans-Regular.ttf")],
        "bold": ["OpenSans-Bold.ttf",
                 "/usr/share/fonts/truetype/open-sans/OpenSans-Bold.ttf",
                 "/Library/Fonts/OpenSans-Bold.ttf",
                 str(Path.home() / "Library/Fonts/OpenSans-Bold.ttf")],
    },
    "inter": {
        "regular": ["Inter-Regular.ttf",
                    "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
                    str(Path.home() / "Library/Fonts/Inter-Regular.ttf")],
        "bold": ["Inter-Bold.ttf",
                 "/usr/share/fonts/truetype/inter/Inter-Bold.ttf",
                 str(Path.home() / "Library/Fonts/Inter-Bold.ttf")],
    },
}


@dataclass
class FontBook:
    """Resolve and cache real font files for consistent metrics."""
    regular: str | None = None
    bold: str | None = None
    family: str | None = None
    extra_dirs: tuple[str, ...] = ()
    _cache: dict = field(default_factory=dict, repr=False)

    def _candidates(self, weight: str) -> list[str]:
        result: list[str] = []
        explicit = self.bold if weight == "bold" else self.regular
        if explicit:
            result.append(explicit)
        family = (self.family or "").lower().replace(" ", "")
        if family in FAMILY_CANDIDATES:
            result.extend(FAMILY_CANDIDATES[family][weight])
        elif self.family:
            # Any installed "<Family>-<Weight>.ttf" (e.g. a Google Fonts
            # download in ~/Library/Fonts) resolves by family name alone.
            stem = (f'{self.family.replace(" ", "")}-'
                    f'{"Bold" if weight == "bold" else "Regular"}.ttf')
            result.extend([
                str(Path.home() / "Library/Fonts" / stem),
                f"/Library/Fonts/{stem}",
                stem,
            ])
        for directory in self.extra_dirs:
            result.extend(str(path) for path in
                          sorted(Path(directory).glob("*.tt[fc]")))
            result.extend(str(path) for path in
                          sorted(Path(directory).glob("*.otf")))
        result.extend(DEFAULT_CANDIDATES[weight])
        return result

    def path(self, weight: str = "regular") -> str:
        if weight not in ("regular", "bold"):
            raise ValueError("Font weight must be regular or bold")
        cache_key = f"path:{weight}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        for candidate in self._candidates(weight):
            if not candidate:
                continue
            if os.path.isfile(candidate):
                self._cache[cache_key] = candidate
                return candidate
        raise RuntimeError(
            "No TrueType font available. Install DejaVu Sans, Open Sans or set "
            "branding.font_regular/branding.font_bold to a real .ttf file.")

    def get(self, size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
        if weight not in ("regular", "bold"):
            raise ValueError("Font weight must be regular or bold")
        if type(size) is not int or not 6 <= size <= 1000:
            raise ValueError("Font size must be an integer between 6 and 1000")
        key = ("font", weight, size)
        if key not in self._cache:
            path = self.path(weight)
            self._cache[key] = ImageFont.truetype(path, size)
        return self._cache[key]


def normalise_copy(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("Text must be a string")
    value = text.replace("\r\n", "\n").replace("\r", "\n")
    # Keep amounts, dates and units together through line breaking.
    value = THOUSANDS.sub(NBSP, value)
    value = UNIT_PROTECTION.sub(NBSP, value)
    value = DATE.sub(lambda match: match.group(0).replace(" ", NBSP), value)
    return value


def _token_width(font: ImageFont.FreeTypeFont, text: str, tracking: float) -> float:
    if not text:
        return 0.0
    return float(font.getlength(text)) + tracking * max(0, len(text) - 1)


def _wrap_paragraph(paragraph: str, font, max_width: float,
                    tracking: float) -> list[list[str]]:
    words = [token for token in WORD.findall(paragraph) if token.strip()]
    if not words:
        return []
    lines: list[list[str]] = []
    current: list[str] = []
    for word in words:
        trial = current + [word]
        width = max(0.0, _token_width(font, " ".join(trial), tracking))
        if width <= max_width or not current:
            # A single unbreakable word may be wider than the column. Keep it
            # on its own line and let fit_text shrink the type; raising here
            # would make long Polish compounds impossible to typeset at hero
            # sizes even when a smaller, still-legible size would fit.
            current = trial
        else:
            lines.append(current)
            current = [word]
    if current:
        lines.append(current)
    return lines


def _balance_lines(paragraph: str, font, max_width: float,
                   tracking: float) -> list[list[str]]:
    """Minimize raggedness for short display copy (dynamic programming)."""
    greedy = _wrap_paragraph(paragraph, font, max_width, tracking)
    if len(greedy) < 2 or len(greedy) > 4:
        return greedy
    words = [token for token in WORD.findall(paragraph)]
    target_lines = len(greedy)
    memo: dict[tuple[int, int], tuple[float, list[list[str]]] | None] = {}

    def solve(start: int, lines_left: int):
        key = (start, lines_left)
        if key in memo:
            return memo[key]
        if lines_left == 1:
            chunk = words[start:]
            width = _token_width(font, " ".join(chunk), tracking)
            result = ((width - max_width) ** 2 if width <= max_width else math.inf,
                      [chunk])
            memo[key] = result
            return result
        best_cost, best_lines = math.inf, None
        for end in range(start + 1, len(words) - lines_left + 2):
            chunk = words[start:end]
            width = _token_width(font, " ".join(chunk), tracking)
            if width > max_width:
                break
            tail = solve(end, lines_left - 1)
            if tail is None or not math.isfinite(tail[0]):
                continue
            slack = max_width - width
            cost = tail[0] + slack * slack
            if cost < best_cost:
                best_cost, best_lines = cost, [chunk] + tail[1]
        if best_lines is None or not math.isfinite(best_cost):
            memo[key] = None
            return None
        memo[key] = (best_cost, best_lines)
        return memo[key]

    result = solve(0, target_lines)
    return result[1] if result is not None else greedy


def typeset(text: str, style: TextStyle, max_width: float,
            fonts: FontBook, *, force_lines: int | None = None) -> TextBlock:
    """Lay out a single-style paragraph block with word-level geometry."""
    if max_width <= 0:
        raise ValueError("Text column must have positive width")
    source = normalise_copy(text).strip()
    if style.uppercase:
        source = source.upper()
    if not source:
        return TextBlock((), 0.0, 0.0, style, "")
    font = fonts.get(style.size, style.weight)
    font_path = fonts.path(style.weight)
    paragraphs = source.split("\n")
    line_groups: list[tuple[list[str], int]] = []
    for run_index, paragraph in enumerate(paragraphs):
        if not paragraph.strip():
            line_groups.append(([], run_index))
            continue
        wrapped = (_balance_lines(paragraph, font, max_width, style.tracking)
                   if style.balance else
                   _wrap_paragraph(paragraph, font, max_width, style.tracking))
        for group in wrapped:
            line_groups.append((group, 0))
    lines: list[Line] = []
    y = 0
    max_seen = 0.0
    for group, _run in line_groups:
        if not group:
            ascent, descent = font.getmetrics()
            height = round(style.size * style.line_height)
            lines.append(Line((), 0.0, ascent, descent, y + ascent, height))
            y += height
            continue
        widths = [_token_width(font, word, style.tracking) for word in group]
        space = _token_width(font, " ", style.tracking)
        width = sum(widths) + space * (len(group) - 1)
        max_seen = max(max_seen, width)
        if style.align == "center":
            x = (max_width - width) / 2
        elif style.align == "right":
            x = max_width - width
        else:
            x = 0.0
        ascent, descent = font.getmetrics()
        height = round(max(style.size * style.line_height, ascent + descent))
        words = []
        for word, word_width in zip(group, widths):
            words.append(Word(word, x, word_width, font_path, 0,
                              style.color, 0, style.tracking, style.size,
                              style.weight))
            x += word_width + space
        lines.append(Line(tuple(words), width, ascent, descent, y + ascent,
                          height))
        y += height
    overflow = any(line.width > max_width + .5 for line in lines)
    truncated = False
    if style.max_lines is not None and len(lines) > style.max_lines:
        lines = lines[:style.max_lines]
        truncated = True
        y = sum(line.height for line in lines)
    return TextBlock(tuple(lines), max_seen, float(y), style, source,
                     overflow, truncated)


def _balance_lines_to(paragraph: str, font, max_width: float,
                      style: TextStyle, lines: int, fonts: FontBook):
    """Force a specific line count only when it actually fits."""
    words = [token for token in WORD.findall(paragraph) if token.strip()]
    if not words or lines < 1 or lines > len(words):
        return None
    best_cost, best_split = math.inf, None
    for cuts in _compositions(len(words), lines):
        groups = []
        previous = 0
        for cut in cuts:
            groups.append(words[previous:cut])
            previous = cut
        groups.append(words[previous:])
        widths = [_token_width(font, " ".join(group), style.tracking)
                  for group in groups]
        if any(width > max_width for width in widths):
            continue
        cost = sum((max_width - width) ** 2 for width in widths)
        if cost < best_cost:
            best_cost, best_split = cost, groups
    return best_split


def _compositions(total: int, parts: int):
    if parts == 1:
        yield ()
        return
    for first in range(1, total - parts + 2):
        for rest in _compositions(total - first, parts - 1):
            yield (first,) + tuple(first + item for item in rest)


def typeset_runs(runs: Iterable[Run], style: TextStyle, max_width: float,
                 fonts: FontBook) -> TextBlock:
    """Mixed-size rich headline on a shared baseline per line."""
    run_list = list(runs)
    if not run_list:
        raise ValueError("At least one text run is required")
    # Build token records: (text, font, color, run index, break-before).
    tokens = []
    for index, run in enumerate(run_list):
        size = max(6, round(style.size * run.scale))
        if run.effect == "negative" and size < 32:
            raise ValueError(
                "Negative text requires a rendered font size of at least 32px")
        if run.break_before:
            tokens.append(("\n", None, None, index, size, run.weight))
        font = fonts.get(size, run.weight)
        source = normalise_copy(run.text)
        if style.uppercase:
            source = source.upper()
        for paragraph_index, paragraph in enumerate(source.split("\n")):
            if paragraph_index:
                tokens.append(("\n", None, None, index, size, run.weight))
            for token in WORD.findall(paragraph):
                tokens.append((token, font, run.color, index, size, run.weight))
    rows: list[list[tuple]] = []
    current: list[tuple] = []
    x = 0.0
    space_width = _token_width(fonts.get(style.size, "bold"), " ", style.tracking)
    for token, font, color, run_index, size, weight in tokens:
        if token == "\n":
            if current:
                rows.append(current)
            current, x = [], 0.0
            continue
        if not token.strip():
            continue
        width = _token_width(font, token, style.tracking)
        if width > max_width and not current:
            raise TextOverflow(f"Word too wide for headline: {token!r}")
        if x + width > max_width and current:
            while current and current[-1][0].isspace():
                current.pop()
            rows.append(current)
            current, x = [], 0.0
        if current and not current[-1][0].isspace():
            current.append((" ", font, color, run_index, size, weight))
            x += space_width
        current.append((token, font, color, run_index, size, weight))
        x += width
    if current:
        rows.append(current)
    if not rows:
        raise ValueError("Rich headline resolved to no visible text")
    placed: list[Line] = []
    y = 0
    max_seen = 0.0
    for row in rows:
        visible = [item for item in row if not item[0].isspace()]
        if not visible:
            continue
        widths_with_space = []
        running = 0.0
        for item in row:
            width = (_token_width(item[1], item[0], style.tracking)
                     if not item[0].isspace() else space_width)
            widths_with_space.append((item, running, width))
            running += width
        row_width = running
        max_seen = max(max_seen, row_width)
        if style.align == "center":
            offset = max(0.0, (max_width - row_width) / 2)
        elif style.align == "right":
            offset = max(0.0, max_width - row_width)
        else:
            offset = 0.0
        ascent = max(item[1].getmetrics()[0] for item in visible)
        descent = max(item[1].getmetrics()[1] for item in visible)
        height = max(round(style.size * style.line_height), ascent + descent)
        words = []
        path = fonts.path("bold")
        for item, position, width in widths_with_space:
            if item[0].isspace():
                continue
            words.append(Word(item[0], offset + position, width,
                              item[1].path if hasattr(item[1], "path") else path,
                              0, item[2], item[3], style.tracking,
                              item[4], item[5], run_list[item[3]].effect))
        placed.append(Line(tuple(words), row_width, ascent, descent,
                           y + ascent, height))
        y += height
    overflow = max_seen > max_width + .5
    if style.max_lines is not None and len(placed) > style.max_lines:
        placed = placed[:style.max_lines]
        y = sum(line.height for line in placed)
    return TextBlock(tuple(placed), max_seen, float(y), style,
                     " ".join(run.text for run in run_list), overflow,
                     len(placed) < len(rows), len(run_list))


def fit_text(text: str, style: TextStyle, max_width: float, max_height: float,
             fonts: FontBook, *, min_scale: float = .42,
             step: float = .94) -> tuple[TextBlock, TextStyle]:
    """Shrink type until the block fits both the column and the height."""
    current = style
    while True:
        block = typeset(text, current, max_width, fonts)
        if block.height <= max_height and not block.overflow:
            return block, current
        next_size = max(6, int(current.size * step))
        if next_size >= current.size or next_size < round(style.size * min_scale):
            raise TextOverflow(
                f"Copy does not fit {max_width:.0f}x{max_height:.0f}px: {text[:48]!r}")
        current = replace(current, size=next_size)


def digits_width(font: ImageFont.FreeTypeFont, text: str) -> float:
    """Width using the widest digit for every numeric character (tabular)."""
    if not text:
        return 0.0
    widest = max((font.getlength(str(digit)) for digit in "0123456789"),
                 default=0.0)
    return sum(widest if character.isdigit() else font.getlength(character)
               for character in text)


def balanced_column(width: float, ratio: float = .82) -> float:
    """Readable measure relative to the available width.

    Display copy should not run edge-to-edge on wide canvases; the minimum is
    expressed in design units so it never becomes fewer than a few words.
    """
    if width <= 0:
        raise ValueError("Width must be positive")
    return max(min(width, 420), width * ratio)
