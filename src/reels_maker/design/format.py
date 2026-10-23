"""Deterministic number formatting shared by components, renderers and QA."""
from __future__ import annotations

from typing import Mapping


def format_value(value: float, fmt: Mapping | None = None) -> str:
    """Format a number with Polish thousands spacing and explicit suffixes."""
    fmt = dict(fmt or {})
    decimals = int(fmt.get("decimals", 0))
    if decimals < 0 or decimals > 6:
        raise ValueError("decimals must be between 0 and 6")
    prefix = str(fmt.get("prefix", ""))
    suffix = str(fmt.get("suffix", ""))
    separator = str(fmt.get("thousands", " "))
    number = f"{float(value):,.{decimals}f}"
    if separator != ",":
        number = number.replace(",", separator)
    return f"{prefix}{number}{suffix}"
