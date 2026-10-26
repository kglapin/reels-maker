"""Table and table-derived chart scene compilers."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import math

from .data_director import _field_label
from .data_integrity import validate_loaded_data
from .data_sources import LoadedData
from .data_render_support import DataRenderError, _exact_float
from .data_charts import bar_chart_scene

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
