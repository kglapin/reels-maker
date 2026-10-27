"""Typed values shared by text measurement and rendering."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TextStyle:
    size: int
    color: tuple[int, int, int] = (255, 255, 255)
    weight: str = "regular"
    line_height: float = 1.1
    tracking: float = 0.0
    align: str = "left"
    uppercase: bool = False
    max_lines: int | None = None
    balance: bool = False
    tabular: bool = False
    opacity: float = 1.0

    def __post_init__(self) -> None:
        if type(self.size) is not int or self.size < 6 or self.size > 1000:
            raise ValueError("Text size must be an integer between 6 and 1000")
        if self.weight not in ("regular", "bold"):
            raise ValueError("Font weight must be regular or bold")
        if self.align not in ("left", "center", "right"):
            raise ValueError("Text align must be left, center or right")
        if not .8 <= self.line_height <= 2.0:
            raise ValueError("Line height must be between 0.8 and 2.0")
        if not -5 <= self.tracking <= 40:
            raise ValueError("Tracking must be between -5 and 40")
        if not 0 <= self.opacity <= 1:
            raise ValueError("Text opacity must be between 0 and 1")


@dataclass(frozen=True)
class Word:
    text: str
    x: float
    width: float
    font_path: str
    font_index: int
    color: tuple[int, int, int]
    run: int = 0
    tracking: float = 0.0
    size: int = 0
    weight: str = "regular"
    effect: str | None = None


@dataclass(frozen=True)
class Line:
    words: tuple[Word, ...]
    width: float
    ascent: int
    descent: int
    baseline: int
    height: int


@dataclass(frozen=True)
class TextBlock:
    lines: tuple[Line, ...]
    width: float
    height: float
    style: TextStyle
    text: str
    overflow: bool = False
    truncated: bool = False
    run_count: int = 1


@dataclass(frozen=True)
class Run:
    text: str
    scale: float = 1.0
    color: tuple[int, int, int] = (255, 255, 255)
    weight: str = "bold"
    break_before: bool = False
    effect: str | None = None

    def __post_init__(self) -> None:
        if self.effect not in (None, "negative"):
            raise ValueError("Rich-text effect must be 'negative' or omitted")
        if self.effect == "negative":
            word = self.text.strip()
            if (not math.isfinite(self.scale) or len(word.split()) != 1
                    or len(word) > 18
                    or self.weight != "bold" or self.scale < 1.08):
                raise ValueError(
                    "Negative text is limited to one word (max 18 chars), "
                    "bold weight and scale >= 1.08")
