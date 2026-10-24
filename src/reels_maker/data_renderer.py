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


def bar_chart_scene(
    data: LoadedData,
    plan: VisualizationPlan,
    *,
    duration: float,
    data_order: str = "source",
    headline: str | None = None,
    subtitle: str | None = None,
    row_id_column: str | None = None,
    variant: int = 0,
) -> dict:
    """Compile a validated bar-chart recommendation into a Studio ``bars`` scene (DM-003/004)."""
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
    if selected.family != "bar":
        raise DataRenderError(
            f"bar_chart_scene requires a 'bar' variant, got {selected.family!r}"
        )
    if selected.missing_fields:
        raise DataRenderError(
            "Recommendation has unresolved required fields: "
            + ", ".join(selected.missing_fields)
        )
    if data_order not in ("source", "ascending", "descending"):
        raise DataRenderError("data_order must be source, ascending or descending")
    if (isinstance(duration, bool) or not isinstance(duration, (int, float))
            or not math.isfinite(duration) or not .5 <= duration <= 30):
        raise DataRenderError("duration must be finite and between 0.5 and 30 seconds")

    cat_name, val_name = selected.required_axes
    columns = {col.name: col for col in data.schema.columns}
    cat_col, val_col = columns[cat_name], columns[val_name]
    if cat_col.data_type != "string":
        raise DataRenderError("bar category column must be string")
    if val_col.data_type not in ("integer", "decimal"):
        raise DataRenderError("bar measure column must be integer or decimal")
    if row_id_column is not None and row_id_column not in columns:
        raise DataRenderError(f"Unknown row_id_column {row_id_column!r}")

    unit_suffix = (
        f" {val_col.unit}"
        if val_col.unit and val_col.unit not in ("none", "ratio")
        else ""
    )
    bars = []
    seen_labels = set()
    row_ids = []
    for idx, row in enumerate(data.rows):
        raw_label, raw_val = row[cat_name], row[val_name]
        if raw_label is None or raw_val is None:
            raise DataRenderError(f"row {idx} has missing bar category or value")
        label = str(raw_label).strip()
        if not label or label in seen_labels:
            raise DataRenderError(f"row {idx} category label must be non-empty and unique")
        seen_labels.add(label)
        numeric = _exact_float(raw_val, row_index=idx, label=val_name)
        if numeric < 0:
            raise DataRenderError("bar_chart_scene requires non-negative values")
        rid = str(row[row_id_column]).strip() if row_id_column else label
        row_ids.append(rid)
        bars.append({
            "id": rid,
            "label": label,
            "value": numeric,
            "suffix": unit_suffix,
        })

    title = (plan.question if headline is None else headline).strip()
    if not title or len(title) > 160:
        raise DataRenderError("headline must be non-empty and at most 160 characters")
    return {
        "type": "bars",
        "duration": float(duration),
        "headline": title,
        "subtitle": (
            subtitle if subtitle is not None
            else f"{plan.row_count} source rows; order={data_order}"
        ),
        "data_order": data_order,
        "bars": bars,
        "data_provenance": {
            "source_path": data.source_path,
            "source_sha256": data.sha256,
            "rights_authorized": data.rights.authorized,
            "license": data.rights.license_name,
            "authorization_basis": data.rights.authorization_basis,
            "calculation": f"none; order={data_order}",
            "source_values_exact": [str(row[val_name]) for row in data.rows],
            "row_ids": row_ids,
        },
        "visualization_rationale": selected.rationale,
        "renderer_family": "bar",
    }


def stacked_bars_100_scene(
    data: LoadedData,
    plan: VisualizationPlan,
    *,
    category_column: str,
    segment_column: str,
    value_column: str,
    duration: float,
    headline: str | None = None,
    subtitle: str | None = None,
    variant: int = 0,
) -> dict:
    """Compile authorized part-to-whole rows into a 100% stacked bar scene (DM-003/004)."""
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
    if selected.family != "stacked_bar":
        raise DataRenderError(
            f"stacked_bars_100_scene requires 'stacked_bar', got {selected.family!r}"
        )
    if (isinstance(duration, bool) or not isinstance(duration, (int, float))
            or not math.isfinite(duration) or not .5 <= duration <= 30):
        raise DataRenderError("duration must be finite and between 0.5 and 30 seconds")

    columns = {col.name: col for col in data.schema.columns}
    for col_name in (category_column, segment_column, value_column):
        if col_name not in columns:
            raise DataRenderError(f"Unknown schema column {col_name!r}")
    if len({category_column, segment_column, value_column}) != 3:
        raise DataRenderError("category_column, segment_column and value_column must be distinct")
    if columns[category_column].data_type != "string" or columns[segment_column].data_type != "string":
        raise DataRenderError("category and segment columns must be declared strings")
    if columns[value_column].data_type not in ("integer", "decimal"):
        raise DataRenderError("value_column must be integer or decimal")

    category_order: list[str] = []
    segment_order: list[str] = []
    cell_map: dict[tuple[str, str], float] = {}
    exact_values: list[str] = []
    for idx, row in enumerate(data.rows):
        cat = str(row[category_column] or "").strip()
        seg = str(row[segment_column] or "").strip()
        val = row[value_column]
        if not cat or not seg or val is None:
            raise DataRenderError(f"row {idx} has missing category, segment or value")
        key = (cat, seg)
        if key in cell_map:
            raise DataRenderError(f"duplicate category/segment cell {key!r}")
        numeric = _exact_float(val, row_index=idx, label=value_column)
        if numeric < 0:
            raise DataRenderError("stacked_bars_100 requires non-negative values")
        if cat not in category_order:
            category_order.append(cat)
        if seg not in segment_order:
            segment_order.append(seg)
        cell_map[key] = numeric
        exact_values.append(str(val))

    if not 1 <= len(category_order) <= 4:
        raise DataRenderError("stacked_bars_100 requires 1..4 categories")
    if not 2 <= len(segment_order) <= 4:
        raise DataRenderError("stacked_bars_100 requires 2..4 segments")

    categories = []
    for cat in category_order:
        segs = []
        for seg in segment_order:
            if (cat, seg) not in cell_map:
                raise DataRenderError(
                    f"missing segment {seg!r} for category {cat!r}; no zero is imputed"
                )
            segs.append({"id": seg.lower().replace(" ", "-"), "label": seg,
                         "value": cell_map[(cat, seg)]})
        if sum(item["value"] for item in segs) <= 0:
            raise DataRenderError(f"category {cat!r} has zero total")
        categories.append({
            "id": cat.lower().replace(" ", "-"),
            "label": cat,
            "segments": segs,
        })

    title = (plan.question if headline is None else headline).strip()
    if not title or len(title) > 160:
        raise DataRenderError("headline must be non-empty and at most 160 characters")
    return {
        "type": "stacked_bars_100",
        "duration": float(duration),
        "headline": title,
        "subtitle": subtitle or "100% normalized per category; no imputation",
        "categories": categories,
        "data_provenance": {
            "source_path": data.source_path,
            "source_sha256": data.sha256,
            "rights_authorized": data.rights.authorized,
            "license": data.rights.license_name,
            "authorization_basis": data.rights.authorization_basis,
            "calculation": "segment value / explicit category total",
            "source_values_exact": exact_values,
        },
        "visualization_rationale": selected.rationale,
        "renderer_family": "stacked_bar",
    }


def sorted_table_scene(
    data: LoadedData,
    *,
    row_id_column: str,
    column_widths: dict[str, float],
    alignments: dict[str, str],
    duration: float,
    headline: str,
    sort_by: str,
    sort_order: str = "descending",
    animate_sort: bool = True,
    highlight_rows: list[str] | tuple[str, ...] = (),
    highlight_cells: list[tuple[str, str]] | tuple[tuple[str, str], ...] = (),
    cell_transitions: dict[str, dict[str, dict]] | None = None,
    visible_columns: list[str] | tuple[str, ...] | None = None,
    max_rows: int = 8,
    subtitle: str = "",
) -> dict:
    """Compile a table scene with explicit deterministic sort, row reorder animation and highlights (DM-005/006)."""
    base = table_scene(
        data,
        row_id_column=row_id_column,
        column_widths=column_widths,
        alignments=alignments,
        duration=duration,
        headline=headline,
        visible_columns=visible_columns,
        max_rows=max_rows,
        subtitle=subtitle,
    )
    schema_cols = {col.name: col for col in data.schema.columns}
    if sort_by not in schema_cols:
        raise DataRenderError(f"Unknown sort_by column {sort_by!r}")
    if sort_order not in ("ascending", "descending"):
        raise DataRenderError("sort_order must be ascending or descending")
    source_row_ids = list(base["data_provenance"]["row_ids"])
    indexed = list(enumerate(zip(data.rows, base["rows"])))
    reverse = sort_order == "descending"
    # Python's Timsort is stable: ties preserve original source order.
    indexed.sort(key=lambda item: item[1][0][sort_by], reverse=reverse)
    sorted_rows = [item[1][1] for item in indexed]
    sorted_ids = [row["id"] for row in sorted_rows]

    col_ids = {c["id"] for c in base["columns"]}
    for rid in highlight_rows:
        if rid not in sorted_ids:
            raise DataRenderError(f"highlight_rows references unknown row_id {rid!r}")
    norm_cells: list[list[str]] = []
    for pair in highlight_cells:
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise DataRenderError("highlight_cells entries must be (row_id, column_id) pairs")
        rid, cid = str(pair[0]), str(pair[1])
        if rid not in sorted_ids or cid not in col_ids:
            raise DataRenderError(f"highlight_cells references unknown ({rid!r}, {cid!r})")
        norm_cells.append([rid, cid])

    if cell_transitions:
        for rid, cols in cell_transitions.items():
            if rid not in sorted_ids:
                raise DataRenderError(f"cell_transitions references unknown row_id {rid!r}")
            for cid, spec in cols.items():
                if cid not in col_ids:
                    raise DataRenderError(f"cell_transitions references unknown column {cid!r}")
                if not isinstance(spec, dict) or "from" not in spec or "to" not in spec:
                    raise DataRenderError("cell_transitions entry requires 'from' and 'to'")

    base["rows"] = sorted_rows
    if animate_sort:
        base["animate_from_row_ids"] = source_row_ids
    if highlight_rows:
        base["highlight_rows"] = list(highlight_rows)
    if norm_cells:
        base["highlight_cells"] = norm_cells
    if cell_transitions:
        base["cell_transitions"] = cell_transitions
    base["data_provenance"] = {
        **base["data_provenance"],
        "source_row_ids": source_row_ids,
        "row_ids": sorted_ids,
        "ordering": f"sorted by {sort_by} ({sort_order}); ties preserve source order",
    }
    return base


def paginate_table_scenes(
    data: LoadedData,
    *,
    row_id_column: str,
    column_widths: dict[str, float],
    alignments: dict[str, str],
    duration_per_page: float,
    headline: str,
    page_size: int = 6,
    visible_columns: list[str] | tuple[str, ...] | None = None,
    subtitle: str = "",
) -> list[dict]:
    """Split a large authorized dataset into sequential table page scenes without dropping rows (DM-005)."""
    try:
        validate_loaded_data(data)
    except ValueError as exc:
        raise DataRenderError(f"LoadedData failed integrity validation: {exc}") from exc
    if isinstance(page_size, bool) or type(page_size) is not int or not 1 <= page_size <= 8:
        raise DataRenderError("page_size must be an integer between 1 and 8")
    total_rows = len(data.rows)
    if total_rows == 0:
        raise DataRenderError("Cannot paginate an empty dataset")
    pages: list[dict] = []
    page_count = math.ceil(total_rows / page_size)
    all_seen_ids: list[str] = []
    for page_idx in range(page_count):
        chunk = data.rows[page_idx * page_size:(page_idx + 1) * page_size]
        sub_data = LoadedData(
            rows=chunk,
            schema=data.schema,
            source_path=data.source_path,
            sha256=data.sha256,
            rights=data.rights,
        )
        page_headline = (
            headline.strip() if page_count == 1
            else f"{headline.strip()} ({page_idx + 1}/{page_count})"
        )
        scene = table_scene(
            sub_data,
            row_id_column=row_id_column,
            column_widths=column_widths,
            alignments=alignments,
            duration=duration_per_page,
            headline=page_headline,
            visible_columns=visible_columns,
            max_rows=page_size,
            subtitle=subtitle,
        )
        page_ids = scene["data_provenance"]["row_ids"]
        if set(page_ids) & set(all_seen_ids):
            raise DataRenderError("Duplicate stable row ID across paginated table scenes")
        all_seen_ids.extend(page_ids)
        scene["data_provenance"] = {
            **scene["data_provenance"],
            "page_index": page_idx + 1,
            "page_count": page_count,
            "total_source_rows": total_rows,
        }
        pages.append(scene)
    return pages


def table_to_bars_scenes(
    data: LoadedData,
    *,
    row_id_column: str,
    label_column: str,
    value_column: str,
    column_widths: dict[str, float],
    alignments: dict[str, str],
    headline: str,
    table_duration: float = 2.5,
    chart_duration: float = 3.0,
    data_order: str = "descending",
    visible_columns: list[str] | tuple[str, ...] | None = None,
) -> tuple[dict, dict]:
    """Compile a table -> bar-chart scene pair with shared stable object IDs and conservation proof (DM-101)."""
    from .data_director import recommend_visualizations

    tbl = table_scene(
        data,
        row_id_column=row_id_column,
        column_widths=column_widths,
        alignments=alignments,
        duration=table_duration,
        headline=headline,
        visible_columns=visible_columns,
    )
    # Build a synthetic 2-column projection for the bar recommendation if extra columns exist
    bar_cols = tuple(
        col for col in data.schema.columns
        if col.name in (label_column, value_column, row_id_column)
    )
    from .data_sources import DataSchema
    projected = LoadedData(
        rows=tuple(
            {k: row[k] for k in (row_id_column, label_column, value_column)}
            for row in data.rows
        ),
        schema=DataSchema(
            tuple(
                col for col in sorted(
                    bar_cols,
                    key=lambda c: (0 if c.name == label_column else (1 if c.name == value_column else 2)),
                )
            ),
            data.schema.locale,
            data.schema.currency,
        ),
        source_path=data.source_path,
        sha256=data.sha256,
        rights=data.rights,
    )
    plan = recommend_visualizations(
        projected, question=headline, intent="magnitude_ranking"
    )
    chart = bar_chart_scene(
        projected,
        plan,
        duration=chart_duration,
        data_order=data_order,
        headline=headline,
        row_id_column=row_id_column,
    )
    table_ids = tbl["data_provenance"]["row_ids"]
    chart_ids = chart["data_provenance"]["row_ids"]
    if set(table_ids) != set(chart_ids) or len(table_ids) != len(chart_ids):
        raise DataRenderError("table -> bars transformation lost or duplicated row IDs")
    table_sum = sum(Decimal(str(row[value_column])) for row in data.rows)
    chart_sum = sum(Decimal(str(v)) for v in chart["data_provenance"]["source_values_exact"])
    if table_sum != chart_sum:
        raise DataRenderError("table -> bars transformation failed numeric conservation")

    shared_meta = {
        "shared_object_ids": table_ids,
        "conservation_verified": True,
        "conserved_measure_column": value_column,
        "conserved_total": str(table_sum),
    }
    tbl["data_provenance"] = {**tbl["data_provenance"], **shared_meta}
    chart["data_provenance"] = {**chart["data_provenance"], **shared_meta}
    return tbl, chart


def compile_visualization_scene(
    data: LoadedData,
    plan: VisualizationPlan,
    *,
    variant: int = 0,
    duration: float = 3.0,
    **kwargs,
) -> dict:
    """Unified DM-003 dispatcher from a VisualizationPlan variant to a Studio scene."""
    if not isinstance(plan, VisualizationPlan):
        raise TypeError("plan must be a VisualizationPlan")
    if type(variant) is not int or not 0 <= variant < len(plan.variants):
        raise DataRenderError("variant index is outside the recommendation list")
    family = plan.variants[variant].family
    if family == "line":
        return line_chart_scene(data, plan, variant=variant, duration=duration, **kwargs)
    if family == "bar":
        return bar_chart_scene(data, plan, variant=variant, duration=duration, **kwargs)
    if family == "stacked_bar":
        return stacked_bars_100_scene(data, plan, variant=variant, duration=duration, **kwargs)
    if family == "table":
        return table_scene(data, duration=duration, headline=kwargs.pop("headline", plan.question), **kwargs)
    raise DataRenderError(f"Unsupported visualization family for compilation: {family!r}")
