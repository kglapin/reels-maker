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
             "funnel", "donut", "diverging_bar", "scatter",
             "stacked_bars_100"}

_ENGINE_VERSION = 11
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
        # Pass the deduped family list so fontweight="bold" can resolve the
        # bold face registered from the bold TTF, not just the first family.
        plt.rcParams["font.family"] = list(dict.fromkeys(families))
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
    # axison must stay True: axis("off") suppresses ALL artists (patches,
    # lines, text), which is what made early frames fully transparent.
    # Instead hide decorations and map data coords 1:1 onto top-left-origin
    # pixel space (y grows downward, matching the native builders).
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    return fig, ax


def _save(fig, path: Path) -> None:
    fig.savefig(path, dpi=100, transparent=True, pad_inches=0,
                facecolor="none")


def _ease_out(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


def _stagger(t: float, count: int, start: float = .12,
             step: float = .07) -> list[float]:
    """Per-item progress values 0..1 staggered across the timeline.

    ``step`` is a *preference*: when ``count`` is large (e.g. a dense
    heatmap) the effective step shrinks so the last item still starts
    inside the animation window instead of never appearing.
    """
    window = max(.15, 1.0 - start - .10)
    step_eff = step if count <= 1 else min(step, window * .55 / (count - 1))
    span = max(.12, window - step_eff * max(0, count - 1))
    out = []
    for i in range(count):
        local = (t - start - i * step_eff) / span
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


def _num(value, default: float = 0.0) -> float:
    """Coerce manifest values to a finite float; NaN/inf/garbage -> default."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def _fmt(value: float, decimals: int = 0) -> str:
    if decimals <= 0:
        return f"{value:,.0f}".replace(",", " ")
    return f"{value:,.{decimals}f}".replace(",", " ")


def _reset_axes(ax, width: int, height: int) -> None:
    """Clear a reused axes and re-apply the pixel-space decoration state."""
    ax.clear()
    ax.set_facecolor("none")
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def _chart_frame(kind: str, scene: dict, theme: dict, width: int,
                 height: int, t: float, duration: float,
                 fonts: dict, pal: dict, plt, fig=None, ax=None) -> None:
    if fig is None or ax is None:
        fig, ax = _new_figure(plt, width, height)
    else:
        _reset_axes(ax, width, height)
    _draw_card(ax, width, height, pal)
    draw = _DRAWERS.get(kind)
    if draw is None:
        if fig is not None:
            plt.close(fig)
        return
    draw(ax, scene, width, height, t, duration, pal, plt)
    _save(fig, _CURRENT_FRAME[0])


_CURRENT_FRAME: list[Path] = [Path()]


def _render_all(kind: str, scene: dict, theme: dict, width: int,
                height: int, count: int, fps: int, out_dir: Path,
                fonts: dict) -> None:
    plt = _setup_matplotlib(fonts)
    pal = _palette(theme)
    duration = count / fps
    fig, ax = _new_figure(plt, width, height)
    try:
        for index in range(count):
            _CURRENT_FRAME[0] = out_dir / f"frame_{index:04d}.png"
            _chart_frame(kind, scene, theme, width, height,
                         index / fps, duration, fonts, pal, plt,
                         fig=fig, ax=ax)
    finally:
        plt.close(fig)


# -- individual drawers -------------------------------------------------------
# All coordinates are in pixel units of the 2x frame. `t` is scene seconds.
#
# Shared geometry + type scale. Frames render at 2x and display at 0.5x, so a
# font size in points maps to screen px as ``pt * 100/72 * 0.5 ≈ pt * 0.694`` —
# independent of region size. These constants therefore hold the same visual
# size in every chart scene and match the native builders' axis/value roles.
FS_TICK = 23      # ~16px — axis ticks, grid labels, headers
FS_LABEL = 26     # ~18px — category labels, legend, cell headers
FS_VALUE = 30     # ~21px — data values, latest-point callouts
FS_MICRO = 21     # ~15px — secondary annotations

# Cartesian plot frame (fractions of frame w/h). Left gutter reserves room for
# right-aligned axis labels; right/top/bottom keep clear of the card edge.
PLOT_L, PLOT_R, PLOT_T, PLOT_B = .17, .95, .11, .86
# X-axis category labels sit just below PLOT_B.
XLABEL_DY = .028


def _text_frac(text: str, fs_pt: float, w: float) -> float:
    """Rough rendered width of ``text`` as a fraction of frame width."""
    return len(str(text)) * fs_pt * 0.55 * (100 / 72) / max(1.0, w)


def _clip(text: str, fs_pt: float, max_frac: float, w: float) -> str:
    """Truncate ``text`` with an ellipsis so it fits ``max_frac`` of width."""
    text = str(text)
    if _text_frac(text, fs_pt, w) <= max_frac:
        return text
    budget = max(1, int(max_frac * w / (fs_pt * 0.55 * (100 / 72))) - 3)
    return text[:budget].rstrip() + "..."


def _fit_fs(text: str, fs_max: float, box_w: float, box_h: float) -> float:
    """Largest font size (pt) whose estimated glyphs fit ``box_w``×``box_h`` px.

    Average glyph advance ≈ 0.55em and cap height ≈ 0.72em; at dpi=100 a
    point is 100/72 px, so 0.72em * 100/72 ≈ 1.0 px per pt of cap height.
    """
    text = str(text)
    if not text or box_w <= 0 or box_h <= 0:
        return fs_max
    px_per_pt = 100 / 72
    w_lim = box_w * .85 / (len(text) * .55 * px_per_pt)
    h_lim = box_h * .75
    return max(9.0, min(fs_max, w_lim, h_lim))


def _draw_bars(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    data = scene.get("bars") or scene.get("data") or []
    items = [{"label": str(i.get("label", "")),
              "value": _num(i.get("value", 0)),
              "suffix": str(i.get("suffix", "")),
              "prefix": str(i.get("prefix", ""))} for i in data]
    if not items:
        return
    order = scene.get("data_order", "source")
    if order in ("ascending", "descending"):
        indexed = list(enumerate(items))
        indexed.sort(key=(lambda pair: (-pair[1]["value"], pair[0]))
                     if order == "descending" else
                     (lambda pair: (pair[1]["value"], pair[0])))
        items = [item for _, item in indexed]
    n = len(items)
    max_v = max(max(i["value"] for i in items), 0.0) or 1
    label_x = (PLOT_L - .015) * w
    left, right = PLOT_L * w, PLOT_R * w
    top, bottom = PLOT_T * h, h * .90
    track_h = min(h * .075, (bottom - top) / n * .34)
    progresses = _stagger(t / dur, n, start=.10, step=.06)
    for i, item in enumerate(items):
        p = progresses[i]
        y = top + i * (bottom - top) / n + ((bottom - top) / n - track_h) / 2
        frac = min(1.0, max(0.0, item["value"] / max_v))
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
        ax.text(label_x, y + track_h * .5,
                _clip(item["label"].upper(), FS_LABEL, label_x - w * .035, w),
                va="center", ha="right", fontsize=FS_LABEL,
                color=pal["axis"], fontweight="bold",
                transform=ax.transData)
        shown = item["value"] * p
        txt = item["prefix"] + _fmt(shown) + item["suffix"]
        from matplotlib import patheffects as pe
        ax.text(right, y + track_h * .5, txt, va="center", ha="right",
                fontsize=FS_VALUE, color=pal["accent"],
                fontweight="bold",
                path_effects=[pe.withStroke(linewidth=3.5,
                                            foreground=pal["plot"])])


def _draw_line_chart(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    points = scene.get("points") or []
    if len(points) < 2:
        return
    import numpy as np
    labels = [str(p.get("label", "")) for p in points]
    values = [_num(p.get("value", 0)) for p in points]
    dom = scene.get("y_domain") or [min(values), max(values) or 1]
    lo, hi = float(dom[0]), float(dom[1])
    if hi <= lo:
        hi = lo + 1
    left, right = PLOT_L * w, PLOT_R * w
    top, bottom = PLOT_T * h, PLOT_B * h
    pw, ph = right - left, bottom - top
    if scene.get("x_axis_type") == "date":
        # position by elapsed days like the native builder, not evenly
        try:
            import datetime as _dt
            ordinals = [_dt.date.fromisoformat(lab.strip()[:10]).toordinal()
                        for lab in labels]
            span = max(ordinals) - min(ordinals) or 1
            xs = np.array([left + (o - min(ordinals)) / span * pw
                           for o in ordinals])
        except (ValueError, TypeError):
            xs = np.linspace(left, right, len(values))
    else:
        xs = np.linspace(left, right, len(values))
    ys = np.clip(bottom - (np.array(values) - lo) / (hi - lo) * ph,
                 top, bottom)
    # grid + ticks
    tick_fs = FS_TICK
    for i in range(5):
        gy = bottom - ph * i / 4
        ax.plot([left, right], [gy, gy], color=pal["grid"],
                linewidth=max(1, w * .0018), zorder=1)
        tick = lo + (hi - lo) * i / 4
        ax.text(left - w * .015, gy, _fmt(tick), va="center", ha="right",
                fontsize=tick_fs, color=pal["muted"])
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
        for seg in range(n_pts - 1):
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
    ax.plot(xd, yd, color=pal["accent"], linewidth=max(2.0, w * .005),
            solid_capstyle="round", zorder=3)
    # dots at revealed points (scatter s is in pt^2: ~17px frame diameter)
    dot_s = (w * .017) ** 2
    for x, y in zip(xs[:n_pts], ys[:n_pts]):
        ax.scatter([x], [y], s=dot_s, color=pal["plot"],
                   edgecolors=pal["accent"], linewidths=max(1.2, w * .002),
                   zorder=4)
        ax.scatter([x], [y], s=dot_s * .32, color=pal["accent"], zorder=5)
    # latest value label counts up with the draw-on progress
    lv = values[-1] * min(1.0, p * 1.15)
    from matplotlib import patheffects as pe
    ax.text(right, min(ys[-1], bottom) - h * .03,
            _fmt(lv), va="bottom", ha="right",
            fontsize=FS_VALUE, color=pal["accent"], fontweight="bold",
            path_effects=[pe.withStroke(linewidth=3.5,
                                        foreground=pal["plot"])])
    xlab_budget = max(.03, (right - left) / len(labels) * .8 / w)
    for i, lab in enumerate(labels):
        ax.text(xs[i], bottom + h * XLABEL_DY,
                _clip(lab, FS_LABEL, xlab_budget, w),
                va="top", ha="center",
                fontsize=FS_LABEL, color=pal["muted"],
                rotation=0)
    # axis titles from the manifest (native builders render these too)
    x_title = str(scene.get("x_axis_label") or "")
    y_title = str(scene.get("y_axis_label") or "")
    if x_title:
        ax.text((left + right) / 2, bottom + h * (XLABEL_DY + .045),
                x_title.upper(), ha="center", va="top",
                fontsize=FS_MICRO, color=pal["muted"], fontweight="bold")
    if y_title:
        ax.text(w * .04, (top + bottom) / 2, y_title.upper(),
                ha="center", va="center", rotation=90,
                fontsize=FS_MICRO, color=pal["muted"], fontweight="bold")


def _draw_waterfall(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    steps = scene.get("steps") or []
    parsed = []
    running = 0.0
    for idx, st in enumerate(steps):
        kind = str(st.get("kind", "delta" if 0 < idx < len(steps) - 1 else "total"))
        val = _num(st.get("value", 0))
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
    left, right = w * .08, PLOT_R * w
    top, bottom = h * .10, PLOT_B * h
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
        # value label fades in as the bar lands
        va = min(1.0, max(0.0, (p - .45) / .4))
        sign = "+" if item["kind"] == "delta" and item["value"] > 0 else (
            "−" if item["kind"] == "delta" and item["value"] < 0 else "")
        ax.text(x + bar_w / 2, y_top - h * .015,
                f"{sign}{_fmt(abs(item['value']))}",
                ha="center", va="bottom", fontsize=FS_VALUE,
                color=pal["axis"], fontweight="bold", alpha=va)
        xlab_budget = max(.03, slot * .8 / w)
        ax.text(x + bar_w / 2, bottom + h * XLABEL_DY,
                _clip(item["label"], FS_LABEL, xlab_budget, w),
                ha="center", va="top", fontsize=FS_LABEL,
                color=pal["muted"], fontweight="bold")


def _draw_bullet(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    metrics = scene.get("metrics") or scene.get("items") or []
    items = [{"label": str(m.get("label", "")),
              "value": _num(m.get("value", 0)),
              "target": _num(m.get("target", 0)),
              "max": abs(_num(m.get("max"), 1.0)) or 1.0} for m in metrics]
    if not items:
        return
    label_x = w * .24
    left, right = w * .27, PLOT_R * w
    top, bottom = h * .12, h * .90
    row_h = (bottom - top) / len(items)
    prog = _stagger(t / dur, len(items), start=.10, step=.09)
    for i, item in enumerate(items):
        p = prog[i]
        y = top + i * row_h
        track_h = min(h * .10, row_h * .55)
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
            from matplotlib import patheffects as pe
            ax.text(right, ty + track_h / 2,
                    _fmt(item["value"] * min(1.0, p)),
                    va="center", ha="right", fontsize=FS_VALUE,
                    color=pal["accent"], fontweight="bold",
                    path_effects=[pe.withStroke(linewidth=3.5,
                                                foreground=pal["plot"])])
        ax.text(label_x, ty + track_h / 2,
                _clip(item["label"], FS_LABEL, label_x - w * .04, w),
                va="center", ha="right", fontsize=FS_LABEL,
                color=pal["axis"], fontweight="bold")


def _draw_heatmap(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    rows = scene.get("row_labels") or []
    cols = scene.get("col_labels") or []
    matrix = scene.get("values") or []
    if not rows or not cols or not matrix:
        return
    flat = [_num(v) for row in matrix for v in row]
    lo, hi = min(flat), max(flat)
    span = max(1e-6, hi - lo)
    left, right = w * .22, PLOT_R * w
    top, bottom = h * .13, h * .93
    cw = (right - left) / len(cols)
    ch = (bottom - top) / len(rows)
    prog = _stagger(t / dur, len(rows) * len(cols), start=.08, step=.012)
    idx = 0
    for r_i, row in enumerate(matrix):
        for c_i, raw in enumerate(row[:len(cols)]):
            val = _num(raw)
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
            cw_px = max(2.0, cw - w * .012)
            ch_px = max(2.0, ch - h * .012)
            from matplotlib.patches import FancyBboxPatch
            alpha = p
            # grow from cell center, not left edge
            gx = cx + cw_px * (1 - p) / 2
            ax.add_patch(FancyBboxPatch(
                (gx, cy), cw_px * p, ch_px,
                boxstyle="round,pad=0,rounding_size=6",
                facecolor=color, edgecolor="none", alpha=alpha, zorder=2))
            if p > .8:
                lum = sum(mixc) / 3
                tx_col = "#ffffff" if lum < 140 else "#111111"
                txt = _fmt(val)
                fs = _fit_fs(txt, FS_VALUE, cw_px * .92, ch_px * .9)
                ax.text(cx + cw_px / 2, cy + ch_px / 2, txt,
                        ha="center", va="center", fontsize=fs,
                        color=tx_col, fontweight="bold")
    # headers
    col_budget = max(.03, cw * .8 / w)
    for c_i, lab in enumerate(cols):
        ax.text(left + c_i * cw + cw / 2, top - h * .015,
                _clip(lab, FS_TICK, col_budget, w),
                ha="center", va="bottom", fontsize=FS_TICK,
                color=pal["muted"], fontweight="bold")
    for r_i, lab in enumerate(rows):
        ax.text(left - w * .015, top + r_i * ch + ch / 2,
                _clip(lab, FS_TICK, left - w * .05, w),
                ha="right", va="center", fontsize=FS_TICK,
                color=pal["muted"], fontweight="bold")


def _draw_funnel(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    stages = scene.get("stages") or []
    items = [{"label": str(s.get("label", "")),
              "value": _num(s.get("value", 0))} for s in stages]
    if len(items) < 2:
        return
    top_val = items[0]["value"] or 1
    left, right = w * .08, w * .92
    top, bottom = h * .10, h * .92
    row_h = (bottom - top) / len(items)
    prog = _stagger(t / dur, len(items), start=.08, step=.10)
    for i, item in enumerate(items):
        p = prog[i]
        share = item["value"] / top_val
        label_txt = f"{item['label']}  ·  {round(share * 100)}%"
        # keep the bar wide enough for its centered label, capped at the frame
        fs_lbl = _fit_fs(label_txt, FS_VALUE, (right - left) * .8,
                         row_h * .6)
        min_w = max(_text_frac(label_txt, fs_lbl, w) * 1.12,
                    (right - left) * .20)
        bar_w = min(right - left,
                    max(min_w, (right - left) * share)) * p
        x = (left + right) / 2 - bar_w / 2
        y = top + i * row_h + row_h * .10
        bh = row_h * .72
        from matplotlib.patches import FancyBboxPatch
        # color fades toward surface for later stages
        ax.add_patch(FancyBboxPatch(
            (x, y), bar_w, bh,
            boxstyle=f"round,pad=0,rounding_size={min(bh * .3, w * .02)}",
            facecolor=pal["accent"], edgecolor="none",
            alpha=max(.15, .95 - i * .12), zorder=2))
        if p > .7:
            ax.text((left + right) / 2, y + bh / 2, label_txt,
                    ha="center", va="center", fontsize=fs_lbl,
                    color="#ffffff", fontweight="bold")
        if i + 1 < len(items) and p > .9:
            sep_y = top + (i + 1) * row_h
            ax.plot([x + bar_w / 2 - bar_w * .3, x + bar_w / 2 + bar_w * .3],
                    [sep_y, sep_y], color=pal["hairline"],
                    linewidth=max(1, w * .0015), zorder=1)


def _draw_diverging(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    baseline = _num(scene.get("baseline", 0))
    raw = scene.get("items") or scene.get("bars") or []
    items = [{"label": str(i.get("label", "")),
              "delta": _num(i.get("value", 0)) - baseline}
             for i in raw]
    if not items:
        return
    max_abs = max(abs(i["delta"]) for i in items) or 1
    label_x = w * .22
    left, right = w * .25, PLOT_R * w
    top, bottom = h * .12, h * .90
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
        cy = y + row_h / 2
        if bar_w > w * .02:
            if item["delta"] >= 0:
                ax.text(x0 + bar_w + w * .008, cy,
                        f"+{_fmt(item['delta'])}", va="center", ha="left",
                        fontsize=FS_VALUE, color=pal["axis"],
                        fontweight="bold")
            else:
                ax.text(x0 - w * .008, cy, f"−{_fmt(abs(item['delta']))}",
                        va="center", ha="right", fontsize=FS_VALUE,
                        color=pal["axis"], fontweight="bold")
        ax.text(label_x, cy,
                _clip(item["label"], FS_LABEL, label_x - w * .04, w),
                va="center", ha="right", fontsize=FS_LABEL,
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
    if x1 == x0:
        x1 = x0 + 1
    if y1 == y0:
        y1 = y0 + 1
    left, right = PLOT_L * w, PLOT_R * w
    top, bottom = PLOT_T * h, PLOT_B * h
    pw, ph = right - left, bottom - top
    for i in range(5):
        gy = bottom - ph * i / 4
        gx = left + pw * i / 4
        ax.plot([left, right], [gy, gy], color=pal["grid"],
                linewidth=max(1, w * .0015), zorder=1)
        ax.plot([gx, gx], [top, bottom], color=pal["grid"],
                linewidth=max(1, w * .0015), zorder=1)
        ax.text(left - w * .015, gy, _fmt(y0 + (y1 - y0) * i / 4),
                va="center", ha="right", fontsize=FS_TICK,
                color=pal["muted"])
        ax.text(gx, bottom + h * XLABEL_DY, _fmt(x0 + (x1 - x0) * i / 4),
                va="top", ha="center", fontsize=FS_TICK,
                color=pal["muted"])
    prog = _stagger(t / dur, len(pts), start=.10, step=.05)
    dot_s = (w * .017) ** 2
    for i, pt in enumerate(pts):
        xv, yv = _num(pt.get("x", 0)), _num(pt.get("y", 0))
        px = min(right, max(left, left + (xv - x0) / (x1 - x0) * pw))
        py = min(bottom, max(top, bottom - (yv - y0) / (y1 - y0) * ph))
        p = prog[i]
        if p <= 0:
            continue
        ax.scatter([px], [py], s=dot_s * p, color=pal["accent"],
                   edgecolors=pal["plot"], linewidths=max(1.2, w * .002),
                   zorder=3)


def _draw_donut(ax, scene, w, h, t, dur, pal, plt):
    from matplotlib import patches as mpatches
    cx, cy = w / 2, h * .44
    radius = min(w, h) * .33
    width_pt = radius * .26
    segments = scene.get("segments")
    track = mpatches.Circle((cx, cy), radius, fill=False,
                       edgecolor=pal["hairline"], linewidth=width_pt,
                       zorder=1)
    ax.add_patch(track)
    if isinstance(segments, list) and len(segments) >= 2:
        vals = [max(0.0, _num(s.get("value", 0))) for s in segments]
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
        # legend fades in once the last segment has landed
        n = len(segments)
        lw = w * .88 / n
        label_budget = max(.04, lw / w - .055)
        la = min(1.0, max(0.0, (prog[-1] - .55) / .35)) if prog else 1.0
        for i, seg in enumerate(segments):
            lx = w * .06 + i * lw
            from matplotlib.patches import FancyBboxPatch
            ax.add_patch(FancyBboxPatch(
                (lx, h * .855), w * .02, h * .030,
                boxstyle="round,pad=0,rounding_size=4",
                facecolor=pal["series"][i % len(pal["series"])],
                edgecolor="none", alpha=la, zorder=2))
            ax.text(lx + w * .028, h * .87, _clip(seg.get("label", ""),
                    FS_LABEL, label_budget, w),
                    va="center", ha="left", fontsize=FS_LABEL,
                    color=pal["muted"], alpha=la)
    else:
        pct = min(100.0, max(0.0,
                   _num(scene.get("value", scene.get("percent", 0)))))
        p = _ease_out(min(1.0, max(0.0, (t / dur - .10) / .6)))
        sweep = 360 * (pct / 100.0) * p
        if sweep > .5:
            wedge = mpatches.Wedge(
                (cx, cy), radius, 90 - sweep, 90, width=width_pt,
                facecolor=pal["accent"], edgecolor="none", zorder=2)
            ax.add_patch(wedge)
        # center number counts up
    count_p = _ease_out(min(1.0, max(0.0, (t / dur - .15) / .7)))
    if isinstance(segments, list) and len(segments) >= 2:
        shown = sum(max(0.0, _num(s.get("value", 0)))
                    for s in segments)
        center_fmt = _fmt(shown * count_p)
    else:
        shown = min(100.0, max(0.0,
                   _num(scene.get("value", scene.get("percent", 0)))))
        center_fmt = f"{shown * count_p:,.0f}%"
    ax.text(cx, cy, center_fmt, ha="center", va="center",
            fontsize=h * .075, color=pal["axis"], fontweight="bold",
            zorder=3)
    label = str(scene.get("label", ""))
    if label:
        ax.text(cx, cy - radius * .34, _clip(label.upper(), FS_LABEL,
                .5, w), ha="center",
                va="center", fontsize=FS_LABEL, color=pal["muted"],
                fontweight="bold")


def _draw_stacked(ax, scene, w, h, t, dur, pal, plt):
    """100% normalized horizontal stacked bars with a percent axis."""
    from matplotlib import patches as mpatches
    categories = scene.get("categories") or []
    parsed = []
    for cat in categories:
        raw = [{"label": str(s.get("label", "")),
                "share": s.get("share"),
                "value": _num(s.get("value", 0))}
               for s in (cat.get("segments") or [])]
        total = sum(s["value"] for s in raw)
        segs = []
        for s in raw:
            share = s["share"]
            share = (float(share) if share is not None
                     else (s["value"] / total if total > 0 else 0.0))
            segs.append({"label": s["label"], "share": share})
        if segs:
            parsed.append({"label": str(cat.get("label", "")),
                           "segments": segs})
    if not parsed:
        return
    n = len(parsed)
    label_x = w * .22
    left, right = w * .25, PLOT_R * w
    top, bottom = h * .13, h * .78   # legend zone reserved below
    row_h = (bottom - top) / n
    bar_h = min(h * .11, row_h * .55)
    # percent grid + ticks
    for i in range(5):
        gx = left + (right - left) * i / 4
        ax.plot([gx, gx], [top, bottom], color=pal["grid"],
                linewidth=max(1, w * .0015), zorder=1)
        ax.text(gx, bottom + h * .015, f"{i * 25}%", va="top", ha="center",
                fontsize=FS_TICK, color=pal["muted"])
    prog = _stagger(t / dur, n, start=.10, step=.12)
    n_seg = max(len(c["segments"]) for c in parsed)
    for r_i, cat in enumerate(parsed):
        p = prog[r_i]
        y = top + r_i * row_h + (row_h - bar_h) / 2
        ax.text(label_x, y + bar_h / 2,
                _clip(cat["label"], FS_LABEL, label_x - w * .04, w),
                va="center", ha="right", fontsize=FS_LABEL,
                color=pal["axis"], fontweight="bold")
        x = left
        seg_w_total = right - left
        for s_i, seg in enumerate(cat["segments"]):
            share = min(1.0, max(0.0, seg["share"]))
            sw = seg_w_total * share * p
            if sw <= 1:
                x += seg_w_total * share
                continue
            color = pal["series"][s_i % len(pal["series"])]
            ax.add_patch(mpatches.Rectangle(
                (x, y), sw, bar_h, facecolor=color, edgecolor="none",
                zorder=2))
            x += seg_w_total * share
        if p > .85:
            ax.text(right + w * .008, y + bar_h / 2,
                    f"{round(sum(min(1.0, max(0.0, s['share'])) for s in cat['segments']) * 100)}%",
                    va="center", ha="left", fontsize=FS_VALUE,
                    color=pal["axis"], fontweight="bold")
    # legend — segment labels are consistent across categories per the
    # builder contract, so dedupe preserving first-seen order
    seen = []
    for cat in parsed:
        for s in cat["segments"]:
            if s["label"] not in seen:
                seen.append(s["label"])
    lw = w * .86 / max(1, len(seen))
    la = min(1.0, max(0.0, (prog[-1] - .5) / .4)) if prog else 1.0
    for i, lab in enumerate(seen):
        lx = w * .07 + i * lw
        ax.add_patch(mpatches.FancyBboxPatch(
            (lx, h * .87), w * .018, h * .026,
            boxstyle="round,pad=0,rounding_size=4",
            facecolor=pal["series"][i % len(pal["series"])],
            edgecolor="none", alpha=la, zorder=2))
        ax.text(lx + w * .026, h * .883,
                _clip(lab, FS_LABEL, max(.04, lw / w - .05), w),
                va="center", ha="left", fontsize=FS_LABEL,
                color=pal["muted"], alpha=la)


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
    "stacked_bars_100": _draw_stacked,
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
