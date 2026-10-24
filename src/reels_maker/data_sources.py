"""Explicitly typed, local tabular data import with rights provenance."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal


DataType = Literal["string", "integer", "decimal", "boolean", "date"]
MissingPolicy = Literal["reject", "null"]


class DataSourceError(ValueError):
    """Invalid source data, schema, locale, or rights metadata."""


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    data_type: DataType
    unit: str
    missing_policy: MissingPolicy
    missing_tokens: tuple[str, ...] = ()
    currency: str | None = None


@dataclass(frozen=True)
class DataSchema:
    columns: tuple[ColumnSpec, ...]
    locale: Literal["en_US", "pl_PL"]
    # Explicitly use "none" for datasets that are not monetary.
    currency: str


@dataclass(frozen=True)
class RightsProvenance:
    source_title: str
    license_name: str
    license_url: str
    authorization_basis: str
    authorized: bool


@dataclass(frozen=True)
class LoadedData:
    rows: tuple[dict[str, Any], ...]
    schema: DataSchema
    source_path: str
    sha256: str
    rights: RightsProvenance


def _required_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise DataSourceError(f"{label} must be explicitly provided")


def _validate_schema(schema: DataSchema, rights: RightsProvenance) -> None:
    if schema.locale not in ("en_US", "pl_PL"):
        raise DataSourceError("locale must be explicitly supported: en_US or pl_PL")
    _required_text(schema.currency, "schema currency (use 'none' when not applicable)")
    _required_text(rights.source_title, "rights source_title")
    _required_text(rights.license_name, "rights license_name")
    _required_text(rights.license_url, "rights license_url or documented identifier")
    _required_text(rights.authorization_basis, "rights authorization_basis")
    if rights.authorized is not True:
        raise DataSourceError("source authorization must be explicitly true before loading")
    if not schema.columns:
        raise DataSourceError("schema must declare at least one column")
    names = [c.name for c in schema.columns]
    if any(not isinstance(name, str) or not name.strip() for name in names) or len(set(names)) != len(names):
        raise DataSourceError("column names must be non-empty and unique")
    for column in schema.columns:
        _required_text(column.unit, f"unit for column {column.name!r} (use 'none' if not applicable)")
        if column.data_type not in ("string", "integer", "decimal", "boolean", "date"):
            raise DataSourceError(f"unsupported type for column {column.name!r}: {column.data_type!r}")
        if column.missing_policy not in ("reject", "null"):
            raise DataSourceError(f"missing_policy for {column.name!r} must be reject or null")
        if column.missing_policy == "null" and not column.missing_tokens:
            raise DataSourceError(f"column {column.name!r} must declare missing_tokens for null policy")
        if column.data_type == "decimal" and column.currency is None:
            raise DataSourceError(f"decimal column {column.name!r} must declare currency (use 'none' if not applicable)")
        if column.currency is not None and column.currency != schema.currency:
            raise DataSourceError(f"currency for column {column.name!r} conflicts with dataset currency")


def _number(value: Any, locale: str, name: str) -> Decimal:
    if isinstance(value, bool):
        raise DataSourceError(f"{name}: boolean is not a number")
    raw = str(value).strip()
    if not raw:
        raise DataSourceError(f"{name}: empty number")
    decimal_sep, group_sep = (".", ",") if locale == "en_US" else (",", ".")
    if isinstance(value, (int, Decimal)) and not isinstance(value, bool):
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise DataSourceError(f"{name}: invalid decimal {value!r}") from exc
    if "," in raw and "." in raw and locale == "pl_PL" and raw.find(",") < raw.find("."):
        raise DataSourceError(f"{name}: mixed or locale-ambiguous separators in {value!r}")
    # Group separators are accepted only in groups of three; spaces are the
    # documented Polish grouping separator. No currency/unit adornments guessed.
    if locale == "pl_PL" and " " in raw:
        raw = raw.replace("\u00a0", " ")
        integer = raw.split(decimal_sep, 1)[0]
        if " " in integer and not re.fullmatch(r"[+-]?\d{1,3}(?: \d{3})+", integer):
            raise DataSourceError(f"{name}: ambiguous grouped number {value!r}")
        raw = raw.replace(" ", "")
    integer_part = raw.split(decimal_sep, 1)[0]
    if decimal_sep in raw and group_sep in raw.split(decimal_sep, 1)[1]:
        raise DataSourceError(f"{name}: mixed or locale-ambiguous separators in {value!r}")
    if group_sep in integer_part and not re.fullmatch(rf"[+-]?\d{{1,3}}(?:{re.escape(group_sep)}\d{{3}})+", integer_part):
        raise DataSourceError(f"{name}: invalid thousands grouping in {value!r}")
    normalized = raw.replace(group_sep, "").replace(decimal_sep, ".")
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", normalized):
        raise DataSourceError(f"{name}: invalid or locale-ambiguous number {value!r}")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise DataSourceError(f"{name}: invalid decimal {value!r}") from exc


def _convert(value: Any, column: ColumnSpec, schema: DataSchema, row_number: int) -> Any:
    label = f"row {row_number}, column {column.name!r}"
    if value is None or (isinstance(value, str) and value in column.missing_tokens):
        if column.missing_policy == "null":
            return None
        raise DataSourceError(f"{label}: missing value is not allowed")
    if isinstance(value, str) and not value.strip():
        raise DataSourceError(f"{label}: blank value is ambiguous; declare it as a missing token")
    try:
        if column.data_type == "string":
            if not isinstance(value, str):
                raise DataSourceError(f"{label}: expected string")
            return value
        if column.data_type == "decimal":
            return _number(value, schema.locale, label)
        if column.data_type == "integer":
            result = _number(value, schema.locale, label)
            if result != result.to_integral_value():
                raise DataSourceError(f"{label}: expected an integer")
            return int(result)
        if column.data_type == "boolean":
            if value is True or value == "true":
                return True
            if value is False or value == "false":
                return False
            raise DataSourceError(f"{label}: boolean must be true/false")
        if column.data_type == "date":
            if not isinstance(value, str):
                raise DataSourceError(f"{label}: date must use ISO YYYY-MM-DD")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise DataSourceError(f"{label}: date must use ISO YYYY-MM-DD")
            return date.fromisoformat(value)
    except (ValueError, InvalidOperation) as exc:
        if isinstance(exc, DataSourceError):
            raise
        raise DataSourceError(f"{label}: invalid {column.data_type} value {value!r}") from exc
    raise DataSourceError(f"{label}: unsupported type")


def load_data_source(
    path: str | Path,
    *,
    schema: DataSchema,
    rights: RightsProvenance,
    sheet: str | None = None,
) -> LoadedData:
    """Load a local CSV, JSON row array, or XLSX file using only declared facts.

    JSON must be an array of objects with exactly the schema's keys. XLSX uses
    the first row as headers and requires the optional ``openpyxl`` extra.
    """
    _validate_schema(schema, rights)
    try:
        source = Path(path).expanduser().resolve(strict=True)
    except OSError as exc:
        raise DataSourceError(f"source file cannot be resolved: {path}") from exc
    if not source.is_file():
        raise DataSourceError(f"source is not a regular file: {source}")
    suffix = source.suffix.lower()
    raw_rows: list[dict[str, Any]]
    if suffix == ".csv":
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise DataSourceError("CSV must have a header row")
            if reader.fieldnames != [c.name for c in schema.columns]:
                raise DataSourceError("CSV headers/order must exactly match the declared schema")
            raw_rows = list(reader)
    elif suffix == ".json":
        try:
            payload = json.loads(source.read_text(encoding="utf-8"), parse_float=Decimal)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DataSourceError(f"invalid JSON: {exc}") from exc
        if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
            raise DataSourceError("JSON must contain an array of row objects")
        raw_rows = payload
    elif suffix == ".xlsx":
        if not sheet:
            raise DataSourceError("XLSX requires an explicit sheet name")
        try:
            import openpyxl  # type: ignore[import-not-found]
        except ImportError as exc:
            raise DataSourceError("XLSX support requires the optional extra: pip install 'reels-maker[xlsx]'") from exc
        workbook = openpyxl.load_workbook(source, read_only=True, data_only=True)
        try:
            if sheet not in workbook.sheetnames:
                raise DataSourceError(f"XLSX sheet not found: {sheet!r}")
            values = workbook[sheet].iter_rows(values_only=True)
            headers = next(values, None)
            if headers != tuple(c.name for c in schema.columns):
                raise DataSourceError("XLSX headers/order must exactly match the declared schema")
            raw_rows = [dict(zip((c.name for c in schema.columns), row, strict=True)) for row in values]
        finally:
            workbook.close()
    else:
        raise DataSourceError("supported local formats are .csv, .json, and .xlsx")

    if not raw_rows:
        raise DataSourceError("source must contain at least one data row")
    columns = [c.name for c in schema.columns]
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows, 1):
        if set(raw) != set(columns):
            raise DataSourceError(f"row {index}: keys must exactly match the declared schema")
        rows.append({c.name: _convert(raw[c.name], c, schema, index) for c in schema.columns})
    checksum = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    digest = checksum.hexdigest()
    return LoadedData(tuple(rows), schema, str(source), digest, rights)


def snapshot_dataset_version(
    data: LoadedData,
    *,
    snapshot_id: str,
    captured_at: str,
) -> dict:
    """Create an immutable, SHA-256-audited snapshot of a LoadedData dataset (DM-201)."""
    if not isinstance(data, LoadedData):
        raise DataSourceError("data must be a LoadedData instance")
    if not data.rights.authorized:
        raise DataSourceError("Cannot snapshot an unauthorized dataset")
    if not str(snapshot_id or "").strip() or not str(captured_at or "").strip():
        raise DataSourceError("snapshot_id and captured_at are required")
    serialized_rows = [
        {k: (v.isoformat() if hasattr(v, "isoformat") else str(v))
         for k, v in row.items()}
        for row in data.rows
    ]
    payload_bytes = json.dumps(serialized_rows, sort_keys=True, ensure_ascii=False).encode("utf-8")
    content_sha256 = hashlib.sha256(payload_bytes).hexdigest()
    return {
        "schema_version": 1,
        "snapshot_id": str(snapshot_id).strip(),
        "captured_at": str(captured_at).strip(),
        "source_path": data.source_path,
        "source_sha256": data.sha256,
        "content_sha256": content_sha256,
        "row_count": len(serialized_rows),
        "rows": serialized_rows,
        "rights": {
            "license": data.rights.license_name,
            "authorized": data.rights.authorized,
        },
    }


def diff_dataset_snapshots(
    older: dict,
    newer: dict,
    *,
    key_column: str,
    value_column: str,
) -> dict:
    """Compute a deterministic historical comparison between two dataset snapshots (DM-201)."""
    if not isinstance(older, dict) or not isinstance(newer, dict):
        raise DataSourceError("older and newer must be snapshot dicts")
    old_map = {str(r[key_column]): Decimal(str(r[value_column])) for r in older.get("rows", [])}
    new_map = {str(r[key_column]): Decimal(str(r[value_column])) for r in newer.get("rows", [])}
    all_keys = sorted(set(old_map) | set(new_map))
    deltas = []
    for k in all_keys:
        if k in old_map and k in new_map:
            diff = new_map[k] - old_map[k]
            deltas.append({
                "key": k,
                "status": "changed" if diff != 0 else "unchanged",
                "old": str(old_map[k]),
                "new": str(new_map[k]),
                "delta": str(diff),
            })
        elif k in new_map:
            deltas.append({"key": k, "status": "added", "old": None, "new": str(new_map[k]), "delta": None})
        else:
            deltas.append({"key": k, "status": "removed", "old": str(old_map[k]), "new": None, "delta": None})
    return {
        "older_snapshot_id": older.get("snapshot_id"),
        "newer_snapshot_id": newer.get("snapshot_id"),
        "older_sha256": older.get("content_sha256"),
        "newer_sha256": newer.get("content_sha256"),
        "deltas": deltas,
    }
