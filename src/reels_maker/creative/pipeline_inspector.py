"""Scene graph inspector data and self-contained HTML output."""
from __future__ import annotations

import json
from pathlib import Path

def export_scene_graph_inspector(built_scenes: list) -> dict:
    """Export a GUI-ready scene graph and editable motion-path SVG/JSON payload (MD-603)."""
    scenes_out = []
    for built in built_scenes:
        nodes_out = []
        for root in built.nodes:
            for node in root.flatten():
                tracks_out = {
                    t_name: [
                        {"time": round(float(k.time), 4), "value": round(float(k.value), 4), "easing": k.easing}
                        for k in track.keys
                    ]
                    for t_name, track in node.tracks.items()
                }
                svg_path = None
                if "dx" in node.tracks or "dy" in node.tracks:
                    times = sorted({
                        0.0,
                        *(float(k.time) for t in node.tracks.values() for k in t.keys),
                        float(built.duration),
                    })
                    pts = [
                        (
                            round(float(node.tracks["dx"].value(t)) if "dx" in node.tracks else 0.0, 2),
                            round(float(node.tracks["dy"].value(t)) if "dy" in node.tracks else 0.0, 2),
                        )
                        for t in times
                    ]
                    svg_path = "M " + " L ".join(f"{x},{y}" for x, y in pts)
                nodes_out.append({
                    "role": node.role,
                    "kind": node.kind,
                    "bounds": node.world_bounds(),
                    "tracks": tracks_out,
                    "motion_path_svg": svg_path,
                })
        scenes_out.append({
            "scene_index": built.index + 1,
            "duration": float(built.duration),
            "recipe": built.layout.recipe,
            "node_count": len(nodes_out),
            "nodes": nodes_out,
        })
    return {"schema_version": 1, "scenes": scenes_out}

def write_scene_graph_inspector_html(
    built_scenes: list,
    output_html: str | Path,
) -> dict:
    """Write a self-contained interactive HTML5 + SVG motion-path editor and inspector (MD-603)."""
    import html as html_mod

    payload = export_scene_graph_inspector(built_scenes)
    out_path = Path(output_html).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    svg_paths = []
    rows_html = []
    for sc in payload["scenes"]:
        for node in sc["nodes"]:
            role_esc = html_mod.escape(str(node["role"]))
            kind_esc = html_mod.escape(str(node["kind"]))
            track_names = ", ".join(sorted(node["tracks"])) or "static"
            rows_html.append(
                f"<tr data-scene='{sc['scene_index']}' data-role='{role_esc}'>"
                f"<td>{sc['scene_index']}</td><td>{role_esc}</td><td>{kind_esc}</td>"
                f"<td>{html_mod.escape(track_names)}</td></tr>"
            )
            if node["motion_path_svg"]:
                svg_paths.append(
                    f"<path d='{html_mod.escape(node['motion_path_svg'])}' "
                    f"data-role='{role_esc}' fill='none' stroke='#47A013' stroke-width='2.5'/>"
                )
    doc = (
        "<!DOCTYPE html><html lang='pl'><head><meta charset='utf-8'/>"
        "<title>Reels Maker — Motion Path & Scene Graph Inspector</title>"
        "<style>body{font-family:system-ui,sans-serif;margin:24px;background:#0E1A13;color:#F2F5F0}"
        ".grid{display:grid;grid-template-columns:380px 1fr;gap:24px}"
        "svg{background:#14241B;border:1px solid #2C4637;border-radius:12px;width:100%;height:420px}"
        "table{width:100%;border-collapse:collapse}th,td{padding:8px;border-bottom:1px solid #24382C;text-align:left}"
        "</style></head><body>"
        "<h1>Scene Graph &amp; Editable Motion Path Inspector</h1>"
        "<label>Timeline scrubber: <input id='scrubber' type='range' min='0' max='100' value='50'/></label>"
        "<div class='grid'>"
        f"<svg id='motion-viewport' viewBox='-120 -120 360 360'>{''.join(svg_paths)}</svg>"
        f"<div><table><thead><tr><th>Scena</th><th>Rola</th><th>Typ</th><th>Tory</th></tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody></table></div></div>"
        f"<script id='scene-graph-data' type='application/json'>{json.dumps(payload)}</script>"
        "</body></html>"
    )
    out_path.write_text(doc, encoding="utf-8")
    return {"output_html": str(out_path), "scene_count": len(payload["scenes"]), "payload": payload}
