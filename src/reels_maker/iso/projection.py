"""Isometric projection, drawing canvas, fonts and atmosphere layers."""
from __future__ import annotations

import functools
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

C = math.sqrt(3) / 2
W, H = 1080, 1920
FPS = 30

# ASTA brand-anchored palette (deep greenhouse green, warm light accents).
DEFAULT_PALETTE = {
    "bg": (23, 61, 36),
    "white": (248, 249, 240),
    "mint": (105, 200, 120),
    "muted": (177, 205, 172),
    "gold": (255, 216, 145),
    "cool": (175, 215, 235),
    "ice": (228, 242, 251),
    "amber": (255, 176, 92),
    "dark": (18, 42, 28),
}


def E(x):
    """Smootherstep easing clamped to [0, 1]."""
    x = float(np.clip(x, 0, 1))
    return x * x * x * (x * (x * 6 - 15) + 10)


def mix(a, b, p):
    return tuple(a[i] + (b[i] - a[i]) * p for i in range(len(a)))


def iso(p):
    return C * (p[0] - p[1]), (p[0] + p[1]) * 0.5 - p[2]


def hold(u, a, b):
    return E((u - a) / (b - a))


@functools.lru_cache(maxsize=1)
def resolve_font() -> str:
    """Brand font with safe fallbacks; never raises, never hard-codes one path."""
    candidates = []
    env = os.environ.get("ASTA_FONT") or os.environ.get("REELS_FONT")
    if env:
        candidates.append(Path(env))
    candidates.append(Path.home() / "Library" / "Fonts" / "OpenSans-Regular.ttf")
    candidates.append(Path("/usr/share/fonts/opentype/open-sans/OpenSans-Regular.ttf"))
    try:
        import matplotlib

        candidates.append(
            Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf")
    except Exception:
        pass
    for path in candidates:
        try:
            if path.is_file():
                ImageFont.truetype(str(path), 20)
                return str(path)
        except Exception:
            continue
    return ""


class Canvas:
    """Isometric drawing surface in world units."""

    def __init__(self, bg, k=88, origin=(555, 1390), spin=0.0):
        self.k = k
        self.origin = origin
        # View spin (radians about world +Z): 0 shows the default +X/+Y
        # faces; pi/2, pi, -pi/2 show the other three sides. Zero is the
        # byte-identical legacy path.
        self.spin = float(spin)
        self.dim = 0.0
        self.bg = tuple(bg[:3])
        # Allocated lazily: anchor-only canvases (leader-line projection)
        # never pay for the 1840x1500 raster.
        self._im = None
        self._d = None
        self._stack: list = []

    @property
    def im(self):
        if self._im is None:
            self._im = Image.new("RGB", (1840, 1500), self.bg)
        return self._im

    @property
    def d(self):
        if self._d is None:
            self._d = ImageDraw.Draw(self.im, "RGBA")
        return self._d

    def _raw(self, p):
        u, v = iso(p)
        if self.spin:
            c, s = math.cos(self.spin), math.sin(self.spin)
            u, v = u * c - v * s, u * s + v * c
        return (self.origin[0] + u * self.k - 80) * 2, (self.origin[1] + v * self.k - 790) * 2

    def P(self, p):
        x, y = self._raw(p)
        for px, py, s in self._stack:
            x = px + (x - px) * s
            y = py + (y - py) * s
        return x, y

    def push(self, pivot, s):
        """Scale subsequent drawing around a world pivot (e.g. shrink a unit)."""
        px, py = self._raw(pivot)
        for qx, qy, qs in self._stack:
            px = qx + (px - qx) * qs
            py = qy + (py - qy) * qs
        self._stack.append((px, py, float(s)))

    def pop(self):
        self._stack.pop()

    def _c(self, c):
        rgb = mix(c[:3], self.bg, self.dim) if self.dim else c[:3]
        return tuple(int(round(v)) for v in rgb) + tuple(int(round(v)) for v in c[3:])

    def poly(self, ps, c):
        self.d.polygon([self.P(p) for p in ps], fill=self._c(c))

    def line(self, ps, c, w=1):
        self.d.line([self.P(p) for p in ps], fill=self._c(c),
                    width=max(1, int(round(w * 2))), joint="curve")

    def dot(self, p, r, c):
        x, y = self.P(p)
        self.d.ellipse((x - r * 2, y - r * 2, x + r * 2, y + r * 2), fill=self._c(c))

    def box(self, a, b, front=(239, 244, 232), side=(171, 193, 164), top=(250, 252, 241)):
        x, y, z = a
        X, Y, Z = b
        self.poly([(X, y, z), (X, Y, z), (X, Y, Z), (X, y, Z)], side)
        self.poly([(x, Y, z), (X, Y, z), (X, Y, Z), (x, Y, Z)], front)
        self.poly([(x, y, Z), (X, y, Z), (X, Y, Z), (x, Y, Z)], top)

    @staticmethod
    def _mul(c, f):
        return tuple(max(0, min(255, int(round(v * f))))
                     for v in c[:3])

    def grad_poly(self, ps, c_top, c_bot):
        """Vertical gradient polygon: top color flows into bottom color."""
        pts = [self.P(p) for p in ps]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, x1 = int(min(xs)), int(max(xs))
        y0, y1 = int(min(ys)), int(max(ys))
        if x1 <= x0 or y1 <= y0:
            return
        mask = Image.new("L", (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(mask).polygon([(x - x0, y - y0) for x, y in pts],
                                    fill=255)
        t = np.linspace(0.0, 1.0, y1 - y0, dtype=float)[:, None, None]
        ct = np.array(self._c(c_top)[:3], dtype=float)
        cb = np.array(self._c(c_bot)[:3], dtype=float)
        grad = np.broadcast_to(ct[None, None, :] * (1.0 - t)
                               + cb[None, None, :] * t,
                               (y1 - y0, x1 - x0, 3)).astype(np.uint8)
        self.im.paste(Image.fromarray(grad, "RGB"), (x0, y0), mask)

    def boxg(self, a, b, c=(200, 205, 195), *rest, dl=0.14):
        """Gradient box (house look M1+M2): faces shade vertically from
        a lightened top to a darkened bottom; top edges get a hairline
        highlight instead of dark outlines. The base color drives every
        face; legacy per-face tints passed after it are superseded by
        the gradient system."""
        x, y, z = a
        X, Y, Z = b
        side = self._mul(c, 0.88)
        self.grad_poly([(X, y, z), (X, Y, z), (X, Y, Z), (X, y, Z)],
                       self._mul(side, 1.0 + dl),
                       self._mul(side, 1.0 - dl))
        self.grad_poly([(x, Y, z), (X, Y, z), (X, Y, Z), (x, Y, Z)],
                       self._mul(c, 1.0 + dl), self._mul(c, 1.0 - dl))
        self.poly([(x, y, Z), (X, y, Z), (X, Y, Z), (x, Y, Z)],
                  self._mul(c, 1.0 + dl * 0.5))
        hi = self._mul(c, 1.0 + dl * 1.6) + (255,)
        self.line([(x, y, Z), (X, y, Z)], hi, 1)
        self.line([(X, y, Z), (X, Y, Z)], hi, 1)
        self.line([(X, Y, Z), (x, Y, Z)], hi, 1)
        self.line([(x, Y, Z), (x, y, Z)], hi, 1)

    def ao(self, cx, cy, r, strength=0.18, z=0.0, squash=0.5):
        """Soft grounding shadow (house look M3): radial falloff, never
        a hard-edged ellipse. Alpha is capped at 0.25 by design."""
        if not 0.0 < strength <= 0.25:
            raise ValueError(f"ao strength must be within (0, 0.25], "
                             f"got {strength!r}")
        pts = [(cx + r * math.cos(i * math.tau / 24),
                cy + r * squash * math.sin(i * math.tau / 24), z)
               for i in range(24)]
        xy = [self.P(p) for p in pts]
        xs = [p[0] for p in xy]
        ys = [p[1] for p in xy]
        x0, x1 = int(min(xs)), int(max(xs))
        y0, y1 = int(min(ys)), int(max(ys))
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[0:(y1 - y0), 0:(x1 - x0)]
        nx = (xx - (x1 - x0) / 2) / ((x1 - x0) / 2)
        ny = (yy - (y1 - y0) / 2) / ((y1 - y0) / 2)
        d = np.clip(np.sqrt(nx * nx + ny * ny), 0.0, 1.0)
        fall = (1.0 - d * d) ** 2 * strength
        region = np.asarray(self.im.crop((x0, y0, x1, y1)),
                            dtype=float) / 255.0
        region = region * (1.0 - fall[..., None])
        dark = Image.fromarray((region * 255).astype(np.uint8), "RGB")
        full = self.im.copy()
        full.paste(dark, (x0, y0))
        self._im = full
        # The draw handle targets the old raster: drop it so the next
        # poly/line/dot rebinds lazily to the darkened image.
        self._d = None

    def fp(self, x, X, y, z, Z, c):
        self.poly([(x, y, z), (X, y, z), (X, y, Z), (x, y, Z)], c)

    def disc_x(self, x, cy, cz, r, c, n=36):
        self.poly([(x, cy + r * math.cos(i * math.tau / n),
                    cz + r * math.sin(i * math.tau / n)) for i in range(n)], c)

    def disc_y(self, cx, y, cz, r, c, n=36):
        self.poly([(cx + r * math.cos(i * math.tau / n), y,
                    cz + r * math.sin(i * math.tau / n)) for i in range(n)], c)

    def ground_ellipse(self, cx, cy, rx, ry, c, z=-0.125, n=40):
        self.poly([(cx + rx * math.cos(i * math.tau / n),
                    cy + ry * math.sin(i * math.tau / n), z) for i in range(n)], c)

    def tube(self, cx, cy, z0, z1, r):
        """Marker only: declares a vertical tube body for tooling
        (the audit reads it via Rec). Draws nothing."""
        return None


def shade_face(q, corners, top, bottom, steps=8):
    """Vertical light falloff over a world quad (material depth, no blur)."""
    (ax, ay, az), (bx, by, bz), (cx, cy, cz), (dx, dy, dz) = corners
    for i in range(steps):
        f0, f1 = i / steps, (i + 1) / steps

        def lerp(P, Q, f):
            return (P[0] + (Q[0] - P[0]) * f, P[1] + (Q[1] - P[1]) * f, P[2] + (Q[2] - P[2]) * f)

        quad = [lerp((ax, ay, az), (dx, dy, dz), f0), lerp((bx, by, bz), (cx, cy, cz), f0),
                lerp((bx, by, bz), (cx, cy, cz), f1), lerp((ax, ay, az), (dx, dy, dz), f1)]
        col = mix(top, bottom, (f0 + f1) / 2)
        q.poly(quad, col)


def contact_shadow(q, cx, cy, rx, ry, alpha=110):
    """Soft grounding blob from layered ellipses (no per-frame blur)."""
    for grow, part in ((1.18, 0.35), (1.0, 0.4), (0.82, 0.5)):
        q.ground_ellipse(cx, cy, rx * grow, ry * grow,
                         (10, 26, 18, int(alpha * part)), z=-0.11, n=36)


def sheen(q, corners, alpha=70):
    """Diagonal glass gloss over a world quad."""
    (ax, ay, az), (bx, by, bz), (cx, cy, cz), (dx, dy, dz) = corners

    def lerp(P, Q, f):
        return (P[0] + (Q[0] - P[0]) * f, P[1] + (Q[1] - P[1]) * f, P[2] + (Q[2] - P[2]) * f)

    band = [lerp((ax, ay, az), (bx, by, bz), 0.12), lerp((ax, ay, az), (bx, by, bz), 0.38),
            lerp((dx, dy, dz), (cx, cy, cz), 0.30), lerp((dx, dy, dz), (cx, cy, cz), 0.04)]
    q.poly(band, (255, 255, 255, alpha))


@functools.lru_cache(maxsize=512)
def _glyph(s, n, col, font_path):
    if font_path:
        f = ImageFont.truetype(font_path, n)
    else:
        f = ImageFont.load_default()
    z = Image.new("RGBA", (math.ceil(f.getlength(s)) + 32, n * 3))
    d = ImageDraw.Draw(z)
    d.text((16, n * 2), s, font=f, fill=col, anchor="ls")
    return z.crop(z.getbbox())


@functools.lru_cache(maxsize=1)
def resolve_font_bold() -> str:
    """Bold companion of resolve_font(); falls back to regular."""
    from PIL import ImageFont as _F
    reg = resolve_font()
    cands = [reg.replace("Regular", "Bold"), reg.replace("regular", "bold"),
             reg.replace("Sans.ttf", "Sans-Bold.ttf")]
    for c in dict.fromkeys(cands):
        try:
            if c != reg and Path(c).is_file():
                _F.truetype(c, 20)
                return c
        except Exception:
            continue
    return reg


def glyph(s, n, col, font_path):
    return _glyph(s, n, tuple(col), font_path or "")


def decal(q, s, O, U, V, u, v, height, col, font_path, maxw=2.6):
    """Project typeset text onto a world-space quad (ground labels)."""
    z = glyph(s, 96, tuple(col), font_path)
    ww = min(maxw, height * z.width / z.height)
    hh = ww * z.height / z.width

    def pt(a, b):
        return np.array(q.P(tuple(O[i] + U[i] * a + V[i] * b for i in range(3))))

    p0 = pt(u, v)
    p1 = pt(u + ww, v)
    p2 = pt(u, v + hh)
    p3 = p1 + p2 - p0
    lo = np.maximum(np.floor(np.minimum.reduce([p0, p1, p2, p3])).astype(int), 0)
    hi = np.minimum(np.ceil(np.maximum.reduce([p0, p1, p2, p3])).astype(int) + 1, q.im.size)
    if np.any(hi <= lo):
        return
    mat = np.column_stack([(p1 - p0) / z.width, (p2 - p0) / z.height])
    if abs(np.linalg.det(mat)) < 1e-10:
        return
    inv = np.linalg.inv(mat)
    b = inv @ (lo - p0)
    zz = z.transform(tuple(hi - lo), Image.Transform.AFFINE,
                     (inv[0, 0], inv[0, 1], b[0], inv[1, 0], inv[1, 1], b[1]),
                     Image.Resampling.BICUBIC)
    q.im.paste(zz, tuple(lo), zz)


@functools.lru_cache(maxsize=1)
def vignette():
    yy, xx = np.mgrid[0:750, 0:920]
    r = np.sqrt(((xx - 460) / 520) ** 2 + ((yy - 375) / 430) ** 2)
    a = np.clip((r - 0.72) / 0.6, 0, 1) * 70
    lay = Image.new("RGBA", (920, 750), (12, 34, 22, 0))
    lay.putalpha(Image.fromarray(a.astype("uint8")))
    return lay


@functools.lru_cache(maxsize=1)
def flake_table():
    rng = np.random.default_rng(3)
    return rng.random((110, 6))


@functools.lru_cache(maxsize=1024)
def _flake_sprite(index: int, alpha: int):
    """One pre-blurred snow flake.

    Flake size and base alpha are fixed per flake (only the position moves
    with time), so the GaussianBlur(0.6) is paid once per flake instead of
    once per frame. Pasted at integer positions: sub-pixel placement and
    flake-overlap blending can differ by a few levels from a full-layer
    blur, which is invisible on sparse snowfall but runs ~8x faster.
    """
    a, _b, _c, _dd, e, f = tuple(flake_table()[index])
    big = index < 14
    r = (1 + 2.2 * e) if not big else (6 + 5 * e)
    pad = 4
    half = int(math.ceil(r + pad))
    size = half * 2 + 1
    dot = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(dot).ellipse(
        (half - r, half - r, half + r, half + r),
        fill=(250, 253, 255, alpha))
    return dot.filter(ImageFilter.GaussianBlur(0.6)), half


def snow_layer(u, strength=1.0, parallax=1.0):
    """Two-depth snowfall; parallax scales drift speed for a 2.5D feel."""
    lay = Image.new("RGBA", (920, 750), (0, 0, 0, 0))
    T = flake_table()
    for i, (a, b, c, dd, _e, f) in enumerate(T):
        big = i < 14
        vy = (22 + 60 * c) * (1.0 if not big else 1.5) * parallax
        x = (a * 920 + u * (8 + 14 * dd) * parallax + math.sin(u * 0.8 + i) * 14) % 920
        y = (b * 750 + u * vy) % 750
        al = int((95 + 130 * f) * strength) if not big else int(40 * strength)
        if al <= 0:
            continue
        sprite, half = _flake_sprite(i, al)
        lay.alpha_composite(sprite, (int(round(x)) - half,
                                     int(round(y)) - half))
    return lay
