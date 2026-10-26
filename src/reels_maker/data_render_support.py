"""Shared validation contracts for typed data-to-scene compilers."""
from __future__ import annotations

from decimal import Decimal
import math

class DataRenderError(ValueError):
    """Invalid typed data, selected visualization, or explicit axis contract."""

def _exact_float(value: object, *, row_index: int, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise DataRenderError(f"row {row_index} {label} is not numeric")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise DataRenderError(f"row {row_index} {label} must be finite")
    if isinstance(value, Decimal) and Decimal(str(numeric)) != value:
        raise DataRenderError(
            f"row {row_index} {label} cannot be represented exactly by renderer"
        )
    if type(value) is int and int(numeric) != value:
        raise DataRenderError(
            f"row {row_index} {label} integer exceeds exact renderer precision"
        )
    return numeric
