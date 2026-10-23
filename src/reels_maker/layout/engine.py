"""Constraint-based composition regions.

Components measure their own content, then ask the layout engine for regions.
Recipes allocate intrinsic heights first and give the remaining space to the
visual or data area. Nothing is positioned with hard-coded 360/805-style
coordinates, and every recipe respects the same safe rectangle.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from ..core.scene_graph import BBox, boxes_overlap, intersect_boxes
from ..design.tokens import DesignTokens


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def center_x(self) -> float:
        return self.x + self.w / 2

    @property
    def center_y(self) -> float:
        return self.y + self.h / 2

    @property
    def area(self) -> float:
        return max(0.0, self.w) * max(0.0, self.h)

    @property
    def bbox(self) -> BBox:
        return (self.x, self.y, self.right, self.bottom)

    def inset(self, left: float = 0, top: float | None = None,
              right: float | None = None, bottom: float | None = None) -> "Rect":
        top = left if top is None else top
        right = left if right is None else right
        bottom = top if bottom is None else bottom
        return Rect(self.x + left, self.y + top,
                    max(0.0, self.w - left - right),
                    max(0.0, self.h - top - bottom))

    def split_h(self, ratio: float, gap: float = 0) -> tuple["Rect", "Rect"]:
        if not 0 < ratio < 1:
            raise ValueError("Split ratio must be between 0 and 1")
        width = (self.w - gap) * ratio
        return (Rect(self.x, self.y, width, self.h),
                Rect(self.x + width + gap, self.y, self.w - width - gap, self.h))

    def split_v(self, ratio: float, gap: float = 0) -> tuple["Rect", "Rect"]:
        if not 0 < ratio < 1:
            raise ValueError("Split ratio must be between 0 and 1")
        height = (self.h - gap) * ratio
        return (Rect(self.x, self.y, self.w, height),
                Rect(self.x, self.y + height + gap, self.w, self.h - height - gap))

    def grid(self, columns: int, rows: int, gap: float) -> list["Rect"]:
        if columns < 1 or rows < 1:
            raise ValueError("Grid requires positive rows and columns")
        cell_w = (self.w - gap * (columns - 1)) / columns
        cell_h = (self.h - gap * (rows - 1)) / rows
        return [Rect(self.x + column * (cell_w + gap),
                     self.y + row * (cell_h + gap), cell_w, cell_h)
                for row in range(rows) for column in range(columns)]

    def align(self, width: float, height: float,
              horizontal: str = "center", vertical: str = "center") -> "Rect":
        if horizontal == "left":
            x = self.x
        elif horizontal == "right":
            x = self.right - width
        elif horizontal == "center":
            x = self.center_x - width / 2
        else:
            raise ValueError("horizontal must be left, center or right")
        if vertical == "top":
            y = self.y
        elif vertical == "bottom":
            y = self.bottom - height
        elif vertical == "center":
            y = self.center_y - height / 2
        else:
            raise ValueError("vertical must be top, center or bottom")
        return Rect(x, y, width, height)

    def clamp(self, width: float, height: float) -> "Rect":
        return Rect(self.x, self.y, min(self.w, width), min(self.h, height))


@dataclass
class LayoutPlan:
    recipe: str
    canvas: Rect
    safe: Rect
    regions: dict[str, Rect]
    notes: list[str] = field(default_factory=list)

    def region(self, name: str) -> Rect:
        if name not in self.regions:
            raise KeyError(f"Layout {self.recipe!r} has no region {name!r}")
        return self.regions[name]

    def optional(self, name: str) -> Rect | None:
        return self.regions.get(name)

    def describe(self) -> dict:
        return {
            "recipe": self.recipe,
            "canvas": [round(v, 1) for v in
                       (self.canvas.x, self.canvas.y, self.canvas.w, self.canvas.h)],
            "safe": [round(v, 1) for v in
                     (self.safe.x, self.safe.y, self.safe.w, self.safe.h)],
            "regions": {name: [round(v, 1) for v in
                               (rect.x, rect.y, rect.w, rect.h)]
                        for name, rect in self.regions.items()},
            "notes": list(self.notes),
        }


def _height(measurements: Mapping[str, tuple[float, float]], role: str,
            fallback: float) -> float:
    value = measurements.get(role)
    return float(value[1]) if value and value[1] > 0 else fallback


def _width(measurements: Mapping[str, tuple[float, float]], role: str,
           fallback: float) -> float:
    value = measurements.get(role)
    return float(value[0]) if value and value[0] > 0 else fallback


class LayoutEngine:
    def __init__(self, width: int, height: int, tokens: DesignTokens):
        if width < 2 or height < 2:
            raise ValueError("Canvas must be at least 2x2 pixels")
        self.width, self.height = width, height
        self.tokens = tokens
        margin, top, bottom = tokens.safe_pixels(width, height)
        self.canvas = Rect(0, 0, width, height)
        self.safe = Rect(margin, top, width - 2 * margin,
                         height - top - bottom)
        self.landscape = width / height >= 1.2
        self.square = .85 <= width / height <= 1.18
        self.gap = tokens.space("md")
        self.notes: list[str] = []

    # ------------------------------------------------------------------ public
    def layout(self, recipe: str,
               measurements: Mapping[str, tuple[float, float]] | None = None,
               *, has_visual: bool = False) -> LayoutPlan:
        measurements = measurements or {}
        recipes = {
            "stack-center": self._stack_center,
            "hero-number": self._hero_number,
            "split-editorial": self._split,
            "full-bleed-type": self._full_bleed_type,
            "data-panel": self._data_panel,
            "comparison": self._comparison,
            "calendar": self._calendar,
            "cta-panel": self._cta,
            "spotlight": self._spotlight,
            "statement": self._statement,
            "timeline": self._timeline,
            "checklist": self._checklist,
            "stat-grid": self._stat_grid,
            "breakdown": self._breakdown,
            "energy-flow": self._energy_flow,
            "quote": self._quote,
        }
        if recipe not in recipes:
            raise ValueError(f"Unknown composition {recipe!r}; choose one of "
                             + ", ".join(sorted(recipes)))
        regions = recipes[recipe](measurements, has_visual)
        plan = LayoutPlan(recipe, self.canvas, self.safe, regions,
                          list(self.notes))
        self._validate(plan)
        return plan

    # ----------------------------------------------------------------- recipes
    def _stack_center(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        kicker = _height(measure, "kicker", self.tokens.type_size("kicker") * 1.4)
        headline = _height(measure, "headline", self.tokens.type_size("title") * 2.2)
        body = _height(measure, "body", self.tokens.type_size("body") * 1.5)
        content = kicker + self.gap + headline + self.gap + body
        top_space = safe.h * (.62 if has_visual else 1.0)
        start = safe.y + max(0, (top_space - content) / 2)
        regions = {
            "kicker": Rect(safe.x, start, safe.w, kicker),
            "headline": Rect(safe.x, start + kicker + self.gap,
                             safe.w, headline),
            "body": Rect(safe.x, start + kicker + self.gap + headline + self.gap,
                         safe.w, body),
        }
        if has_visual:
            regions["visual"] = Rect(
                safe.x, safe.y + safe.h * .64, safe.w, safe.h * .36)
        return regions

    def _hero_number(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        kicker = _height(measure, "kicker", self.tokens.type_size("kicker") * 1.5)
        hero = _height(measure, "headline", self.tokens.type_size("hero") * 1.2)
        subtitle = _height(measure, "body", self.tokens.type_size("subtitle") * 1.4)
        visual_h = safe.h * (.34 if has_visual else 0)
        content_h = kicker + self.gap + hero + self.gap + subtitle
        available = safe.h - visual_h
        start = safe.y + max(self.gap, (available - content_h) * .44)
        regions = {
            "kicker": Rect(safe.x, start, safe.w, kicker),
            "headline": Rect(safe.x, start + kicker + self.gap,
                             safe.w, hero),
            "body": Rect(safe.x, start + kicker + self.gap + hero + self.gap,
                         safe.w, subtitle),
        }
        if has_visual:
            regions["visual"] = Rect(safe.x, safe.bottom - visual_h,
                                     safe.w, visual_h)
        return regions

    def _split(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        kicker = _height(measure, "kicker", self.tokens.type_size("kicker") * 1.4)
        headline = _height(measure, "headline", self.tokens.type_size("title") * 2.4)
        body = _height(measure, "body", self.tokens.type_size("body") * 1.6)
        if self.landscape:
            text, visual = safe.split_h(.52, self.gap * 2)
            regions = {
                "text": text,
                "visual": visual,
                "kicker": Rect(text.x, text.y, text.w, kicker),
                "headline": Rect(text.x, text.y + kicker + self.gap,
                                 text.w, headline),
                "body": Rect(text.x, text.y + kicker + self.gap + headline
                             + self.gap, text.w, body),
            }
        elif has_visual:
            text, visual = safe.split_v(.5, self.gap * 2)
            regions = {
                "text": text,
                "visual": visual,
                "kicker": Rect(text.x, text.y, text.w, kicker),
                "headline": Rect(text.x, text.y + kicker + self.gap,
                                 text.w, headline),
                "body": Rect(text.x, text.y + kicker + self.gap + headline
                             + self.gap, text.w, body),
            }
        else:
            text = safe
            regions = {
                "text": text,
                "kicker": Rect(text.x, text.y, text.w, kicker),
                "headline": Rect(text.x, text.y + kicker + self.gap,
                                 text.w, headline),
                "body": Rect(text.x, text.y + kicker + self.gap + headline
                             + self.gap, text.w, body),
            }
        return regions

    def _full_bleed_type(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        headline = _height(measure, "headline", safe.h * .48)
        body = _height(measure, "body", self.tokens.type_size("body") * 1.5)
        headline_top = safe.y + max(self.gap, (safe.h - headline - body - self.gap) * .18)
        return {
            "headline": Rect(safe.x, headline_top, safe.w, headline),
            "body": Rect(safe.x, safe.bottom - body, safe.w, body),
            "kicker": Rect(safe.x, safe.y, safe.w, self.tokens.type_size("kicker") * 1.4),
        }

    def _data_panel(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        kicker = _height(measure, "kicker", self.tokens.type_size("kicker") * 1.4)
        headline = _height(measure, "headline", self.tokens.type_size("title") * 1.5)
        caption = _height(measure, "body", self.tokens.type_size("body") * 1.4)
        header = kicker + self.gap * .5 + headline
        chart_top = safe.y + header + self.gap * 1.4
        chart_bottom = safe.bottom - caption - self.gap * 1.4
        chart_size = min(safe.w, max(0, chart_bottom - chart_top))
        return {
            "kicker": Rect(safe.x, safe.y, safe.w, kicker),
            "headline": Rect(safe.x, safe.y + kicker + self.gap * .5,
                             safe.w, headline),
            "chart": Rect(safe.center_x - chart_size / 2, chart_top,
                          chart_size, chart_size),
            # Leave a small extra inset for entrance overshoot so transient
            # easing cannot push the caption into the platform UI margin.
            "body": Rect(safe.x, safe.bottom - caption - self.gap * .25,
                         safe.w, caption),
        }

    def _comparison(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        headline = _height(measure, "headline", self.tokens.type_size("title"))
        body = _height(measure, "body", 0)
        reserve = body + self.gap if body else 0
        top_h = min(safe.h * .18, max(headline, self.tokens.type_size("title")))
        top = Rect(safe.x, safe.y, safe.w, top_h)
        rest = Rect(safe.x, top.bottom + self.gap, safe.w,
                    safe.h - top_h - self.gap - reserve)
        columns = rest.grid(2, 1, self.gap)
        regions = {
            "headline": top,
            "column-left": columns[0],
            "column-right": columns[1],
            "visual": rest,
        }
        if body:
            regions["body"] = Rect(safe.x, safe.bottom - body, safe.w, body)
        return regions

    def _calendar(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        kicker_h = self.tokens.type_size("kicker") * 1.4
        headline_y = safe.y + kicker_h + self.gap
        body = _height(measure, "body", self.tokens.type_size("body") * 1.4)
        card_h = min(safe.w * .92, safe.h * .42)
        card_top = safe.y + safe.h * .40
        # The headline owns the space above the calendar card. Clamping the
        # measured height prevents a long first word from pushing copy across
        # the card; fit_text then selects a legible size for that window.
        max_headline = max(self.tokens.type_size("display") * .55,
                           card_top - headline_y - self.gap)
        headline = min(_height(measure, "headline",
                               self.tokens.type_size("title") * 1.4),
                       max_headline)
        return {
            "kicker": Rect(safe.x, safe.y, safe.w, kicker_h),
            "headline": Rect(safe.x, headline_y, safe.w, headline),
            "visual": Rect(safe.center_x - card_h / 2,
                           card_top, card_h, card_h),
            "body": Rect(safe.x, safe.bottom - body, safe.w, body),
        }

    def _cta(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        headline = _height(measure, "headline", self.tokens.type_size("title") * 1.7)
        body = _height(measure, "body", self.tokens.type_size("body") * 1.4)
        card_h = min(safe.h * .30, self.tokens.px(330))
        content_h = headline + self.gap + card_h + self.gap * 2 + body * 2
        start = safe.y + max(0, (safe.h - content_h) * .38)
        return {
            "headline": Rect(safe.x, start, safe.w, headline),
            "cta": Rect(safe.x, start + headline + self.gap * 1.4,
                        safe.w, card_h),
            "body": Rect(safe.x, start + headline + self.gap * 1.4 + card_h
                         + self.gap * 1.4, safe.w, body * 2 + self.gap),
        }

    def _spotlight(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        headline = _height(measure, "headline", self.tokens.type_size("hero") * 1.5)
        body = _height(measure, "body", self.tokens.type_size("body") * 2)
        return {
            "kicker": Rect(safe.x, safe.y, safe.w,
                           self.tokens.type_size("kicker") * 1.4),
            "headline": Rect(safe.x, safe.bottom - body - self.gap * 2 - headline,
                             safe.w, headline),
            "body": Rect(safe.x, safe.bottom - body, safe.w, body),
        }

    def _statement(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        body = min(_height(measure, "body", self.tokens.type_size("body") * 1.4),
                   safe.h * .22)
        headline = min(_height(measure, "headline", safe.h * .5),
                       max(self.tokens.type_size("title"),
                           safe.h - body - self.gap * 2))
        total = headline + self.gap + body
        start = safe.y + max(0.0, (safe.h - total) / 2)
        return {
            "headline": Rect(safe.x, start, safe.w, headline),
            "body": Rect(safe.x, start + headline + self.gap, safe.w, body),
        }

    def _timeline(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        headline = _height(measure, "headline", self.tokens.type_size("title") * 1.4)
        caption = _height(measure, "body", self.tokens.type_size("body") * 1.4)
        header_bottom = safe.y + headline + self.tokens.type_size("kicker") * 2
        return {
            "kicker": Rect(safe.x, safe.y, safe.w, self.tokens.type_size("kicker") * 1.4),
            "headline": Rect(safe.x, safe.y + self.tokens.type_size("kicker") * 1.7,
                             safe.w, headline),
            "timeline": Rect(safe.x, header_bottom + self.gap * 2, safe.w,
                             max(self.gap * 8, safe.h * .28)),
            "body": Rect(safe.x, safe.bottom - caption, safe.w, caption),
        }

    def _checklist(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        headline = _height(measure, "headline", self.tokens.type_size("title") * 1.4)
        return {
            "headline": Rect(safe.x, safe.y, safe.w, headline),
            "list": Rect(safe.x, safe.y + headline + self.gap * 2,
                         safe.w, safe.h - headline - self.gap * 2),
        }

    def _stat_grid(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        headline = _height(measure, "headline", self.tokens.type_size("title") * 1.4)
        rest = Rect(safe.x, safe.y + headline + self.gap * 2, safe.w,
                    safe.h - headline - self.gap * 2)
        cells = rest.grid(2, 2, self.gap)
        return {
            "headline": Rect(safe.x, safe.y, safe.w, headline),
            "stat-1": cells[0], "stat-2": cells[1],
            "stat-3": cells[2], "stat-4": cells[3],
        }

    def _breakdown(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        headline = _height(measure, "headline", self.tokens.type_size("title") * 1.6)
        rows = _height(measure, "rows", safe.h * .32)
        return {
            "kicker": Rect(safe.x, safe.y, safe.w, self.tokens.type_size("kicker") * 1.4),
            "headline": Rect(safe.x, safe.y + self.tokens.type_size("kicker") * 1.7,
                             safe.w, headline),
            "rows": Rect(safe.x, safe.y + safe.h * .54, safe.w, rows),
        }

    def _energy_flow(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        headline = _height(measure, "headline", self.tokens.type_size("title") * 1.5)
        diagram_h = min(safe.w, safe.h * .48)
        return {
            "kicker": Rect(safe.x, safe.y, safe.w, self.tokens.type_size("kicker") * 1.4),
            "headline": Rect(safe.x, safe.y + self.tokens.type_size("kicker") * 1.7,
                             safe.w, headline),
            "diagram": Rect(safe.center_x - diagram_h / 2,
                            safe.y + safe.h * .43, diagram_h, diagram_h),
            "body": Rect(safe.x, safe.bottom - self.tokens.type_size("body") * 1.6,
                         safe.w, self.tokens.type_size("body") * 1.6),
        }

    def _quote(self, measure, has_visual: bool) -> dict[str, Rect]:
        safe = self.safe
        quote = _height(measure, "headline", safe.h * .46)
        body = _height(measure, "body", self.tokens.type_size("body") * 1.4)
        start = safe.y + (safe.h - quote - body - self.gap * 2) / 2
        return {
            "headline": Rect(safe.x, start, safe.w, quote),
            "body": Rect(safe.x, start + quote + self.gap * 2, safe.w, body),
        }

    # ------------------------------------------------------------------ checks
    def _validate(self, plan: LayoutPlan) -> None:
        for name, rect in plan.regions.items():
            if rect.w <= 0 or rect.h <= 0:
                raise ValueError(f"Layout {plan.recipe!r}: empty region {name!r}")
            if not (self.safe.x - 1 <= rect.x
                    and rect.right <= self.safe.right + 1
                    and self.safe.y - 1 <= rect.y
                    and rect.bottom <= self.safe.bottom + 1):
                raise ValueError(
                    f"Layout {plan.recipe!r}: region {name!r} leaves safe area")
        # Intentional overlaps: `visual` always sits behind text; `text` is a
        # container alias. Every other pair of text regions must stay clear.
        containers = {"visual", "text", "list", "rows", "columns", "diagram"}
        text_regions = {name: rect for name, rect in plan.regions.items()
                        if name not in containers}
        names = sorted(text_regions)
        for first in range(len(names)):
            for second in range(first + 1, len(names)):
                a, b = text_regions[names[first]], text_regions[names[second]]
                if boxes_overlap(a.bbox, b.bbox, padding=-1):
                    plan.notes.append(
                        f"Soft overlap: {names[first]} and {names[second]}")
