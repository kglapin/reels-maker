#!/usr/bin/env python3
"""Create reproducible five-minute Motion Lab capability demo manifests."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRAND = "motion-lab"
BRAND_ROOT = ROOT / "brands" / BRAND
MEDIA = "media/stock"
STILLS = [
    f"{MEDIA}/solar-field-synthetic.png",
    f"{MEDIA}/battery-room-synthetic.png",
    f"{MEDIA}/wind-farm-synthetic.png",
    f"{MEDIA}/city-grid-synthetic.png",
]
VIDEO_A = f"{MEDIA}/energy-orbit-synthetic.mp4"
VIDEO_B = f"{MEDIA}/grid-flow-synthetic.mp4"
TRANSITIONS = (
    "color-takeover", "radial-reveal", "whip-pan", "zoom-through",
    "diagonal-wipe", "iris-close-open", "stripe-reveal", "split-slide",
    "spin-zoom", "pixel-dissolve",
)
TEXT_MOTIONS = (
    "vertical-drift", "curtain-mask", "horizontal-wipe", "lateral-slide",
    "elastic-scale", "optical-tracking", "stagger-cascade", "depth-focus",
)


def _scene(kind: str, headline: str, subtitle: str = "", **fields) -> dict:
    scene = {
        "type": kind,
        "duration": 8.0,
        "headline": headline,
        "subtitle": subtitle,
        "decor": False,
        "theme": "dark",
    }
    scene.update(fields)
    return scene


def studio_scenes() -> list[dict]:
    scenes = [
        _scene("statement", "MOTION", "SYNTHETIC ENGINE SHOWCASE",
               typography_motion=TEXT_MOTIONS[0]),
        _scene("spotlight", "IMAGE + VIDEO LAYERS", "GENERATED DEMO MEDIA",
               photo=STILLS[0], photo_time=0.0,
               video_layer={"path": VIDEO_A, "x": 60, "y": 740,
                            "w": 600, "h": 300, "mask": "rounded",
                            "radius": 20}, typography_motion=TEXT_MOTIONS[1]),
        _scene("announcement", "CALENDAR", "SCENE COMPOSITION",
               kicker="DEMO", day="08", calendar_label="SCENE GRAPH",
               typography_motion=TEXT_MOTIONS[2]),
        _scene("deadline", "TEMPORAL DESIGN", "DEADLINE / TIMELINE",
               kicker="", date="08.10.2026",
               milestones=["START", "BUILD", "HOLD"],
               typography_motion=TEXT_MOTIONS[3]),
        _scene("urgency", "PACE WITH PURPOSE", "URGENCY WITHOUT CHAOS",
               typography_motion=TEXT_MOTIONS[4]),
        _scene("quote", "ONE IDEA PER SHOT", "MOTION LAB · SYNTHETIC BRAND",
               typography_motion=TEXT_MOTIONS[5]),
        _scene("amount", "COUNTERS + UNITS", "ILLUSTRATIVE VALUE",
               value=12800, kicker="SYNTHETIC DATA", visual="battery",
               format={"suffix": " kWh", "decimals": 0},
               typography_motion=TEXT_MOTIONS[6]),
        _scene("breakdown", "COMPOSITION", "MULTI-ROW VALUE BREAKDOWN",
               items=[{"label": "STORAGE", "value": 5200},
                      {"label": "CONTROL", "value": 3100},
                      {"label": "GENERATION", "value": 4500}],
               total=12800, typography_motion=TEXT_MOTIONS[7]),
        _scene("comparison", "BEFORE / AFTER", "COMPARISON CARDS",
               columns=[{"label": "BASELINE", "value": 5400, "suffix": " kWh"},
                        {"label": "OPTIMIZED", "value": 9200, "suffix": " kWh"}]),
        _scene("donut", "PROPORTION", "SYNTHETIC SHARE", value=68,
               suffix="%", allowed_overlaps=[
                   ["visual/chart", "visual/percent"],
                   ["visual/chart", "visual/chart-label"],
               ]),
        _scene("heat", "HERO METRIC", "ACCENTED VALUE DISPLAY",
               value=7420, kicker="ILLUSTRATIVE", suffix=" kWh"),
        _scene("europe", "REGIONAL VIEW", "DATA-DRIVEN HIGHLIGHT",
               value=47, kicker="SYNTHETIC INDEX", suffix="%"),
        _scene("stats", "MULTI-METRIC GRID", "SYNTHETIC SAMPLE VALUES",
                stats=[{"label": "OUTPUT", "value": 128, "suffix": " kWh"},
                       {"label": "STORAGE", "value": 64, "suffix": " kWh"},
                       {"label": "HOURS", "value": 18, "suffix": " h"},
                       {"label": "SITES", "value": 12, "suffix": ""}]),
        _scene("checklist", "STAGED REVEAL", "CHECKLIST CHOREOGRAPHY",
               items=["SOURCE", "MEASURE", "OPTIMIZE", "VERIFY"]),
        _scene("cta", "END CARD", "SYNTHETIC DEMO — NOT AN ADVERTISEMENT",
               phone="DEMO ONLY", website="motion-lab.example", line_one="RENDER SYSTEM",
               line_two="LOCAL DEMONSTRATION"),
        _scene("energy", "ENERGY FLOW", "BUILT-IN VECTOR ICONS"),
        _scene("photo_carousel", "MEDIA CAROUSEL", "GENERATED STILL IMAGES",
               carousel={"direction": "horizontal", "advance_seconds": 1.4,
                         "items": [{"image": path} for path in STILLS]}),
        _scene("photo_marquee", "PHOTO MARQUEE", "ALTERNATING ROW CHOREOGRAPHY",
               carousel={"items": [{"image": path} for path in STILLS]}),
        _scene("polaroid_burst", "POLAROID BURST", "FRAME-QUANTIZED ENTRIES",
               polaroid_burst={"photos": STILLS, "seed": 19,
                               "interval": .24, "entry_duration": .2,
                               "flash_duration": .1, "hold_after": .5}),
        _scene("table", "DATA TABLE", "ROW IDS + REORDER + CELL CHANGES",
               columns=[{"id": "system", "label": "SYSTEM", "width": .58, "align": "left"},
                        {"id": "value", "label": "VALUE", "width": .42, "align": "right"}],
               rows=[{"id": "r1", "values": {"system": "SOLAR", "value": "42 kWh"}},
                     {"id": "r2", "values": {"system": "STORAGE", "value": "28 kWh"}},
                     {"id": "r3", "values": {"system": "GRID", "value": "14 kWh"}}],
               highlight_rows=["r2"], animate_from_row_ids=["r3", "r1", "r2"]),
        _scene("bars", "BAR CHART", "ANIMATED RANKING",
               bars=[{"label": "SOLAR", "value": 82},
                     {"label": "STORAGE", "value": 64},
                     {"label": "GRID", "value": 31}],
               data_order="descending"),
        _scene("line_chart", "LINE + AXES", "SYNTHETIC DAILY OUTPUT",
               x_axis_type="category", x_axis_label="DAY",
               y_axis_label="ENERGY (kWh)", y_domain=[0, 100],
               points=[{"label": "MON", "value": 24}, {"label": "TUE", "value": 48},
                       {"label": "WED", "value": 41}, {"label": "THU", "value": 78},
                       {"label": "FRI", "value": 68}]),
        _scene("stacked_bars_100", "100% STACKS", "EXPLICIT CATEGORY TOTALS",
               categories=[
                   {"id": "home", "label": "HOME", "segments": [
                       {"id": "solar", "label": "SOLAR", "value": 68},
                       {"id": "grid", "label": "GRID", "value": 32}]},
                   {"id": "office", "label": "OFFICE", "segments": [
                       {"id": "solar", "label": "SOLAR", "value": 74},
                       {"id": "grid", "label": "GRID", "value": 26}]},
               ]),
        _scene("waterfall", "WATERFALL", "TOTAL CONSERVATION CHECK",
               steps=[{"id": "opening", "label": "START", "value": 40, "kind": "opening"},
                      {"id": "gain", "label": "GAIN", "value": 24, "kind": "delta"},
                      {"id": "use", "label": "USE", "value": -9, "kind": "delta"},
                      {"id": "closing", "label": "END", "value": 55, "kind": "total"}]),
        _scene("diverging_bar", "DIVERGING BARS", "BASELINE = SYNTHETIC TARGET",
               baseline=50, items=[{"label": "A", "value": 72},
                                   {"label": "B", "value": 43},
                                   {"label": "C", "value": 28}]),
        _scene("bullet", "TARGET TRACKING", "BULLET CHART",
               metrics=[{"label": "OUTPUT", "value": 78, "target": 90, "max": 100},
                        {"label": "STORAGE", "value": 56, "target": 70, "max": 100}]),
        _scene("heatmap", "HEATMAP", "SYNTHETIC HOURLY PROFILE",
               row_labels=["MON", "TUE", "WED", "THU"],
               col_labels=["AM", "NOON", "PM"],
               values=[[16, 45, 28], [22, 64, 32], [30, 82, 41], [18, 58, 35]]),
        _scene("scatter", "SCATTER PLOT", "EXPLICIT AXIS DOMAINS",
               x_domain=[0, 10], y_domain=[0, 100],
               points=[{"id": "p1", "x": 1, "y": 18}, {"id": "p2", "x": 3, "y": 39},
                       {"id": "p3", "x": 5, "y": 48}, {"id": "p4", "x": 8, "y": 82}]),
        _scene("funnel", "FUNNEL", "MONOTONIC STAGE VALUES",
               stages=[{"id": "s1", "label": "VISITS", "value": 1000},
                       {"id": "s2", "label": "INTEREST", "value": 620},
                       {"id": "s3", "label": "REQUESTS", "value": 240},
                       {"id": "s4", "label": "CONVERTED", "value": 82}]),
        _scene("sankey", "SANKEY FLOW", "CONSERVATION-PRESERVING LINKS",
               links=[{"source": "SOLAR", "target": "LOAD", "value": 64},
                      {"source": "SOLAR", "target": "STORE", "value": 36},
                      {"source": "GRID", "target": "LOAD", "value": 28},
                      {"source": "STORE", "target": "LOAD", "value": 36}]),
        _scene("chart_morph", "TABLE → BAR MORPH", "SHARED STABLE IDS",
               from_type="table", transition_duration=1.5,
               items=[{"id": "solar", "label": "SOLAR", "from_index": 2,
                       "to_index": 0, "from_value": 30, "to_value": 82},
                      {"id": "store", "label": "STORAGE", "from_index": 1,
                       "to_index": 1, "from_value": 55, "to_value": 64},
                      {"id": "grid", "label": "GRID", "from_index": 0,
                       "to_index": 2, "from_value": 90, "to_value": 31}]),
        _scene("product_3d", "PROCEDURAL 3D", "SYNTHETIC PRISM + LIGHT RIG",
               product_3d={
                   "mesh_path": "procedural-demo.obj",
                   "camera": {"focal_length_mm": 55, "distance": 3.8,
                              "yaw_deg": -22, "turntable_deg_per_s": 12},
                   "lighting": {"key_light": {"intensity": 1.0},
                                "fill_light": {"intensity": .45},
                                "rim_light": {"intensity": .7}},
                   "material": {"color": "#42D6A4"},
               }),
        _scene("spotlight", "MOTION OVER FOOTAGE", "GENERATED CLIP — NO STOCK MEDIA",
               photo=STILLS[2], photo_time=0.0,
               video_layer={"path": VIDEO_B, "x": 60, "y": 740,
                            "w": 600, "h": 300, "mask": "rounded",
                            "radius": 18}),
        _scene("statement", "MECHANISMS", "STAGGER · HOLD · SCALE · MASK",
               typography_motion=TEXT_MOTIONS[1]),
        _scene("statement", "REVIEW", "SYNTHETIC FIVE-MINUTE DEMO"),
    ]
    if len(scenes) != 35:
        raise RuntimeError(f"Expected 35 Studio showcase scenes, got {len(scenes)}")
    if sum(scene["duration"] for scene in scenes) != 280.0:
        raise RuntimeError("Studio showcase segment must be exactly 280 seconds")

    # Demonstrate every object-driven transition once without saturating every
    # cut. Each transition consumes frames inside its scene; it adds no time.
    for boundary, effect in zip(range(2, 22, 2), TRANSITIONS):
        scenes[boundary]["transition_out"] = {
            "type": effect, "duration": .4, "color": "#42D6A4",
            "anchor": [.5, .5], "direction": "left",
        }
    return scenes


def camera_canvas_scenes() -> list[dict]:
    return [
        {"type": "statement", "duration": 5.0, "headline": "CAMERA",
         "subtitle": "SHARED WORLD · SYNTHETIC STILL",
         "photo": STILLS[0],
         "camera_canvas": {"x": 520, "y": 620, "angle": -4, "zoom": 1.0,
                           "layout": "photo-above", "move_duration": .8,
                           "reveal_delay": .15, "reveal_duration": .65,
                           "typography_motion": "mask-rise"}},
        {"type": "statement", "duration": 5.0, "headline": "STOPS",
         "subtitle": "GENERATED VIDEO SOURCE",
         "video": VIDEO_A,
         "camera_canvas": {"x": 1480, "y": 850, "angle": 7, "zoom": 1.0,
                           "layout": "photo-left", "move_duration": 1.0,
                           "reveal_delay": .1, "reveal_duration": .7,
                           "trim_start": .5, "mask": "rounded",
                           "typography_motion": "slide-up"}},
        {"type": "statement", "duration": 5.0, "headline": "TYPE",
         "subtitle": "ROTATION AND SETTLED REVEAL",
         "photo": STILLS[1],
         "camera_canvas": {"x": 2340, "y": 1540, "angle": -5, "zoom": 1.08,
                           "layout": "offset", "move_duration": .9,
                           "reveal_delay": .2, "reveal_duration": .6,
                           "typography_motion": "scale-focus"}},
        {"type": "statement", "duration": 5.0, "headline": "TOUR",
         "subtitle": "FOURTH SHOT · FINAL CAMERA STOP",
         "photo": STILLS[3],
         "camera_canvas": {"x": 3200, "y": 1100, "angle": 3, "zoom": 1.0,
                           "layout": "photo-left", "move_duration": .85,
                           "reveal_delay": .12, "reveal_duration": .7}},
    ]


def write_manifests(brand_root: Path = BRAND_ROOT) -> tuple[Path, Path]:
    projects = brand_root / "projects"
    projects.mkdir(parents=True, exist_ok=True)
    studio_path = projects / "studio-showcase-280s.json"
    camera_path = projects / "camera-canvas-showcase-20s.json"
    base = {
        "brand": BRAND,
        "style": "editorial-premium",
        "design_overrides": {"body": 38},
        "video": {"width": 720, "height": 1280, "fps": 30},
        "export": {"profile": "review", "codec": "libx264",
                    "crf": 20, "preset": "medium"},
    }
    studio_path.write_text(json.dumps({
        **base, "name": "motion-lab-studio-showcase",
        "scenes": studio_scenes(),
        "metadata": {"synthetic_demo": True,
                     "duration_seconds": 280,
                     "notice": "Illustrative engine demo; not an advertisement."},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    camera_path.write_text(json.dumps({
        **base, "name": "motion-lab-camera-canvas-showcase",
        "scenes": camera_canvas_scenes(),
        "metadata": {"synthetic_demo": True,
                     "duration_seconds": 20,
                     "notice": "Illustrative engine demo; not an advertisement."},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return studio_path, camera_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand-root", type=Path, default=BRAND_ROOT)
    args = parser.parse_args()
    studio_path, camera_path = write_manifests(args.brand_root)
    print(json.dumps({"studio_manifest": str(studio_path),
        "studio_duration_seconds": 280,
                      "camera_canvas_manifest": str(camera_path),
        "camera_canvas_duration_seconds": 20,
                      "total_duration_seconds": 300}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
