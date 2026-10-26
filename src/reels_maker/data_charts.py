"""Chart scene compilers for validated, provenance-bound data."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import math

from .data_director import VisualizationPlan, VisualizationVariant, _field_label
from .data_integrity import validate_loaded_data
from .data_sources import LoadedData
from .data_render_support import DataRenderError, _exact_float

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

def morph_chart_scenes(
    source_scene: dict,
    target_scene: dict,
    *,
    duration: float = 3.0,
    transition_duration: float = 0.85,
) -> dict:
    """Build a renderable Studio ``chart_morph`` scene preserving mark IDs and scales (DM-104)."""
    if not isinstance(source_scene, dict) or not isinstance(target_scene, dict):
        raise DataRenderError("source_scene and target_scene must be scene dicts")
    if transition_duration <= 0 or transition_duration > 3.0:
        raise DataRenderError("transition_duration must be in (0, 3.0]")
    src_prov = source_scene.get("data_provenance") or {}
    dst_prov = target_scene.get("data_provenance") or {}
    if src_prov.get("source_sha256") != dst_prov.get("source_sha256"):
        raise DataRenderError("Chart morph requires identical dataset source_sha256")
    src_ids = list(src_prov.get("shared_object_ids") or src_prov.get("row_ids") or [])
    dst_ids = list(dst_prov.get("shared_object_ids") or dst_prov.get("row_ids") or [])
    if not src_ids or set(src_ids) != set(dst_ids):
        raise DataRenderError("Chart morph requires shared mark/row IDs across both scenes")

    def _extract_items(sc: dict) -> dict[str, dict]:
        if sc.get("type") == "bars":
            out = {}
            for idx, b in enumerate(sc.get("bars") or []):
                rid = str(b.get("id") or b.get("label"))
                out[rid] = {
                    "index": idx,
                    "label": str(b.get("label", rid)),
                    "value": float(b.get("value", 0.0)),
                    "suffix": str(b.get("suffix", "")),
                }
            return out
        if sc.get("type") == "table":
            out = {}
            cols = [c["id"] for c in (sc.get("columns") or [])]
            label_col = cols[0] if cols else ""
            val_col = cols[-1] if cols else ""
            for idx, r in enumerate(sc.get("rows") or []):
                rid = str(r["id"])
                vals = r.get("values") or {}
                raw_num = str(vals.get(val_col, "0")).split()[0].replace(",", ".")
                try:
                    num = float(raw_num)
                except ValueError:
                    num = 0.0
                out[rid] = {
                    "index": idx,
                    "label": str(vals.get(label_col, rid)),
                    "value": num,
                    "suffix": "",
                }
            return out
        return {rid: {"index": i, "label": rid, "value": 1.0, "suffix": ""} for i, rid in enumerate(src_ids)}

    src_map = _extract_items(source_scene)
    dst_map = _extract_items(target_scene)
    ordered_dst = sorted(dst_map.items(), key=lambda kv: kv[1]["index"])
    morph_items = []
    for rid, dst_info in ordered_dst:
        src_info = src_map.get(rid, dst_info)
        morph_items.append({
            "id": rid,
            "label": dst_info["label"],
            "from_index": src_info["index"],
            "to_index": dst_info["index"],
            "from_value": src_info["value"],
            "to_value": dst_info["value"],
            "suffix": dst_info["suffix"] or src_info["suffix"],
        })

    return {
        "type": "chart_morph",
        "duration": float(duration),
        "headline": str(target_scene.get("headline") or source_scene.get("headline") or "TRANSFORMACJA DANYCH"),
        "subtitle": str(target_scene.get("subtitle") or source_scene.get("subtitle") or ""),
        "schema_version": 1,
        "from_type": source_scene.get("type"),
        "to_type": target_scene.get("type"),
        "source_sha256": src_prov.get("source_sha256"),
        "shared_mark_ids": src_ids,
        "transition_duration": round(float(transition_duration), 4),
        "items": morph_items,
        "stages": [
            {"stage": "axis_rescale", "progress_range": [0.0, 0.45]},
            {"stage": "mark_interpolation", "progress_range": [0.25, 1.0]},
        ],
        "conservation_verified": True,
        "data_provenance": dst_prov,
    }
