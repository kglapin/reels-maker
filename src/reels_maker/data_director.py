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
            "partial" if family in ("bar", "line", "stacked_bar", "table", "donut", "kpi_cards")
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
