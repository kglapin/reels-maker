"""Typed visualization dispatch, story examples and annotations."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from .data_director import VisualizationPlan
from .data_sources import LoadedData
from .data_render_support import DataRenderError
from .data_charts import (
    bar_chart_scene, line_chart_scene, stacked_bars_100_scene,
)
from .data_tables import (
    sorted_table_scene, table_scene, table_to_bars_scenes,
)

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

def credible_data_story_examples() -> dict[str, dict]:
    """Build 4 credible multi-scene data-motion story packages with original datasets (DM-008)."""
    from .data_director import recommend_visualizations
    from .data_sources import ColumnSpec, DataSchema, RightsProvenance

    rights = RightsProvenance(
        "Internal verified benchmark dataset",
        "Reels Maker Data Lab",
        "https://example.org/datasets/verified-oze-2026",
        "Original synthetic benchmark dataset cleared for cross-platform demonstration",
        True,
    )

    # 1. PV generation annual profile (line + table)
    pv_data = LoadedData(
        (
            {"month": date(2026, 3, 1), "kwh": Decimal("680.0")},
            {"month": date(2026, 6, 1), "kwh": Decimal("1240.5")},
            {"month": date(2026, 9, 1), "kwh": Decimal("890.0")},
            {"month": date(2026, 12, 1), "kwh": Decimal("260.5")},
        ),
        DataSchema((
            ColumnSpec("month", "date", "none", "reject"),
            ColumnSpec("kwh", "decimal", "kWh", "reject", currency="none"),
        ), "pl_PL", "none"),
        "datasets/pv_seasonal_2026.csv",
        "11" * 32,
        rights,
    )
    pv_plan = recommend_visualizations(
        pv_data, question="Sezonowy profil produkcji PV", intent="change_over_time"
    )
    pv_scene = line_chart_scene(pv_data, pv_plan, y_domain=(0, 1400), duration=3.0)

    # 2. Household storage savings ranking (bars + sorted table)
    fin_data = LoadedData(
        (
            {"id": "t-1", "tariff": "Bez magazynu", "savings": Decimal("1800")},
            {"id": "t-2", "tariff": "Magazyn 10 kWh", "savings": Decimal("4650")},
            {"id": "t-3", "tariff": "Magazyn + EMS", "savings": Decimal("6200")},
        ),
        DataSchema((
            ColumnSpec("id", "string", "none", "reject"),
            ColumnSpec("tariff", "string", "none", "reject"),
            ColumnSpec("savings", "decimal", "PLN", "reject", currency="PLN"),
        ), "pl_PL", "PLN"),
        "datasets/storage_savings_2026.csv",
        "22" * 32,
        rights,
    )
    fin_table = sorted_table_scene(
        fin_data,
        row_id_column="id",
        visible_columns=["tariff", "savings"],
        column_widths={"tariff": .62, "savings": .38},
        alignments={"tariff": "left", "savings": "right"},
        duration=3.0,
        headline="Roczna oszczędność według wariantu",
        sort_by="savings",
        sort_order="descending",
        highlight_rows=["t-3"],
    )

    # 3. Regional OZE share 100% stacked bars
    mix_data = LoadedData(
        (
            {"sector": "Dom", "source": "Autokonsumpcja PV", "mwh": Decimal("68")},
            {"sector": "Dom", "source": "Sieć", "mwh": Decimal("32")},
            {"sector": "Biuro", "source": "Autokonsumpcja PV", "mwh": Decimal("74")},
            {"sector": "Biuro", "source": "Sieć", "mwh": Decimal("26")},
        ),
        DataSchema((
            ColumnSpec("sector", "string", "none", "reject"),
            ColumnSpec("source", "string", "none", "reject"),
            ColumnSpec("mwh", "decimal", "MWh", "reject", currency="none"),
        ), "pl_PL", "none"),
        "datasets/oze_share_2026.csv",
        "33" * 32,
        rights,
    )
    mix_plan = recommend_visualizations(
        mix_data, question="Udział autokonsumpcji PV", intent="part_to_whole"
    )
    mix_scene = stacked_bars_100_scene(
        mix_data, mix_plan,
        category_column="sector", segment_column="source", value_column="mwh",
        duration=3.0,
    )

    # 4. Campaign conversion table -> bars transformation
    camp_data = LoadedData(
        (
            {"id": "c-1", "channel": "Reels Wideo", "leads": Decimal("145")},
            {"id": "c-2", "channel": "Wyszukiwarka", "leads": Decimal("98")},
            {"id": "c-3", "channel": "Partnerzy", "leads": Decimal("64")},
        ),
        DataSchema((
            ColumnSpec("id", "string", "none", "reject"),
            ColumnSpec("channel", "string", "none", "reject"),
            ColumnSpec("leads", "decimal", "none", "reject", currency="none"),
        ), "pl_PL", "none"),
        "datasets/campaign_leads_2026.csv",
        "44" * 32,
        rights,
    )
    camp_tbl, camp_bars = table_to_bars_scenes(
        camp_data,
        row_id_column="id",
        label_column="channel",
        value_column="leads",
        visible_columns=["channel", "leads"],
        column_widths={"channel": .65, "leads": .35},
        alignments={"channel": "left", "leads": "right"},
        headline="Pozyskane zapytania z kampanii",
    )

    return {
        "pv_generation_annual": {"data": pv_data, "scenes": [pv_scene]},
        "household_storage_finance": {"data": fin_data, "scenes": [fin_table]},
        "regional_oze_share": {"data": mix_data, "scenes": [mix_scene]},
        "campaign_conversion_lookup": {"data": camp_data, "scenes": [camp_tbl, camp_bars]},
    }

def add_uncertainty_band(
    line_scene: dict,
    *,
    lower_bounds: list[float],
    upper_bounds: list[float],
    confidence_level: float = 0.95,
) -> dict:
    """Attach a validated statistical confidence/uncertainty interval band to a line_chart scene (DM-202)."""
    if not isinstance(line_scene, dict) or line_scene.get("type") != "line_chart":
        raise DataRenderError("add_uncertainty_band requires a line_chart scene")
    if not 0.50 <= float(confidence_level) < 1.0:
        raise DataRenderError("confidence_level must be in [0.50, 1.0)")
    points = line_scene.get("points") or []
    if len(lower_bounds) != len(points) or len(upper_bounds) != len(points):
        raise DataRenderError("lower_bounds and upper_bounds must match point count")
    low_dom, high_dom = (float(v) for v in line_scene["y_domain"])
    band = []
    for idx, (pt, lo, hi) in enumerate(zip(points, lower_bounds, upper_bounds)):
        val = float(pt["value"])
        lo_f, hi_f = float(lo), float(hi)
        if not (low_dom <= lo_f <= val <= hi_f <= high_dom):
            raise DataRenderError(
                f"point {idx} uncertainty interval [{lo_f}, {hi_f}] must bracket value {val} within y_domain"
            )
        band.append({"label": pt["label"], "lower": lo_f, "upper": hi_f})
    updated = dict(line_scene)
    updated["uncertainty_band"] = {
        "confidence_level": round(float(confidence_level), 4),
        "intervals": band,
    }
    return updated

def annotate_chart_scene(
    scene: dict,
    *,
    annotations: list[dict],
    focus_target: str | None = None,
) -> dict:
    """Attach validated custom data annotations and user-directed focus target to a chart/table scene (DM-203)."""
    if not isinstance(scene, dict) or "type" not in scene:
        raise DataRenderError("scene must be a valid chart or table scene dict")
    if not isinstance(annotations, list) or not 1 <= len(annotations) <= 6:
        raise DataRenderError("annotations must be a list of 1..6 annotation objects")
    cleaned = []
    for idx, ann in enumerate(annotations):
        if not isinstance(ann, dict):
            raise DataRenderError(f"annotation {idx} must be an object")
        kind = str(ann.get("kind", "callout"))
        if kind not in ("callout", "threshold_line", "range_highlight"):
            raise DataRenderError(f"Unsupported annotation kind {kind!r}")
        text = str(ann.get("text", "")).strip()
        if not text or len(text) > 120:
            raise DataRenderError(f"annotation {idx} requires non-empty text <= 120 chars")
        cleaned.append({
            "kind": kind,
            "target_id": str(ann.get("target_id", "")),
            "text": text,
            "value": float(ann["value"]) if "value" in ann and ann["value"] is not None else None,
        })
    updated = dict(scene)
    updated["annotations"] = cleaned
    if focus_target is not None:
        if not str(focus_target).strip():
            raise DataRenderError("focus_target cannot be empty string")
        updated["focus_target"] = str(focus_target).strip()
    return updated

def validate_3d_data_justification(spec: dict) -> dict:
    """Fail-closed guard: only permit spatial 3D data scenes when 3 quantitative axes improve comprehension (DM-204)."""
    if not isinstance(spec, dict):
        raise DataRenderError("spec must be a dict")
    chart_type = str(spec.get("chart_type", ""))
    # Extruded 3D bars, 3D pies and 3D single-series lines distort perception and are always rejected
    if chart_type in ("3d_bar", "3d_pie", "3d_donut", "3d_line"):
        raise DataRenderError(
            f"3D chart type {chart_type!r} is rejected: perspective foreshortening distorts 1D/2D magnitude reading"
        )
    axes = spec.get("axes") or []
    rationale = str(spec.get("comprehension_rationale", "")).strip()
    if len(axes) != 3 or not rationale:
        raise DataRenderError(
            "Spatial 3D data scene requires exactly 3 distinct quantitative/spatial axes and an explicit comprehension_rationale"
        )
    return {
        "approved": True,
        "chart_type": chart_type or "spatial_scatter_3d",
        "axes": list(axes),
        "comprehension_rationale": rationale,
    }
