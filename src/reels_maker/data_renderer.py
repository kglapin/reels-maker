"""Deterministic bridge from authorized typed data plans to Studio line charts.

This is deliberately a narrow first renderer bridge: it supports one explicit
date/category series and requires the caller to approve its numeric domain.
It does not infer units, normalize values, aggregate rows or claim other chart
families are rendered.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import math

from .data_director import VisualizationPlan, VisualizationVariant, _field_label
from .data_integrity import validate_loaded_data
from .data_sources import LoadedData


class DataRenderError(ValueError):
    """Invalid typed data, selected visualization, or explicit axis contract."""


def line_chart_scene(
    data: LoadedData,
    plan: VisualizationPlan,
    *,
    y_domain: tuple[float, float] | list[float],
    duration: float,
    x_axis_label: str | None = None,
    y_axis_label: str | None = None,
    headline: str | None = None,
    variant: int = 0,
) -> dict:
    """Convert one planning-only line recommendation to a validated scene.

    ``variant`` is a zero-based index into the recommendation. Only the explicit
    ``line`` family is implemented by this bridge. Date rows are kept in source
    order and must already be strictly increasing; categorical rows are never
    reordered. Missing values are rejected, never imputed.
    """
    try:
        validate_loaded_data(data)
    except ValueError as exc:
        raise DataRenderError(f"LoadedData failed integrity validation: {exc}") from exc
    if not isinstance(plan, VisualizationPlan):
        raise TypeError("plan must be a VisualizationPlan")
    if plan.source != data.source_path or plan.source_sha256 != data.sha256:
        raise DataRenderError("Visualization plan provenance does not match this dataset")
    if type(variant) is not int or not 0 <= variant < len(plan.variants):
        raise DataRenderError("variant index is outside the recommendation list")
    selected: VisualizationVariant = plan.variants[variant]
    if selected.family != "line":
        raise DataRenderError(
            f"Renderer bridge currently supports line, not {selected.family!r}")
    if selected.missing_fields:
        semantic_missing = [field for field in selected.missing_fields
                            if field not in (
                                "explicit axis labels and y-domain confirmation for renderer")]
        if semantic_missing:
            raise DataRenderError("Recommendation has unresolved required fields: "
                                  + ", ".join(semantic_missing))
    if (isinstance(duration, bool) or not isinstance(duration, (int, float))
            or not math.isfinite(duration) or not .5 <= duration <= 30):
        raise DataRenderError("duration must be finite and between 0.5 and 30 seconds")
    if (not isinstance(y_domain, (tuple, list)) or len(y_domain) != 2
            or any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not math.isfinite(value) for value in y_domain)):
        raise DataRenderError("y_domain must contain two explicit finite numbers")
    low, high = float(y_domain[0]), float(y_domain[1])
    if high <= low:
        raise DataRenderError("y_domain maximum must exceed its minimum")

    x_name, y_name = selected.required_axes
    columns = {column.name: column for column in data.schema.columns}
    x_column, y_column = columns[x_name], columns[y_name]
    if x_column.data_type not in ("date", "string"):
        raise DataRenderError("line x-axis must use a declared date or string column")
    if y_column.data_type not in ("integer", "decimal"):
        raise DataRenderError("line y-axis must use a declared numeric column")
    points = []
    previous_date = None
    for row_index, row in enumerate(data.rows):
        x_value, y_value = row[x_name], row[y_name]
        if x_value is None or y_value is None:
            raise DataRenderError(
                f"row {row_index} contains a missing value on a required chart axis")
        if x_column.data_type == "date":
            if not isinstance(x_value, (date, datetime)):
                raise DataRenderError(f"row {row_index} date value is not typed as a date")
            current_date = x_value.date() if isinstance(x_value, datetime) else x_value
            if previous_date is not None and current_date <= previous_date:
                raise DataRenderError("date rows must be strictly increasing; no reordering is implicit")
            previous_date = current_date
            label = current_date.isoformat()
        else:
            if not isinstance(x_value, str) or not x_value.strip():
                raise DataRenderError(f"row {row_index} category label is empty or untyped")
            label = x_value
        numeric = float(y_value)
        if isinstance(y_value, Decimal):
            if Decimal(str(numeric)) != y_value:
                raise DataRenderError(
                    f"row {row_index} value cannot be represented exactly by the line renderer")
        elif type(y_value) is int and int(numeric) != y_value:
            raise DataRenderError(
                f"row {row_index} integer exceeds exact line-renderer precision")
        if not math.isfinite(numeric) or not low <= numeric <= high:
            raise DataRenderError(
                f"row {row_index} value falls outside the explicitly supplied y_domain")
        points.append({"label": label, "value": numeric})

    if len(points) < 2:
        raise DataRenderError("line chart requires at least two data rows")
    if len({point["label"] for point in points}) != len(points):
        raise DataRenderError("line x-axis labels must be unique")

    title = plan.question if headline is None else headline
    if not isinstance(title, str) or not title.strip() or len(title) > 160:
        raise DataRenderError("headline must be non-empty text of at most 160 characters")
    return {
        "type": "line_chart",
        "duration": float(duration),
        "headline": title.strip(),
        "subtitle": f"{plan.row_count} source rows; no aggregation applied",
        "x_axis_type": "date" if x_column.data_type == "date" else "category",
        "x_axis_label": (x_axis_label or _field_label(data, x_name)),
        "y_axis_label": (y_axis_label or _field_label(data, y_name)),
        "y_domain": [low, high],
        "points": points,
        "data_provenance": {
            "source_path": data.source_path,
            "source_sha256": data.sha256,
            "rights_authorized": data.rights.authorized,
            "license": data.rights.license_name,
            "authorization_basis": data.rights.authorization_basis,
            "calculation": "none; source rows plotted in supplied order",
            "source_values_exact": [str(row[y_name]) for row in data.rows],
        },
        "visualization_rationale": selected.rationale,
        "renderer_family": "line",
    }


def table_scene(
    data: LoadedData,
    *,
    row_id_column: str,
    column_widths: dict[str, float],
    alignments: dict[str, str],
    duration: float,
    headline: str,
    visible_columns: list[str] | tuple[str, ...] | None = None,
    max_rows: int = 8,
    subtitle: str = "",
) -> dict:
    """Compile authorized typed rows into an explicit stable-ID table scene.

    Widths/order/alignment are caller-supplied; this bridge never truncates,
    reorders, imputes, rounds or converts units. `row_id_column` is retained as
    each row's stable ID and can be omitted from the visible column set.
    """
    try:
        validate_loaded_data(data)
    except ValueError as exc:
        raise DataRenderError(f"LoadedData failed integrity validation: {exc}") from exc
    if row_id_column not in {column.name for column in data.schema.columns}:
        raise DataRenderError(f"Unknown explicit row ID column {row_id_column!r}")
    id_spec = next(column for column in data.schema.columns
                   if column.name == row_id_column)
    if id_spec.data_type not in ("string", "integer"):
        raise DataRenderError("row ID column must be a declared string or integer")
    if isinstance(max_rows, bool) or type(max_rows) is not int or not 1 <= max_rows <= 8:
        raise DataRenderError("max_rows must be between 1 and 8")
    if len(data.rows) > max_rows:
        raise DataRenderError(
            f"table has {len(data.rows)} rows but the explicit display limit is {max_rows}; no rows were dropped")
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) \
            or not math.isfinite(duration) or not .5 <= duration <= 30:
        raise DataRenderError("duration must be finite and between 0.5 and 30 seconds")
    if not isinstance(headline, str) or not headline.strip() or len(headline) > 160:
        raise DataRenderError("headline must be non-empty text of at most 160 characters")
    if not isinstance(subtitle, str) or len(subtitle) > 300:
        raise DataRenderError("subtitle must be text of at most 300 characters")

    schema_columns = {column.name: column for column in data.schema.columns}
    selected = (list(visible_columns) if visible_columns is not None else
                [column.name for column in data.schema.columns
                 if column.name != row_id_column])
    if not 2 <= len(selected) <= 6 or len(set(selected)) != len(selected):
        raise DataRenderError("table needs 2..6 unique, explicitly ordered visible columns")
    if any(name not in schema_columns for name in selected):
        raise DataRenderError("visible_columns must name declared schema columns")
    if set(column_widths) != set(selected):
        raise DataRenderError("column_widths must exactly match visible_columns")
    if set(alignments) != set(selected):
        raise DataRenderError("alignments must exactly match visible_columns")
    widths = {}
    for name in selected:
        width = column_widths[name]
        if isinstance(width, bool) or not isinstance(width, (int, float)) \
                or not math.isfinite(width) or width <= 0:
            raise DataRenderError(f"column width for {name!r} must be finite and positive")
        if alignments[name] not in ("left", "center", "right"):
            raise DataRenderError(f"column alignment for {name!r} must be explicit")
        widths[name] = float(width)
    total = sum(widths.values())
    if not math.isclose(total, 1.0, rel_tol=0, abs_tol=1e-6):
        raise DataRenderError("column widths must sum to 1.0")

    row_ids = []
    output_rows = []
    for row_index, row in enumerate(data.rows):
        row_id = row[row_id_column]
        if isinstance(row_id, str):
            row_id = row_id.strip()
            if not row_id:
                raise DataRenderError(f"row {row_index} has an empty stable ID")
        row_id = str(row_id)
        if row_id in row_ids:
            raise DataRenderError(f"duplicate stable row ID {row_id!r}")
        row_ids.append(row_id)
        cells = {}
        for name in selected:
            value = row[name]
            if value is None:
                raise DataRenderError(f"row {row_id!r}, column {name!r} is missing")
            if schema_columns[name].data_type == "boolean":
                rendered = "true" if value else "false"
            elif isinstance(value, (date, datetime)):
                rendered = value.isoformat()
            else:
                rendered = str(value)
            if not rendered:
                raise DataRenderError(f"row {row_id!r}, column {name!r} renders empty")
            cells[name] = rendered
        output_rows.append({"id": row_id, "values": cells})

    return {
        "type": "table",
        "duration": float(duration),
        "headline": headline.strip(),
        "subtitle": subtitle,
        "columns": [{"id": name, "label": _field_label(data, name),
                     "width": widths[name], "align": alignments[name]}
                    for name in selected],
        "rows": output_rows,
        "data_provenance": {
            "source_path": data.source_path,
            "source_sha256": data.sha256,
            "rights_authorized": data.rights.authorized,
            "license": data.rights.license_name,
            "authorization_basis": data.rights.authorization_basis,
            "row_id_column": row_id_column,
            "row_ids": row_ids,
            "row_count": len(output_rows),
            "ordering": "source order; no sort applied",
        },
        "renderer_family": "table",
    }
