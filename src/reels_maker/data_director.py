"""Explainable, planning-only visualization recommendations for typed data.

The director selects semantic families from an explicit audience question and
intent. It does not render charts, infer units, or establish causal meaning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .data_sources import LoadedData
from .data_integrity import validate_loaded_data

Intent = Literal[
    "magnitude_ranking", "change_over_time", "deviation_from_target",
    "part_to_whole", "flow_conversion", "distribution", "correlation",
    "matrix", "financial_bridge", "exact_lookup", "geographic_difference",
    "relationships",
]
Family = Literal[
    "bar", "line", "diverging_bar", "bullet", "stacked_bar", "donut",
    "funnel", "sankey", "histogram", "dot_plot", "scatter", "heatmap",
    "waterfall", "table", "kpi_cards", "map", "network_diagram",
]


@dataclass(frozen=True)
class VisualizationVariant:
    family: Family
    rank: int
    rationale: str
    alternatives_rejected: tuple[str, ...]
    required_axes: tuple[str, ...]
    required_labels: tuple[str, ...]
    missing_fields: tuple[str, ...]
    renderer_status: str = "not_assessed"
    planning_only: bool = True


@dataclass(frozen=True)
class VisualizationPlan:
    question: str
    intent: Intent
    row_count: int
    column_count: int
    series_count: int
    variants: tuple[VisualizationVariant, ...]
    source: str
    source_sha256: str
    planning_only: bool = True


_INTENTS: dict[str, tuple[Family, ...]] = {
    "magnitude_ranking": ("bar", "dot_plot"),
    "change_over_time": ("line", "bar"),
    "deviation_from_target": ("diverging_bar", "bullet"),
    "part_to_whole": ("stacked_bar", "donut"),
    "flow_conversion": ("funnel", "sankey"),
    "distribution": ("histogram", "dot_plot"),
    "correlation": ("scatter",),
    "matrix": ("heatmap",),
    "financial_bridge": ("waterfall", "line"),
    "exact_lookup": ("table", "kpi_cards"),
    "geographic_difference": ("bar", "map"),
    "relationships": ("network_diagram", "sankey"),
}


def recommend_visualizations(
    data: LoadedData,
    *,
    question: str,
    intent: Intent,
    max_variants: int = 3,
) -> VisualizationPlan:
    """Recommend 1–3 candidate families from an explicit question and intent.

    `series_count` reports numeric columns in the declared schema; it does not
    assert that each is a meaningful plotted series. Returned families are
    ideas for planning only, never a renderer-capability claim.
    """
    if not isinstance(data, LoadedData):
        raise TypeError("data must be a LoadedData instance")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be explicitly provided")
    if not isinstance(intent, str) or intent not in _INTENTS:
        raise ValueError(f"unsupported explicit intent: {intent!r}")
    if isinstance(max_variants, bool) or not isinstance(max_variants, int) or not 1 <= max_variants <= 3:
        raise ValueError("max_variants must be an integer from 1 to 3")
    validate_loaded_data(data)

    numeric = tuple(
        col for col in data.schema.columns
        if col.data_type in ("integer", "decimal")
    )
    categorical = tuple(col for col in data.schema.columns if col.data_type == "string")
    dates = tuple(col for col in data.schema.columns if col.data_type == "date")
    family_names = _INTENTS[intent][:max_variants]
    primary_measure = numeric[0].name if numeric else None
    category = categorical[0].name if categorical else None
    temporal = dates[0].name if dates else None

    variants: list[VisualizationVariant] = []
    for rank, family in enumerate(family_names, 1):
        axes: tuple[str, ...]
        labels: tuple[str, ...]
        missing: list[str] = []
        rationale: str
        if family in ("bar", "dot_plot", "diverging_bar", "bullet", "stacked_bar", "donut", "funnel", "waterfall", "kpi_cards"):
            axes = tuple(x for x in (category, primary_measure) if x)
            if family != "kpi_cards" and not category:
                missing.append("category column")
            if not primary_measure:
                missing.append("numeric measure")
            if family == "diverging_bar":
                missing.append("explicit baseline/target for divergence")
            if family == "bullet":
                missing.append("explicit target value")
            if family == "stacked_bar":
                missing.append("explicit subgroup/series column")
            if family == "donut":
                missing.append("explicit whole/denominator definition")
            if family == "funnel":
                missing.append("explicit stage-order rule")
            if family == "waterfall":
                missing.append("explicit signed deltas and opening/closing totals")
            labels = tuple(_field_label(data, name) for name in axes)
        elif family == "line":
            axes = tuple(x for x in (temporal or category, primary_measure) if x)
            if not (temporal or category):
                missing.append("date or category column")
            if not primary_measure:
                missing.append("numeric measure")
            missing.append("explicit axis labels and y-domain confirmation for renderer")
            labels = tuple(_field_label(data, name) for name in axes)
        elif family == "scatter":
            axes = tuple(col.name for col in numeric[:2])
            if len(numeric) < 2:
                missing.append("second numeric column")
            labels = tuple(_field_label(data, name) for name in axes)
        elif family == "heatmap":
            axes = tuple(x for x in (temporal, category, primary_measure) if x)
            if not temporal:
                missing.append("date column")
            if not category:
                missing.append("category column")
            if not primary_measure:
                missing.append("numeric measure")
            labels = tuple(_field_label(data, name) for name in axes)
        elif family == "histogram":
            axes = (primary_measure,) if primary_measure else ()
            if not primary_measure:
                missing.append("numeric measure")
            labels = tuple(_field_label(data, name) for name in axes)
        elif family == "table":
            axes = tuple(col.name for col in data.schema.columns)
            labels = tuple(_field_label(data, name) for name in axes)
        elif family == "map":
            axes = tuple(x for x in (category, primary_measure) if x)
            missing.append("explicit geospatial field; current schema has no geospatial type")
            labels = tuple(_field_label(data, name) for name in axes)
        else:  # sankey, network diagram
            axes = tuple(col.name for col in data.schema.columns)
            missing.extend(("explicit source field", "explicit target field", "explicit link-value field"))
            labels = tuple(_field_label(data, name) for name in axes)

        if family == "line" and temporal:
            rationale = f"The explicit change-over-time intent and declared date field {temporal!r} support an ordered time axis; the measure remains {primary_measure or 'unspecified'} as declared."
        elif family == "scatter":
            rationale = "The explicit correlation intent calls for paired quantitative fields; no causal interpretation is implied."
        elif family == "table":
            rationale = "The explicit exact-lookup intent prioritizes retaining source rows and exact declared fields over visual aggregation."
        elif family == "map":
            rationale = "The explicit geographic-difference intent names geography, but the schema has no geospatial type; this is a planning concept only and no map is asserted to be valid."
        elif family in ("sankey", "network_diagram"):
            rationale = "The explicit flow/relationship intent motivates this family; source links, direction and conservation are not inferred from tabular columns."
        else:
            rationale = f"The user explicitly requested {intent.replace('_', ' ')}; this family is a candidate form from the FT Visual Vocabulary, subject to confirmation of the required fields and semantics."
        rejected = tuple(
            f"{name}: not selected as the primary form for the explicit {intent.replace('_', ' ')} question"
            for name in _INTENTS[intent] if name != family
        )
        if missing:
            rationale += " Required but absent or untyped fields: " + ", ".join(missing) + "."
        renderer_status = (
            "partial" if family in (
                "bar", "line", "stacked_bar", "table", "donut", "kpi_cards",
                "waterfall", "diverging_bar", "bullet", "heatmap", "scatter",
                "funnel", "sankey",
            )
            else "not_assessed"
        )
        variants.append(VisualizationVariant(
            family, rank, rationale, rejected, axes, labels, tuple(missing),
            renderer_status=renderer_status))

    return VisualizationPlan(
        question=question.strip(), intent=intent, row_count=len(data.rows),
        column_count=len(data.schema.columns), series_count=len(numeric),
        variants=tuple(variants), source=data.source_path,
        source_sha256=data.sha256,
    )


def _field_label(data: LoadedData, name: str) -> str:
    column = next(column for column in data.schema.columns if column.name == name)
    qualifiers = []
    if column.unit and column.unit != "none":
        qualifiers.append(column.unit)
    currency = column.currency or data.schema.currency
    if currency and currency != "none" and currency not in qualifiers:
        qualifiers.append(currency)
    if not qualifiers:
        return name
    return f"{name} ({', '.join(qualifiers)})"


DOMAIN_PRESETS: dict[str, dict[str, object]] = {
    "pv": {
        "domain": "pv",
        "preferred_families": ("line", "stacked_bar", "sankey", "bar"),
        "default_units": ("kWh", "MWh", "kWp"),
        "style": "editorial-premium",
        "accent_hint": "#47A013",
    },
    "finances": {
        "domain": "finances",
        "preferred_families": ("waterfall", "table", "bar", "line"),
        "default_units": ("PLN", "EUR", "%"),
        "style": "editorial-premium",
        "accent_hint": "#1E6F5C",
    },
    "marketing": {
        "domain": "marketing",
        "preferred_families": ("funnel", "bar", "line", "stacked_bar"),
        "default_units": ("leads", "%", "PLN"),
        "style": "kinetic-advertising",
        "accent_hint": "#E05A2B",
    },
    "operations": {
        "domain": "operations",
        "preferred_families": ("bullet", "heatmap", "diverging_bar", "table"),
        "default_units": ("h", "%", "items"),
        "style": "editorial-premium",
        "accent_hint": "#2A6496",
    },
    "sales": {
        "domain": "sales",
        "preferred_families": ("bar", "funnel", "waterfall", "bullet"),
        "default_units": ("PLN", "units", "%"),
        "style": "kinetic-advertising",
        "accent_hint": "#2C8C4E",
    },
}


def resolve_domain_preset(domain: str) -> dict[str, object]:
    """Return a validated domain preset for PV, finances, marketing, operations or sales (DM-105)."""
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("domain must be a non-empty string")
    key = domain.strip().lower()
    if key not in DOMAIN_PRESETS:
        raise ValueError(
            f"Unknown domain preset {domain!r}; choose one of "
            + ", ".join(sorted(DOMAIN_PRESETS))
        )
    spec = DOMAIN_PRESETS[key]
    return {
        "domain": spec["domain"],
        "preferred_families": list(spec["preferred_families"]),
        "default_units": list(spec["default_units"]),
        "style": spec["style"],
        "accent_hint": spec["accent_hint"],
    }


def plan_data_narration_cues(
    data: LoadedData,
    *,
    label_column: str,
    measure_column: str,
    scene_duration: float = 3.5,
) -> dict:
    """Derive deterministic narration/audio cue anchors and camera focus from verified rows (DM-106)."""
    validate_loaded_data(data)
    if scene_duration <= 1.0:
        raise ValueError("scene_duration must exceed 1.0s")
    cols = {c.name: c for c in data.schema.columns}
    if label_column not in cols or measure_column not in cols:
        raise ValueError("label_column and measure_column must be declared schema columns")
    if cols[measure_column].data_type not in ("integer", "decimal"):
        raise ValueError("measure_column must be numeric")
    rows_with_val = [
        (idx, str(row[label_column]), float(row[measure_column]), str(row[measure_column]))
        for idx, row in enumerate(data.rows)
        if row[label_column] is not None and row[measure_column] is not None
    ]
    if not rows_with_val:
        raise ValueError("Dataset has no non-null rows for cue planning")
    peak = max(rows_with_val, key=lambda r: r[2])
    trough = min(rows_with_val, key=lambda r: r[2])
    return {
        "schema_version": 1,
        "source_sha256": data.sha256,
        "cues": {
            "headline": 0.08,
            "chart": round(scene_duration * 0.18, 3),
            "peak_callout": round(scene_duration * 0.48, 3),
            "body": round(scene_duration * 0.62, 3),
        },
        "data_highlights": {
            "peak_row_index": peak[0],
            "peak_label": peak[1],
            "peak_value_exact": peak[3],
            "min_row_index": trough[0],
            "min_label": trough[1],
            "min_value_exact": trough[3],
        },
        "camera_focus": {
            "target_role": f"row-{peak[0]}",
            "onset": round(scene_duration * 0.45, 3),
            "zoom": 1.04,
        },
    }


def select_data_story_variant(
    data: LoadedData,
    *,
    question: str,
    candidate_scenes: list[dict],
) -> dict:
    """Evaluate 3 visual storytelling variants across responsive aspects and select the best (DM-107)."""
    from .components.base import SceneContext
    from .components.scenes import build_scene
    from .design.tokens import resolve_tokens
    from .qa.report import audit_data_scene
    from .textkit.typesetter import FontBook

    validate_loaded_data(data)
    if not isinstance(candidate_scenes, list) or not 1 <= len(candidate_scenes) <= 3:
        raise ValueError("candidate_scenes must contain 1..3 scene variants")
    fonts = FontBook()
    aspects = (("portrait", 360, 640), ("square", 480, 480), ("landscape", 640, 360))
    evaluated = []
    for idx, scene in enumerate(candidate_scenes):
        variant_id = f"story-variant-{idx + 1}:{scene.get('type', 'unknown')}"
        aspect_results = {}
        total_issues = 0
        for asp_name, w, h in aspects:
            tokens = resolve_tokens("editorial-premium", width=w, height=h)
            ctx = SceneContext(
                width=w, height=h, fps=24,
                duration=float(scene.get("duration", 3.0)),
                tokens=tokens, style="editorial-premium", fonts=fonts,
            )
            try:
                built = build_scene(ctx, scene)
                issues = audit_data_scene(built)
                errs = sum(1 for i in issues if i.severity == "error")
                total_issues += errs
                aspect_results[asp_name] = {"ok": errs == 0, "errors": errs}
            except Exception as exc:
                total_issues += 1
                aspect_results[asp_name] = {"ok": False, "errors": 1, "error": str(exc)}
        valid = total_issues == 0
        # Prefer richer semantic forms when all 3 aspects pass cleanly
        type_bonus = {
            "waterfall": 0.95, "sankey": 0.94, "stacked_bars_100": 0.92,
            "line_chart": 0.91, "bars": 0.90, "table": 0.88,
            "bullet": 0.89, "diverging_bar": 0.89, "funnel": 0.88,
            "heatmap": 0.87, "scatter": 0.86,
        }.get(str(scene.get("type")), 0.80)
        score = round(type_bonus if valid else 0.0, 4)
        evaluated.append({
            "variant_id": variant_id,
            "scene_type": scene.get("type"),
            "valid": valid,
            "score": score,
            "responsive_aspects": aspect_results,
            "scene": scene,
        })
    evaluated.sort(key=lambda r: (not r["valid"], -r["score"], r["variant_id"]))
    winner = next((r for r in evaluated if r["valid"]), None)
    return {
        "question": question,
        "selected_variant_id": winner["variant_id"] if winner else None,
        "selected_scene": winner["scene"] if winner else None,
        "variants": evaluated,
    }
