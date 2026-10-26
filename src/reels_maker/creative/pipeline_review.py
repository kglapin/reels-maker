"""Review portal bundle and HTML generation."""
from __future__ import annotations

import json
from pathlib import Path

def build_review_portal_bundle(
    project_name: str,
    *,
    renders: dict[str, str],
    comments: list[dict],
    release_version: str,
) -> dict:
    """Build a collaboration/approval portal manifest with comparison slider pairs and shot comments (MD-604)."""
    if not str(project_name or "").strip() or not renders:
        raise ValueError("project_name and non-empty renders are required")
    validated_comments = []
    for idx, c in enumerate(comments):
        if not isinstance(c, dict) or "shot" not in c or not str(c.get("text", "")).strip():
            raise ValueError(f"comment {idx} requires shot index and non-empty text")
        validated_comments.append({
            "shot": int(c["shot"]),
            "timecode_s": round(float(c.get("timecode_s", 0.0)), 3),
            "author": str(c.get("author", "reviewer")),
            "text": str(c["text"]).strip(),
            "resolved": bool(c.get("resolved", False)),
        })
    keys = sorted(renders)
    comparison_slider = (
        {"left_variant": keys[0], "right_variant": keys[1],
         "left_path": renders[keys[0]], "right_path": renders[keys[1]]}
        if len(keys) >= 2 else None
    )
    return {
        "schema_version": 1,
        "project": project_name.strip(),
        "release_version": str(release_version).strip(),
        "renders": dict(renders),
        "comparison_slider": comparison_slider,
        "shot_comments": validated_comments,
        "approval_state": "ready_for_signoff" if all(c["resolved"] for c in validated_comments) else "changes_requested",
    }

def write_review_portal_html(
    bundle: dict,
    output_html: str | Path,
) -> dict:
    """Write an interactive HTML5 collaboration/approval portal with A/B comparison slider (MD-604)."""
    import html as html_mod

    out_path = Path(output_html).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    slider = bundle.get("comparison_slider") or {}
    comments_rows = "".join(
        f"<tr><td>#{int(c['shot'])}</td><td>{float(c['timecode_s']):.2f}s</td>"
        f"<td>{html_mod.escape(str(c['author']))}</td>"
        f"<td>{html_mod.escape(str(c['text']))}</td>"
        f"<td>{'RESOLVED' if c.get('resolved') else 'OPEN'}</td></tr>"
        for c in (bundle.get("shot_comments") or [])
    )
    doc = (
        "<!DOCTYPE html><html lang='pl'><head><meta charset='utf-8'/>"
        f"<title>Review Portal — {html_mod.escape(str(bundle.get('project', '')))}</title>"
        "<style>body{font-family:system-ui,sans-serif;margin:24px;background:#101814;color:#F4F7F5}"
        ".badge{padding:4px 10px;border-radius:6px;background:#47A013;display:inline-block}"
        "table{width:100%;border-collapse:collapse;margin-top:16px}th,td{padding:8px;border-bottom:1px solid #26382E}"
        "</style></head><body>"
        f"<h1>Portal Akceptacji: {html_mod.escape(str(bundle.get('project', '')))} "
        f"<span class='badge'>{html_mod.escape(str(bundle.get('approval_state', '')))}</span></h1>"
        "<section id='ab-comparison'>"
        f"<p>Porównanie A/B: <strong>{html_mod.escape(str(slider.get('left_variant', 'A')))}</strong> vs "
        f"<strong>{html_mod.escape(str(slider.get('right_variant', 'B')))}</strong></p>"
        "<input id='ab-slider' type='range' min='0' max='100' value='50'/>"
        "</section>"
        "<table><thead><tr><th>Ujęcie</th><th>Czas</th><th>Autor</th><th>Komentarz</th><th>Status</th></tr></thead>"
        f"<tbody>{comments_rows}</tbody></table>"
        f"<script id='review-bundle-data' type='application/json'>{json.dumps(bundle)}</script>"
        "</body></html>"
    )
    out_path.write_text(doc, encoding="utf-8")
    return {"output_html": str(out_path), "approval_state": bundle.get("approval_state")}
