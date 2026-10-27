"""Scene builders for the table family."""
from __future__ import annotations

import math

from ..core.scene_graph import Node
from ..design.color import ensure_contrast, mix
from ..layout.engine import Rect
from ..motionkit.keyframes import Keyframe, Track
from ..textkit.typesetter import TextStyle
from .base import (BuiltScene, SceneContext, number_node, panel_node,
                   resolve_text_style, safe_number, text_node)
from .scene_support import (
    _background, _decor, _finish, _headline, _measure, _spec, _subtitle,
    _theme,
)



def build_table(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Build a compact table from explicit ordered columns and stable row IDs.

    Cell values must already be formatted strings. Width weights and alignments
    are caller data; this component neither formats numbers nor drops rows.
    """
    theme = _theme(ctx, scene)
    headline = _headline(scene)
    columns = scene.get("columns")
    rows = scene.get("rows")
    if not isinstance(columns, list) or not 2 <= len(columns) <= 6:
        raise ValueError("table requires 2..6 explicit columns")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 8:
        raise ValueError("table requires 1..8 explicit rows; pagination is not implemented")

    parsed_columns = []
    seen_columns = set()
    for index, column in enumerate(columns):
        if not isinstance(column, dict):
            raise ValueError(f"table column {index} must be an object")
        key, label = column.get("id"), column.get("label")
        width = column.get("width")
        align = column.get("align")
        if not isinstance(key, str) or not key.strip() or key in seen_columns:
            raise ValueError("table column IDs must be unique non-empty strings")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"table column {key!r} requires a label")
        if (isinstance(width, bool) or not isinstance(width, (int, float))
                or not math.isfinite(width) or width <= 0):
            raise ValueError(f"table column {key!r} requires a positive width weight")
        if align not in ("left", "center", "right"):
            raise ValueError(f"table column {key!r} requires an explicit alignment")
        seen_columns.add(key)
        parsed_columns.append({"id": key, "label": label.strip(),
                               "width": float(width), "align": align})
    weight_total = sum(column["width"] for column in parsed_columns)
    if not math.isclose(weight_total, 1.0, rel_tol=0, abs_tol=1e-6):
        raise ValueError("table column width weights must sum to 1.0")

    parsed_rows = []
    seen_rows = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"table row {index} must be an object")
        row_id, values = row.get("id"), row.get("values")
        if not isinstance(row_id, str) or not row_id.strip() or row_id in seen_rows:
            raise ValueError("table row IDs must be unique non-empty strings")
        if not isinstance(values, dict) or set(values) != seen_columns:
            raise ValueError(f"table row {row_id!r} values must match all declared column IDs")
        if any(not isinstance(value, str) or not value.strip()
               for value in values.values()):
            raise ValueError(f"table row {row_id!r} cells must be explicit non-empty strings")
        seen_rows.add(row_id)
        parsed_rows.append({"id": row_id,
                            "values": {column["id"]: values[column["id"]]
                                       for column in parsed_columns}})

    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        align="center", balance=True)
    body = str(scene.get("subtitle") or _subtitle(scene) or "")
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    layout = ctx.layout.layout("data-panel", {
        "headline": _measure(headline, headline_style, width, ctx),
        "body": _measure(body, body_style, width, ctx),
    })
    table_region = layout.region("chart")
    outer_x = table_region.x + table_region.w * .02
    table_width = table_region.w * .96
    header_height = min(ctx.tokens.px(46), table_region.h * .12)
    rows_height = table_region.h - header_height - ctx.tokens.px(8)
    row_height = rows_height / len(parsed_rows)
    if row_height < ctx.tokens.px(30):
        raise ValueError("table rows do not fit safely in the available region")
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center")
    }
    table_children: list[Node] = []
    header_y = table_region.y
    table_children.append(panel_node(
        "table-header", Rect(outer_x, header_y, table_width, header_height),
        ctx.tokens, fill=theme["accent"], radius="sm", shadow=False))
    header_style = TextStyle(
        max(12, ctx.tokens.px(17)),
        ensure_contrast(theme["base"], theme["accent"], 4.5),
        "bold", uppercase=False, line_height=1.0)
    cell_size = max(12, min(ctx.tokens.px(20), row_height * .52))
    x = outer_x
    for column in parsed_columns:
        cell_width = table_width * column["width"]
        header = text_node(
            f"table-header-{column['id']}", column["label"], header_style,
            Rect(x + cell_width * .04, header_y, cell_width * .92, header_height),
            ctx.fonts, align=column["align"], valign="center", fit=True)
        if header:
            table_children.append(header)
        x += cell_width

    highlight_rows = {str(r) for r in (scene.get("highlight_rows") or [])}
    highlight_cells = {
        (str(pair[0]), str(pair[1]))
        for pair in (scene.get("highlight_cells") or [])
        if isinstance(pair, (list, tuple)) and len(pair) == 2
    }
    animate_from = [str(r) for r in (scene.get("animate_from_row_ids") or [])]
    prev_slot_by_id = {rid: idx for idx, rid in enumerate(animate_from)}
    cell_transitions = scene.get("cell_transitions") or {}
    for row_index, row in enumerate(parsed_rows):
        y = header_y + header_height + ctx.tokens.px(8) + row_index * row_height
        is_row_hi = row["id"] in highlight_rows
        row_fill = (
            mix(theme["surface"], theme["accent"], .22)
            if is_row_hi else (
                theme["surface"] if row_index % 2 == 0
                else mix(theme["surface"], theme["base"], .06)
            )
        )
        cell_style = TextStyle(
            cell_size, ensure_contrast(theme["ink"], row_fill, 4.5),
            "regular", line_height=1.0)
        cell_highlight_style = TextStyle(
            cell_size, ensure_contrast(theme["accent"], row_fill, 4.5),
            "bold", line_height=1.0)
        row_nodes = [panel_node(
            f"table-row-bg-{row_index}", Rect(outer_x, y, table_width, row_height),
            ctx.tokens, fill=row_fill, radius="sm", shadow=False)]
        x = outer_x
        row_trans = cell_transitions.get(row["id"]) if isinstance(cell_transitions, dict) else None
        for column in parsed_columns:
            cell_width = table_width * column["width"]
            col_id = column["id"]
            is_cell_hi = is_row_hi or ((row["id"], col_id) in highlight_cells)
            style_use = cell_highlight_style if is_cell_hi else cell_style
            cell_rect = Rect(x + cell_width * .04, y, cell_width * .92, row_height)
            spec_tr = row_trans.get(col_id) if isinstance(row_trans, dict) else None
            if isinstance(spec_tr, dict) and "from" in spec_tr and "to" in spec_tr:
                fmt = {
                    "prefix": str(spec_tr.get("prefix", "")),
                    "suffix": str(spec_tr.get("suffix", "")),
                    "decimals": int(spec_tr.get("decimals", 0)),
                    "thousands": " ",
                }
                cell = number_node(
                    f"table-cell-{row_index}-{col_id}",
                    safe_number(spec_tr["to"]),
                    cell_rect,
                    ctx.tokens,
                    fmt=fmt,
                    size_role="body",
                    color=style_use.color,
                    align=column["align"],
                )
                from_val = safe_number(spec_tr["from"])
                to_val = safe_number(spec_tr["to"])
                dur = max(.4, min(1.2, ctx.duration * .45))
                cell.track("prop.value", Track([
                    Keyframe(0.0, from_val, "out-cubic"),
                    Keyframe(0.25, from_val, "out-cubic"),
                    Keyframe(0.25 + dur, to_val, "out-cubic"),
                ]))
            else:
                cell = text_node(
                    f"table-cell-{row_index}-{col_id}",
                    row["values"][col_id], style_use,
                    cell_rect,
                    ctx.fonts, align=column["align"], valign="center", fit=True)
            if cell:
                row_nodes.append(cell)
            x += cell_width
        row_group = Node(
            kind="group", role=f"table-row-{row_index}", children=row_nodes,
            qa_class="control",
            meta={"stable_row_id": row["id"], "highlighted": is_row_hi},
        )
        prev_idx = prev_slot_by_id.get(row["id"])
        if prev_idx is not None and prev_idx != row_index and 0 <= prev_idx < len(parsed_rows):
            delta_y = (prev_idx - row_index) * row_height
            settle_t = max(.35, min(1.1, ctx.duration * .45))
            row_group.track("dy", Track([
                Keyframe(0.0, delta_y, "in-out-cubic"),
                Keyframe(settle_t, 0.0, "in-out-cubic"),
                Keyframe(ctx.duration, 0.0, "linear"),
            ]))
        table_children.append(row_group)
    elements["table"] = Node(kind="group", role="table", children=table_children,
                              qa_class="control",
                              meta={"row_ids": [row["id"] for row in parsed_rows],
                                    "highlight_rows": sorted(highlight_rows)})
    if body and layout.optional("body"):
        elements["body"] = text_node("body", body, body_style,
                                      layout.region("body"), ctx.fonts,
                                      align="center", valign="center")
    specs = [_spec("headline", 7), _spec("table", 9, "control"),
             _spec("body", 3)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "table",
                         "columns": parsed_columns,
                         "row_ids": [row["id"] for row in parsed_rows],
                         "highlight_rows": sorted(highlight_rows),
                         "data_provenance": scene.get("data_provenance")})
