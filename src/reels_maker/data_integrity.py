"""Fail-closed validation and auditable Decimal calculations for loaded data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import (
    Decimal,
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
)
from typing import Literal

from .data_sources import LoadedData, RightsProvenance, _validate_schema


class DataIntegrityError(ValueError):
    """Input data or a requested calculation is incomplete or inconsistent."""


RoundingPolicy = Literal[
    "half_up", "half_down", "half_even", "up", "down", "ceiling", "floor"
]
Aggregation = Literal["sum", "mean"]

_ROUNDING = {
    "half_up": ROUND_HALF_UP,
    "half_down": ROUND_HALF_DOWN,
    "half_even": ROUND_HALF_EVEN,
    "up": ROUND_UP,
    "down": ROUND_DOWN,
    "ceiling": ROUND_CEILING,
    "floor": ROUND_FLOOR,
}


@dataclass(frozen=True)
class LedgerEntry:
    source_path: str
    source_sha256: str
    operation: str
    input_columns: tuple[str, ...]
    row_count: int
    exact_value: Decimal
    rounded_value: Decimal
    decimal_places: int
    rounding_policy: RoundingPolicy
    unit: str
    currency: str
    period: str


@dataclass(frozen=True)
class CalculationResult:
    exact_value: Decimal
    value: Decimal
    unit: str
    currency: str
    period: str
    ledger: LedgerEntry


def validate_loaded_data(data: LoadedData) -> None:
    """Check structural integrity without changing or imputing source values."""
    if not isinstance(data, LoadedData):
        raise DataIntegrityError("data must be a LoadedData instance")
    if not isinstance(data.rights, RightsProvenance):
        raise DataIntegrityError("loaded data must record typed rights provenance")
    if data.rights.authorized is not True:
        raise DataIntegrityError("loaded data does not have explicit authorization")
    try:
        _validate_schema(data.schema, data.rights)
    except ValueError as exc:
        raise DataIntegrityError(f"loaded schema/provenance is invalid: {exc}") from exc
    if not data.source_path or not isinstance(data.source_path, str):
        raise DataIntegrityError("loaded data must record its source path")
    if not isinstance(data.sha256, str) or len(data.sha256) != 64 or any(
        char not in "0123456789abcdef" for char in data.sha256.lower()
    ):
        raise DataIntegrityError("loaded data must record a 64-character SHA-256 checksum")
    if not data.rows:
        raise DataIntegrityError("loaded data has no rows")
    columns = {column.name: column for column in data.schema.columns}
    for index, row in enumerate(data.rows, 1):
        if not isinstance(row, dict) or set(row) != set(columns):
            raise DataIntegrityError(f"row {index}: keys do not match the declared schema")
        for name, column in columns.items():
            value = row[name]
            if value is None and column.missing_policy != "null":
                raise DataIntegrityError(f"row {index}, column {name!r}: unexpected null")
            if value is None:
                continue
            if column.data_type == "string" and not isinstance(value, str):
                raise DataIntegrityError(f"row {index}, column {name!r}: expected string")
            if column.data_type == "string" and not value.strip():
                raise DataIntegrityError(f"row {index}, column {name!r}: blank string is ambiguous")
            if column.data_type == "integer" and (type(value) is not int):
                raise DataIntegrityError(f"row {index}, column {name!r}: expected integer")
            if column.data_type == "boolean" and type(value) is not bool:
                raise DataIntegrityError(f"row {index}, column {name!r}: expected boolean")
            if column.data_type == "date" and (
                not isinstance(value, date) or isinstance(value, datetime)
            ):
                raise DataIntegrityError(f"row {index}, column {name!r}: expected date")
            if column.data_type == "decimal":
                if not isinstance(value, Decimal) or not value.is_finite():
                    raise DataIntegrityError(f"row {index}, column {name!r}: expected finite Decimal")


def aggregate(
    data: LoadedData,
    *,
    column: str,
    operation: Aggregation,
    period: str,
    currency: str,
    decimal_places: int,
    rounding_policy: RoundingPolicy,
) -> CalculationResult:
    """Sum/average one declared decimal column, requiring all metadata explicitly."""
    validate_loaded_data(data)
    if not isinstance(period, str) or not period.strip():
        raise DataIntegrityError("period must be explicitly provided")
    if not isinstance(decimal_places, int) or isinstance(decimal_places, bool) or decimal_places < 0:
        raise DataIntegrityError("decimal_places must be a non-negative integer")
    if rounding_policy not in _ROUNDING:
        raise DataIntegrityError(f"unsupported rounding policy: {rounding_policy!r}")
    if operation not in ("sum", "mean"):
        raise DataIntegrityError(f"unsupported aggregation: {operation!r}")

    spec = next((item for item in data.schema.columns if item.name == column), None)
    if spec is None:
        raise DataIntegrityError(f"unknown column: {column!r}")
    if spec.data_type not in ("decimal", "integer"):
        raise DataIntegrityError(f"column {column!r} is not numeric")
    if currency != data.schema.currency or (spec.currency is not None and currency != spec.currency):
        raise DataIntegrityError("requested currency must exactly match the declared column and dataset currency")

    values: list[Decimal] = []
    for index, row in enumerate(data.rows, 1):
        raw = row[column]
        if raw is None:
            raise DataIntegrityError(f"row {index}, column {column!r}: null cannot be aggregated")
        value = Decimal(raw)
        if not value.is_finite():
            raise DataIntegrityError(f"row {index}, column {column!r}: non-finite value")
        values.append(value)
    if not values:
        raise DataIntegrityError("cannot aggregate an empty value set")

    # Decimal addition is exact for typical financial inputs; use an explicit
    # precision large enough for all input coefficients and the row count.
    from decimal import localcontext

    highest = max(v.adjusted() for v in values if v != 0) if any(v != 0 for v in values) else 0
    lowest = min(v.as_tuple().exponent for v in values)
    precision = max(28, highest - lowest + len(str(len(values))) + 4)
    with localcontext() as context:
        context.prec = precision
        total = sum(values, Decimal(0))
        exact = total if operation == "sum" else total / Decimal(len(values))
        quantum = Decimal(1).scaleb(-decimal_places)
        rounded = exact.quantize(quantum, rounding=_ROUNDING[rounding_policy])

    ledger = LedgerEntry(
        source_path=data.source_path,
        source_sha256=data.sha256,
        operation=operation,
        input_columns=(column,),
        row_count=len(values),
        exact_value=exact,
        rounded_value=rounded,
        decimal_places=decimal_places,
        rounding_policy=rounding_policy,
        unit=spec.unit,
        currency=currency,
        period=period,
    )
    return CalculationResult(exact, rounded, spec.unit, currency, period, ledger)


def divide(
    numerator: Decimal,
    denominator: Decimal,
    *,
    numerator_unit: str,
    denominator_unit: str,
    output_unit: str,
    currency: str,
    period: str,
    decimal_places: int,
    rounding_policy: RoundingPolicy,
) -> Decimal:
    """Divide explicitly dimensioned values; no unit or percentage conversion is inferred."""
    for label, unit in (("numerator_unit", numerator_unit), ("denominator_unit", denominator_unit),
                        ("output_unit", output_unit), ("currency", currency), ("period", period)):
        if not isinstance(unit, str) or not unit.strip():
            raise DataIntegrityError(f"{label} must be explicitly provided")
    if not isinstance(numerator, Decimal) or not numerator.is_finite():
        raise DataIntegrityError("numerator must be a finite Decimal")
    if not isinstance(denominator, Decimal) or not denominator.is_finite():
        raise DataIntegrityError("denominator must be a finite Decimal")
    if denominator == 0:
        raise DataIntegrityError("denominator must not be zero")
    if not isinstance(decimal_places, int) or isinstance(decimal_places, bool) or decimal_places < 0:
        raise DataIntegrityError("decimal_places must be a non-negative integer")
    if rounding_policy not in _ROUNDING:
        raise DataIntegrityError(f"unsupported rounding policy: {rounding_policy!r}")
    from decimal import localcontext

    with localcontext() as context:
        context.prec = max(28, len(numerator.as_tuple().digits) + len(denominator.as_tuple().digits) + decimal_places + 8)
        return (numerator / denominator).quantize(
            Decimal(1).scaleb(-decimal_places), rounding=_ROUNDING[rounding_policy]
        )
