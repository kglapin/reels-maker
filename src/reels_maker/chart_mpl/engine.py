"""Deterministic matplotlib chart-frame renderer.

Each supported chart scene is rasterized to ``ceil(duration*fps)`` RGBA PNGs
at twice the layout resolution, cached on disk by a content hash, and exposed
to builders as a ``sequence`` node. Frame *t* is a pure function of the scene
spec — no wall-clock dependence — so renders stay reproducible.
"""
from __future__ import annotations

import hashlib
import json
import math
import tempfile
from pathlib import Path

from ..components.chart_style import chart_colors

SUPPORTED = {"line_chart", "bars", "waterfall", "bullet", "heatmap",
             "funnel", "donut", "diverging_bar", "scatter"}

_ENGINE_VERSION = 1
_SUPERSAMPLE = 2


def _hex(color) -> str:
    r, g, b = (int(c) for c in color[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


def _palette(theme: dict) -> dict:
    colors = chart_colors(theme)
    pal = {}
    for key, value in colors.items():
        if key == "series" and isinstance(value, (tuple, list)):
            pal[key] = [_hex(item) for item in value]
        else:
            pal[key] = _hex(value)
    return pal


def _cache_dir(scene: dict, width: int, height: int, duration: float,
               fps: int, theme: dict) -> Path:
    payload = {
        "engine": _ENGINE_VERSION,
        "scene": scene,
        "size": [width, height],
        "duration": duration,
        "fps": fps,
        "theme": theme,
    }
    key = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:24]
    root = Path(tempfile.gettempdir()) / "reels-maker" / "chart-mpl"
    return root / key


def frame_paths(scene: dict, theme: dict, width: int, height: int,
                duration: float, fps: int,
                fonts: dict | None = None) -> list[str] | None:
    """Return cached PNG frame paths for a supported chart scene.

    ``width``/``height`` are layout pixels; frames render at 2x and the
    sequence node downscales via ``cover``. Returns ``None`` for unsupported
    scene types so callers can fall back to the native builders.
    """
    kind = scene.get("type") or scene.get("composition")
    if kind not in SUPPORTED:
        return None
    chart_w = max(64, int(round(width * _SUPERSAMPLE)))
    chart_h = max(64, int(round(height * _SUPERSAMPLE)))
    count = max(1, int(math.ceil(duration * fps)))
    out_dir = _cache_dir(scene, chart_w, chart_h, duration, fps, theme)
    done_marker = out_dir / ".complete"
    if done_marker.is_file():
        frames = sorted(out_dir.glob("frame_*.png"))
        if len(frames) >= count:
            return [str(path) for path in frames[:count]]
    out_dir.mkdir(parents=True, exist_ok=True)
    _render_all(kind, scene, theme, chart_w, chart_h, count, fps,
                out_dir, fonts or {})
    done_marker.write_text("ok")
    frames = sorted(out_dir.glob("frame_*.png"))
    return [str(path) for path in frames[:count]]


# ---------------------------------------------------------------------------
# matplotlib plumbing
# ---------------------------------------------------------------------------

def _setup_matplotlib(fonts: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    families = []
    for weight in ("regular", "bold"):
        path = fonts.get(weight)
        if path and Path(path).is_file():
            try:
                font_manager.fontManager.addfont(str(path))
                families.append(font_manager.FontProperties(
                    fname=str(path)).get_name())
            except Exception:
                continue
    if families:
        plt.rcParams["font.family"] = families[0]
    plt.rcParams.update({
        "text.parse_math": False,
        "axes.unicode_minus": False,
    })
    return plt


def _new_figure(plt, width: int, height: int):
    fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
    fig.patch.set_alpha(0.0)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("none")
    ax.axis("off")
    return fig, ax


def _save(fig, path: Path) -> None:
    fig.savefig(path, dpi=100, transparent=True, pad_inches=0,
                facecolor="none")


def _ease_out(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


def _stagger(t: float, count: int, start: float = .12,
             step: float = .07) -> list[float]:
    """Per-item progress values 0..1 staggered across the timeline."""
    span = max(.2, 1.0 - start - step * max(0, count - 1) - .1)
    out = []
    for i in range(count):
        local = (t - start - i * step) / span
        out.append(max(0.0, min(1.0, _ease_out(local))))
    return out


# ---------------------------------------------------------------------------
# chart drawers — each receives normalized progress values in [0,1]
# ---------------------------------------------------------------------------

def _draw_card(ax, width: int, height: int, pal: dict) -> None:
    "-light rounded chart card matching chart_card() proportions."""
    from matplotlib.patches import FancyBboxPatch
    card = FancyBboxPatch(
        (width * .015, height * .015), width * .97, height * .97,
        boxstyle="round,pad=0,rounding_size=%f" % (width * .035),
        linewidth=1.2, edgecolor=pal["border"], facecolor=pal["plot"],
        zorder=0)
    ax.add_patch(card)


def _fmt(value: float, decimals: int = 0) -> str:
    if decimals <= 0:
        return f"{value:,.0f}".replace(",", " ")
    return f"{value:,.{decimals}f}".replace(",", " ")


def _chart_frame(kind: str, scene: dict, theme: dict, width: int,
                 height: int, t: float, duration: float,
                 fonts: dict, pal: dict, plt) -> None:
    fig, ax = _new_figure(plt, width, height)
    _draw_card(ax, width, height, pal)
    draw = _DRAWERS.get(kind)
    if draw is None:
        plt.close(fig)
        return
    draw(ax, scene, width, height, t, duration, pal, plt)
    _save(fig, _CURRENT_FRAME[0])
    plt.close(fig)


_CURRENT_FRAME: list[Path] = [Path()]


def _render_all(kind: str, scene: dict, theme: dict, width: int,
                height: int, count: int, fps: int, out_dir: Path,
                fonts: dict) -> None:
    plt = _setup_matplotlib(fonts)
    pal = _palette(theme)
    duration = count / fps
    font_regular = fonts.get("regular")
    font_bold = fonts.get("bold")
    for index in range(count):
        _CURRENT_FRAME[0] = out_dir / f"frame_{index:04d}.png"
        _chart_frame(kind, scene, theme, width, height,
                     index / fps, duration, fonts, pal, plt)
    # keep references for potential reuse
    _ = (font_regular, font_bold)


# -- individual drawers -------------------------------------------------------
# All coordinates are in pixel units of the 2x frame. `t` is scene seconds.

def _draw_bars(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    data = scene.get("bars") or scene.get("data") or []
    items = [{"label": str(i.get("label", "")),
              "value": float(i.get("value", 0) or 0),
              "suffix": str(i.get("suffix", "")),
              "prefix": str(i.get("prefix", ""))} for i in data]
    if not items:
        return
    n = len(items)
    max_v = max(i["value"] for i in items) or 1
    left, right = w * .04, w * .97
    top, bottom = h * .10, h * .93
    label_w = (right - left) * .60
    track_h = min(h * .075, (bottom - top) / n * .34)
    progresses = _stagger(t / dur, n, start=.10, step=.06)
    for i, item in enumerate(items):
        p = progresses[i]
        y = top + i * (bottom - top) / n + ((bottom - top) / n - track_h) / 2
        frac = item["value"] / max_v
        # track
        ax.add_patch(mpatches.Rectangle((left, y), right - left, track_h,
                                   facecolor=pal["grid"], edgecolor="none",
                                   zorder=1))
        # bar with rounded ends via FancyBboxPatch
        from matplotlib.patches import FancyBboxPatch
        bar_w = max(4.0, (right - left) * frac * p)
        if bar_w > 2:
            ax.add_patch(FancyBboxPatch(
                (left, y), bar_w, track_h,
                boxstyle=f"round,pad=0,rounding_size={track_h / 2}",
                facecolor=pal["accent"], edgecolor="none", zorder=2,
                alpha=.55 + .45 * (1 if i == 0 else .82)))
        fs = h * .032
        ax.text(left, y + track_h * .5, item["label"].upper(),
                va="center", ha="left", fontsize=fs,
                color=pal["axis"], fontweight="bold",
                transform=ax.transData)
        shown = item["value"] * p
        txt = item["prefix"] + _fmt(shown) + item["suffix"]
        ax.text(right, y + track_h * .5, txt, va="center", ha="right",
                fontsize=fs * 1.15, color=pal["accent"],
                fontweight="bold")


def _draw_line_chart(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    points = scene.get("points") or []
    if len(points) < 2:
        return
    import numpy as np
    labels = [str(p.get("label", "")) for p in points]
    values = [float(p.get("value", 0) or 0) for p in points]
    dom = scene.get("y_domain") or [min(values), max(values) or 1]
    lo, hi = float(dom[0]), float(dom[1])
    if hi <= lo:
        hi = lo + 1
    left, right = w * .10, w * .97
    top, bottom = h * .10, h * .86
    pw, ph = right - left, bottom - top
    xs = np.linspace(left, right, len(values))
    ys = bottom - (np.array(values) - lo) / (hi - lo) * ph
    # grid + ticks
    for i in range(5):
        gy = bottom - ph * i / 4
        ax.plot([left, right], [gy, gy], color=pal["grid"],
                linewidth=max(1, w * .0018), zorder=1)
        tick = lo + (hi - lo) * i / 4
        ax.text(left - w * .012, gy, _fmt(tick), va="center", ha="right",
                fontsize=h * .026, color=pal["muted"])
    # draw-on progress
    p = _ease_out(min(1.0, max(0.0, (t / dur - .10) / .55)))
    n_pts = max(2, int(round(len(xs) * p)))
    if n_pts < 2:
        return
    xd, yd = xs[:n_pts], ys[:n_pts]
    # Catmull-Rom smoothing on the revealed prefix (no scipy dependency)
    if n_pts >= 3:
        xs_d = np.concatenate([[xs[0]], xs[:n_pts], [xs[n_pts - 1]]])
        ys_d = np.concatenate([[ys[0]], ys[:n_pts], [ys[n_pts - 1]]])
        dense_x, dense_y = [], []
        for seg in range(n_pts):
            px_ = (xs_d[seg], xs_d[seg + 1], xs_d[seg + 2], xs_d[seg + 3])
            py_ = (ys_d[seg], ys_d[seg + 1], ys_d[seg + 2], ys_d[seg + 3])
            for step in range(6):
                tt = step / 6
                tt2, tt3 = tt * tt, tt * tt * tt
                dense_x.append(.5 * ((2 * px_[1]) + (-px_[0] + px_[2]) * tt
                    + (2 * px_[0] - 5 * px_[1] + 4 * px_[2] - px_[3]) * tt2
                    + (-px_[0] + 3 * px_[1] - 3 * px_[2] + px_[3]) * tt3))
                dense_y.append(.5 * ((2 * py_[1]) + (-py_[0] + py_[2]) * tt
                    + (2 * py_[0] - 5 * py_[1] + 4 * py_[2] - py_[3]) * tt2
                    + (-py_[0] + 3 * py_[1] - 3 * py_[2] + py_[3]) * tt3))
        xd = np.array(dense_x)
        yd = np.array(dense_y)
    # area fill with vertical alpha gradient feel: two fills
    ax.fill_between(xd, yd, bottom, color=pal["accent"], alpha=.16,
                    zorder=2)
    ax.plot(xd, yd, color=pal["accent"], linewidth=max(2.5, w * .008),
            solid_capstyle="round", zorder=3)
    # dots at revealed points
    for x, y in zip(xs[:n_pts], ys[:n_pts]):
        ax.scatter([x], [y], s=w * .0016, color=pal["plot"],
                   edgecolors=pal["accent"], linewidths=max(1.5, w * .003),
                   zorder=4)
        ax.scatter([x], [y], s=w * .0007, color=pal["accent"], zorder=5)
    # latest value label
    lv = values[-1] * min(1.0, p * 1.15)
    ax.text(right, min(ys[-1], bottom) - h * .03,
            _fmt(values[-1]), va="bottom", ha="right",
            fontsize=h * .034, color=pal["accent"], fontweight="bold")
    for i, lab in enumerate(labels):
        ax.text(xs[i], bottom + h * .02, lab, va="top", ha="center",
                fontsize=h * .024, color=pal["muted"],
                rotation=0)


def _draw_waterfall(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    steps = scene.get("steps") or []
    parsed = []
    running = 0.0
    for idx, st in enumerate(steps):
        kind = str(st.get("kind", "delta" if 0 < idx < len(steps) - 1 else "total"))
        val = float(st.get("value", 0) or 0)
        if idx == 0:
            start, end = 0.0, val
            running = val
        elif kind == "total" or idx == len(steps) - 1:
            start, end = 0.0, val
        else:
            start, end = running, running + val
            running = end
        parsed.append({"label": str(st.get("label", "")), "value": val,
                       "kind": kind, "start": start, "end": end})
    if not parsed:
        return
    allv = [0.0] + [p["start"] for p in parsed] + [p["end"] for p in parsed]
    lo, hi = min(allv), max(allv)
    span = max(1e-6, hi - lo)
    lo -= span * .08
    hi += span * .12
    span = hi - lo
    left, right = w * .07, w * .98
    top, bottom = h * .08, h * .90
    slot = (right - left) / len(parsed)
    bar_w = slot * .58
    prog = _stagger(t / dur, len(parsed), start=.08, step=.08)
    zero_y = bottom - (0 - lo) / span * (bottom - top)
    ax.axhline(zero_y, color=pal["hairline"], linewidth=max(1, w * .0015),
               zorder=1)
    for i, item in enumerate(parsed):
        p = prog[i]
        x = left + i * slot + (slot - bar_w) / 2
        y_top = bottom - (max(item["start"], item["end"]) - lo) / span * (bottom - top)
        y_bot = bottom - (min(item["start"], item["end"]) - lo) / span * (bottom - top)
        h_bar = max(3.0, (y_bot - y_top) * p)
        # grow upward from the lower edge
        if item["end"] >= item["start"]:
            y0 = y_bot - h_bar
        else:
            y0 = y_bot
        color = pal["axis"] if item["kind"] in ("opening", "total") else (
            pal["series"][2] if item["value"] >= 0 else "#f87171")
        ax.add_patch(mpatches.Rectangle((x, y0), bar_w, h_bar,
                                   facecolor=color, edgecolor="none",
                                   zorder=2))
        # connector to next
        if i + 1 < len(parsed) and p > .9:
            lvl = bottom - (item["end"] - lo) / span * (bottom - top)
            nx = left + (i + 1) * slot + (slot - bar_w) / 2
            ax.plot([x + bar_w, nx], [lvl, lvl], color=pal["hairline"],
                    linewidth=max(1, w * .0015), zorder=1)
        # value label
        sign = "+" if item["kind"] == "delta" and item["value"] > 0 else (
            "−" if item["kind"] == "delta" and item["value"] < 0 else "")
        ax.text(x + bar_w / 2, y_top - h * .015,
                f"{sign}{_fmt(abs(item['value']))}",
                ha="center", va="bottom", fontsize=h * .028,
                color=pal["axis"], fontweight="bold")
        ax.text(x + bar_w / 2, bottom + h * .015, item["label"],
                ha="center", va="top", fontsize=h * .026,
                color=pal["muted"], fontweight="bold")


def _draw_bullet(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    metrics = scene.get("metrics") or scene.get("items") or []
    items = [{"label": str(m.get("label", "")),
              "value": float(m.get("value", 0) or 0),
              "target": float(m.get("target", 0) or 0),
              "max": float(m.get("max", 1) or 1)} for m in metrics]
    if not items:
        return
    left, right = w * .26, w * .97
    top, bottom = h * .10, h * .92
    row_h = (bottom - top) / len(items)
    prog = _stagger(t / dur, len(items), start=.10, step=.09)
    for i, item in enumerate(items):
        p = prog[i]
        y = top + i * row_h
        track_h = min(h * .075, row_h * .5)
        ty = y + (row_h - track_h) / 2
        ax.add_patch(mpatches.Rectangle((left, ty), right - left, track_h,
                                   facecolor=pal["grid"], edgecolor="none",
                                   zorder=1))
        val_w = (right - left) * min(1.0, item["value"] / item["max"]) * p
        from matplotlib.patches import FancyBboxPatch
        if val_w > 2:
            ax.add_patch(FancyBboxPatch(
                (left, ty + track_h * .18), val_w, track_h * .64,
                boxstyle=f"round,pad=0,rounding_size={track_h * .32}",
                facecolor=pal["accent"], edgecolor="none", zorder=2))
        if p > .85:
            tx = left + (right - left) * min(1.0, item["target"] / item["max"])
            ax.plot([tx, tx], [ty - h * .01, ty + track_h + h * .01],
                    color=pal["axis"], linewidth=max(2, w * .005),
                    zorder=3)
            ax.text(right + w * .005, ty + track_h / 2,
                    _fmt(item["value"] * min(1.0, p)),
                    va="center", ha="left", fontsize=h * .030,
                    color=pal["accent"], fontweight="bold")
        ax.text(left - w * .015, ty + track_h / 2, item["label"],
                va="center", ha="right", fontsize=h * .028,
                color=pal["axis"], fontweight="bold")


def _draw_heatmap(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    rows = scene.get("row_labels") or []
    cols = scene.get("col_labels") or []
    matrix = scene.get("values") or []
    if not rows or not cols or not matrix:
        return
    flat = [float(v) for row in matrix for v in row]
    lo, hi = min(flat), max(flat)
    span = max(1e-6, hi - lo)
    left, right = w * .22, w * .98
    top, bottom = h * .10, h * .94
    cw = (right - left) / len(cols)
    ch = (bottom - top) / len(rows)
    prog = _stagger(t / dur, len(rows) * len(cols), start=.08, step=.012)
    idx = 0
    for r_i, row in enumerate(matrix):
        for c_i, raw in enumerate(row):
            val = float(raw)
            frac = (val - lo) / span
            p = prog[idx]
            idx += 1
            # interpolate plot -> series[0]
            base = tuple(int(c, 16) for c in (pal["plot"][1:3],
                                              pal["plot"][3:5],
                                              pal["plot"][5:7]))
            top_c = tuple(int(c, 16) for c in (pal["series"][0][1:3],
                                               pal["series"][0][3:5],
                                               pal["series"][0][5:7]))
            mixc = tuple(int(base[k] + (top_c[k] - base[k]) * (.15 + .75 * frac))
                         for k in range(3))
            color = "#%02x%02x%02x" % mixc
            cx = left + c_i * cw + w * .006
            cy = top + r_i * ch + h * .006
            cw_px = cw - w * .012
            ch_px = ch - h * .012
            from matplotlib.patches import FancyBboxPatch
            alpha = p
            ax.add_patch(FancyBboxPatch(
                (cx, cy), cw_px * p, ch_px, boxstyle="round,pad=0,rounding_size=6",
                facecolor=color, edgecolor="none", alpha=alpha, zorder=2))
            if p > .8:
                lum = sum(mixc) / 3
                tx_col = "#ffffff" if lum < 140 else "#111111"
                ax.text(cx + cw_px / 2, cy + ch_px / 2, _fmt(val),
                        ha="center", va="center", fontsize=h * .030,
                        color=tx_col, fontweight="bold")
    # headers
    for c_i, lab in enumerate(cols):
        ax.text(left + c_i * cw + cw / 2, top - h * .015, str(lab),
                ha="center", va="bottom", fontsize=h * .026,
                color=pal["muted"], fontweight="bold")
    for r_i, lab in enumerate(rows):
        ax.text(left - w * .015, top + r_i * ch + ch / 2, str(lab),
                ha="right", va="center", fontsize=h * .026,
                color=pal["muted"], fontweight="bold")


def _draw_funnel(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    stages = scene.get("stages") or []
    items = [{"label": str(s.get("label", "")),
              "value": float(s.get("value", 0) or 0)} for s in stages]
    if len(items) < 2:
        return
    top_val = items[0]["value"] or 1
    left, right = w * .10, w * .90
    top, bottom = h * .08, h * .94
    row_h = (bottom - top) / len(items)
    prog = _stagger(t / dur, len(items), start=.08, step=.10)
    for i, item in enumerate(items):
        p = prog[i]
        share = item["value"] / top_val
        bar_w = max((right - left) * .16, (right - left) * share) * p
        x = (left + right) / 2 - bar_w / 2
        y = top + i * row_h + row_h * .10
        bh = row_h * .72
        from matplotlib.patches import FancyBboxPatch
        # color fades toward surface for later stages
        ax.add_patch(FancyBboxPatch(
            (x, y), bar_w, bh,
            boxstyle=f"round,pad=0,rounding_size={min(bh * .3, w * .02)}",
            facecolor=pal["accent"], edgecolor="none", alpha=.95 - i * .12,
            zorder=2))
        if p > .7:
            ax.text((left + right) / 2, y + bh / 2,
                    f"{item['label']}  ·  {round(share * 100)}%",
                    ha="center", va="center", fontsize=h * .032,
                    color="#ffffff", fontweight="bold")
        if i + 1 < len(items) and p > .9:
            sep_y = top + (i + 1) * row_h
            ax.plot([x + bar_w / 2 - bar_w * .3, x + bar_w / 2 + bar_w * .3],
                    [sep_y, sep_y], color=pal["hairline"],
                    linewidth=max(1, w * .0015), zorder=1)


def _draw_diverging(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    baseline = float(scene.get("baseline", 0) or 0)
    raw = scene.get("items") or scene.get("bars") or []
    items = [{"label": str(i.get("label", "")),
              "delta": float(i.get("value", 0) or 0) - baseline}
             for i in raw]
    if not items:
        return
    max_abs = max(abs(i["delta"]) for i in items) or 1
    left, right = w * .26, w * .97
    top, bottom = h * .08, h * .94
    mid_x = (left + right) / 2
    half = (right - left) / 2 * .94
    row_h = (bottom - top) / len(items)
    prog = _stagger(t / dur, len(items), start=.10, step=.08)
    ax.plot([mid_x, mid_x], [top, bottom], color=pal["axis"],
            linewidth=max(1.5, w * .004), zorder=2)
    for i, item in enumerate(items):
        p = prog[i]
        y = top + i * row_h
        bar_h = row_h * .5
        bar_w = half * abs(item["delta"]) / max_abs * p
        x0 = mid_x if item["delta"] >= 0 else mid_x - bar_w
        from matplotlib.patches import FancyBboxPatch
        color = pal["accent"] if item["delta"] >= 0 else "#f87171"
        ax.add_patch(FancyBboxPatch(
            (x0, y + (row_h - bar_h) / 2), max(2.0, bar_w), bar_h,
            boxstyle=f"round,pad=0,rounding_size={bar_h * .5}",
            facecolor=color, edgecolor="none", zorder=3))
        ax.text(left - w * .015, y + row_h / 2, item["label"],
                va="center", ha="right", fontsize=h * .028,
                color=pal["axis"], fontweight="bold")


def _draw_scatter(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    pts = scene.get("points") or []
    if len(pts) < 2:
        return
    xd = scene.get("x_domain") or [0, 1]
    yd = scene.get("y_domain") or [0, 1]
    x0, x1 = float(xd[0]), float(xd[1])
    y0, y1 = float(yd[0]), float(yd[1])
    left, right = w * .14, w * .97
    top, bottom = h * .08, h * .92
    pw, ph = right - left, bottom - top
    for i in range(5):
        gy = bottom - ph * i / 4
        gx = left + pw * i / 4
        ax.plot([left, right], [gy, gy], color=pal["grid"],
                linewidth=max(1, w * .0015), zorder=1)
        ax.plot([gx, gx], [top, bottom], color=pal["grid"],
                linewidth=max(1, w * .0015), zorder=1)
        ax.text(left - w * .012, gy, _fmt(y0 + (y1 - y0) * i / 4),
                va="center", ha="right", fontsize=h * .024,
                color=pal["muted"])
        ax.text(gx, bottom + h * .015, _fmt(x0 + (x1 - x0) * i / 4),
                va="top", ha="center", fontsize=h * .024,
                color=pal["muted"])
    prog = _stagger(t / dur, len(pts), start=.10, step=.05)
    for i, pt in enumerate(pts):
        xv, yv = float(pt.get("x", 0)), float(pt.get("y", 0))
        px = left + (xv - x0) / (x1 - x0) * pw
        py = bottom - (yv - y0) / (y1 - y0) * ph
        p = prog[i]
        if p <= 0:
            continue
        ax.scatter([px], [py], s=w * .0022 * p, color=pal["accent"],
                   edgecolors=pal["plot"], linewidths=max(1.5, w * .003),
                   zorder=3)


def _draw_donut(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    cx, cy = w / 2, h * .46
    radius = min(w, h) * .36
    width_pt = radius * .26
    segments = scene.get("segments")
    track = mpatches.Circle((cx, cy), radius, fill=False,
                       edgecolor=pal["hairline"], linewidth=width_pt,
                       zorder=1)
    ax.add_patch(track)
    if isinstance(segments, list) and len(segments) >= 2:
        vals = [float(s.get("value", 0) or 0) for s in segments]
        total = sum(vals) or 1
        prog = _stagger(t / dur, len(segments), start=.12, step=.10)
        start_deg = 90.0
        for i, seg in enumerate(segments):
            share = vals[i] / total
            sweep = 360 * share * prog[i]
            color = pal["series"][(i) % len(pal["series"])]
            if sweep > .5:
                wedge = mpatches.Wedge(
                    (cx, cy), radius, start_deg - sweep, start_deg,
                    width=width_pt, facecolor=color, edgecolor="none",
                    zorder=2)
                ax.add_patch(wedge)
            start_deg -= 360 * share
        # legend
        n = len(segments)
        lw = w / n
        for i, seg in enumerate(segments):
            lx = w * .06 + i * (w * .88 / n)
            from matplotlib.patches import FancyBboxPatch
            ax.add_patch(FancyBboxPatch(
                (lx, h * .86), w * .02, h * .028,
                boxstyle="round,pad=0,rounding_size=4",
                facecolor=pal["series"][i % len(pal["series"])],
                edgecolor="none", zorder=2))
            ax.text(lx + w * .028, h * .874, str(seg.get("label", "")),
                    va="center", ha="left", fontsize=h * .026,
                    color=pal["muted"])
    else:
        pct = float(scene.get("value", scene.get("percent", 0)) or 0)
        p = _ease_out(min(1.0, max(0.0, (t / dur - .10) / .6)))
        sweep = 360 * (pct / 100.0) * p
        if sweep > .5:
            wedge = mpatches.Wedge(
                (cx, cy), radius, 90 - sweep, 90, width=width_pt,
                facecolor=pal["accent"], edgecolor="none", zorder=2)
            ax.add_patch(wedge)
        # center number counts up
    shown = float(scene.get("value", scene.get("percent", 0)) or 0)
    count_p = _ease_out(min(1.0, max(0.0, (t / dur - .15) / .7)))
    ax.text(cx, cy, f"{shown * count_p:,.0f}%", ha="center", va="center",
            fontsize=h * .075, color=pal["axis"], fontweight="bold",
            zorder=3)
    label = str(scene.get("label", ""))
    if label:
        ax.text(cx, cy - radius * .34, label.upper(), ha="center",
                va="center", fontsize=h * .028, color=pal["muted"],
                fontweight="bold")


_DRAWERS = {
    "bars": _draw_bars,
    "line_chart": _draw_line_chart,
    "waterfall": _draw_waterfall,
    "bullet": _draw_bullet,
    "heatmap": _draw_heatmap,
    "funnel": _draw_funnel,
    "diverging_bar": _draw_diverging,
    "scatter": _draw_scatter,
    "donut": _draw_donut,
}


def sequence_node(ctx, scene: dict, theme: dict, rect,
                    role: str = "chart") -> "Node | None":
    """Build a ``sequence`` node covering ``rect`` with mpl chart frames.

    Returns ``None`` when the scene type is unsupported or matplotlib is
    unavailable, so callers fall back to the native vector builders.
    """
    try:
        frames = frame_paths(
            scene, theme,
            width=max(64, int(round(rect.w))),
            height=max(64, int(round(rect.h))),
            duration=float(ctx.duration), fps=int(ctx.fps),
            fonts=_font_paths(ctx))
    except Exception:
        return None
    if not frames:
        return None
    from ..core.scene_graph import Node
    return Node(
        kind="sequence", role=role,
        props={"frames": frames, "fps": float(ctx.fps), "start": 0.0,
               "speed": 1.0, "x": rect.x, "y": rect.y,
               "w": rect.w, "h": rect.h},
        qa_class="control",
        meta={"component": "mpl-" + str(scene.get("type"))})


def _font_paths(ctx) -> dict:
    fonts = getattr(ctx, "fonts", None)
    paths = {}
    if fonts is None:
        return paths
    for weight in ("regular", "bold"):
        try:
            path = fonts.path(weight)
            if path:
                paths[weight] = str(path)
        except Exception:
            continue
    return paths
