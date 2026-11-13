"""Interior props batch: softener, filters, cabinet, thermo-head, phone.

Builders take ``(q, cx, cy, P)`` with all coordinates relative to the
placement center, mid-tone palette (nothing below RGB 60 except tiny
dots), overlapped joints, NO contact shadows, no text decals.
"""
from __future__ import annotations

import math

from .world import _cylinder


def softener(q, cx, cy, P):
    """Water softener: tall slim resin tank (hero) plus brine tank."""
    rx, bx = cx - 0.17, cx + 0.24
    # Solid base discs FIRST (call-order painter): tanks sink their feet
    # into them; the visible annulus reads as the flange top face.
    # (Tube rings here read as hollow outlines / stray discs.)
    _cylinder(q, rx, cy, 0.0, 0.06, 0.26,
              (70, 86, 74), (54, 68, 58), (70, 86, 74), n=32)
    _cylinder(q, bx, cy - 0.02, 0.0, 0.05, 0.185,
              (70, 86, 74), (54, 68, 58), (70, 86, 74), n=24)
    # Resin tank: tall slim hero + lid rim + valve head straddling the top.
    _cylinder(q, rx, cy, 0.02, 1.42, 0.24,
              (228, 234, 226), (158, 180, 160), (232, 238, 230), n=40)
    q.ground_ellipse(rx, cy, 0.245, 0.245, (206, 220, 208), z=0.70)
    q.ground_ellipse(rx, cy, 0.245, 0.245, (206, 220, 208), z=1.05)
    for i in range(10):
        a = i * math.tau / 10
        q.dot((rx + 0.247 * math.cos(a), cy + 0.247 * math.sin(a), 1.475),
              0.9, (120, 142, 126, 255))
    # Valve head: collar sunk into the lid, body + cap above.
    _cylinder(q, rx, cy, 1.40, 1.52, 0.10,
              (96, 112, 100), (70, 86, 74), (120, 136, 124), n=16)
    q.box((rx - 0.09, cy - 0.07, 1.50), (rx + 0.09, cy + 0.07, 1.60),
          (70, 86, 74), (54, 68, 58), (94, 110, 96))
    q.box((rx - 0.10, cy - 0.08, 1.585), (rx + 0.10, cy + 0.08, 1.62),
          (94, 110, 96), (70, 86, 74), (116, 132, 118))
    # Brine tank: shorter squat companion with overlapping lid.
    _cylinder(q, bx, cy - 0.02, 0.02, 0.60, 0.17,
              (214, 208, 190), (150, 146, 128), (222, 216, 198), n=32)
    _cylinder(q, bx, cy - 0.02, 0.585, 0.66, 0.176,
              (150, 146, 128), (120, 116, 102), (170, 166, 148), n=32)
    q.dot((bx, cy - 0.02, 0.665), 1.2, (120, 116, 102, 255))
    # Short bridge hose between the tanks, low and dark.
    q.box((rx + 0.10, cy - 0.035, 0.42), (bx - 0.10, cy + 0.035, 0.50),
          (70, 86, 74), (54, 68, 58), (94, 110, 96))
    # (Base discs painted first, above.)


def filters(q, cx, cy, P):
    """Filter station: two blue housings on a bracket with valves."""
    # Bracket bar on two end legs; legs sink into the plinth.
    q.box((cx - 0.52, cy - 0.06, 0.78), (cx + 0.52, cy + 0.06, 0.88),
          (150, 164, 154), (118, 134, 122), (172, 186, 174))
    for sx in (cx - 0.46, cx + 0.46):
        q.box((sx - 0.05, cy - 0.05, 0.0), (sx + 0.05, cy + 0.05, 0.80),
              (118, 134, 122), (96, 112, 100), (140, 154, 142))
        q.box((sx - 0.08, cy - 0.08, 0.0), (sx + 0.08, cy + 0.08, 0.05),
              (96, 112, 100), (78, 94, 84), (118, 134, 122))
    # Two housings: cap sunk under the bar, blue sump below, drain nub.
    for hx in (cx - 0.22, cx + 0.22):
        _cylinder(q, hx, cy, 0.30, 0.72, 0.105,
                  (96, 150, 198), (70, 118, 162), (120, 170, 210), n=24)
        _cylinder(q, hx, cy, 0.70, 0.80, 0.115,
                  (118, 134, 122), (92, 108, 96), (140, 154, 142), n=20)
        _cylinder(q, hx, cy, 0.24, 0.32, 0.06,
                  (92, 108, 96), (70, 86, 74), (110, 126, 114), n=12)
        q.ground_ellipse(hx, cy, 0.06, 0.06, (70, 86, 74), z=0.24)
        # Gloss band strictly on the sump flank.
        q.poly([(hx - 0.055, cy + 0.088, 0.40), (hx - 0.015, cy + 0.103, 0.40),
                (hx - 0.015, cy + 0.103, 0.62), (hx - 0.055, cy + 0.088, 0.62)],
               (255, 255, 255, 60))
        # Valve handle above the bar on a short stem.
        _cylinder(q, hx, cy, 0.875, 0.97, 0.028,
                  (150, 150, 140), (118, 118, 108), (165, 165, 155), n=10)
        q.box((hx - 0.075, cy - 0.025, 0.955), (hx + 0.075, cy + 0.025, 0.995),
              (198, 110, 80), (160, 84, 60), (214, 134, 100))


def cabinet(q, cx, cy, P):
    """Open manifold cabinet: shell open to +Y, brass manifold inside."""
    x0, x1, yb, d, z0, z1 = cx - 0.45, cx + 0.45, cy - 0.14, 0.28, 0.06, 1.06
    yf = yb + d
    # Shell: back panel, sides, top, bottom — open toward +Y.
    q.box((x0, yb, z0), (x1, yb + 0.04, z1),
          (226, 231, 220), (200, 209, 194), (236, 240, 231))
    q.box((x0, yb, z0), (x0 + 0.05, yf, z1),
          (214, 222, 210), (226, 231, 220), (232, 238, 226))
    q.box((x1 - 0.05, yb, z0), (x1, yf, z1),
          (214, 222, 210), (226, 231, 220), (232, 238, 226))
    q.box((x0, yb, z1 - 0.05), (x1, yb + 0.14, z1 + 0.02),
          (214, 222, 210), (200, 209, 194), (232, 238, 226))
    q.box((x0, yb, z0 - 0.02), (x1, yf, z0 + 0.06),
          (200, 209, 194), (188, 197, 182), (220, 227, 214))
    # Recessed-interior shading on the back panel front face, painted
    # before the manifold so the cavity reads as open, not solid.
    q.fp(x0 + 0.055, x1 - 0.055, yb + 0.042, z0 + 0.06, z1 - 0.05,
         (196, 204, 190))
    # Feet under the shell, sunk into the plinth.
    for fx in (x0 + 0.10, x1 - 0.10):
        q.box((fx - 0.05, yb + 0.02, 0.0), (fx + 0.05, yf - 0.02, z0 + 0.02),
              (96, 112, 100), (78, 94, 84), (118, 134, 122))
    # Brass manifold bar across the back panel + end valves.
    my = yb + 0.13
    q.box((x0 + 0.10, my - 0.035, 0.30), (x1 - 0.10, my + 0.035, 0.38),
          (196, 150, 92), (150, 110, 64), (214, 172, 112))
    for ex in (x0 + 0.10, x1 - 0.10):
        q.box((ex - 0.045, my - 0.05, 0.285), (ex + 0.045, my + 0.05, 0.395),
              (150, 110, 64), (120, 88, 50), (172, 132, 80))
    # Four loops: short down stubs with collars and red/blue tops.
    for i in range(4):
        lx = x0 + 0.20 + (x1 - x0 - 0.40) * i / 3
        q.box((lx - 0.022, my - 0.022, 0.10), (lx + 0.022, my + 0.022, 0.305),
              (150, 110, 64), (150, 110, 64), (150, 110, 64))
        q.box((lx - 0.035, my - 0.035, 0.20), (lx + 0.035, my + 0.035, 0.26),
              (120, 88, 50), (120, 88, 50), (120, 88, 50))
        q.dot((lx, my + 0.036, 0.335), 1.4,
              (198, 110, 80, 255) if i % 2 == 0 else (96, 150, 198, 255))
    # Two screw dots fixing the manifold rail to the back panel.
    for sx in (x0 + 0.14, x1 - 0.14):
        q.dot((sx, my + 0.036, 0.34), 1.0, (120, 134, 122, 255))


def thermo_head(q, cx, cy, P):
    """Thermostatic radiator head: valve body plus ribbed head."""
    # Tail pipe from the plinth + collar where the valve sits.
    _cylinder(q, cx, cy, 0.0, 0.30, 0.045,
              (150, 162, 150), (116, 130, 118), (168, 180, 168), n=12)
    _cylinder(q, cx, cy, 0.22, 0.30, 0.062,
              (116, 130, 118), (92, 106, 94), (134, 148, 136), n=12)
    # Brass valve body with side outlet stub toward +Y.
    q.box((cx - 0.055, cy - 0.055, 0.295), (cx + 0.055, cy + 0.055, 0.42),
          (196, 150, 92), (150, 110, 64), (214, 172, 112))
    q.box((cx - 0.030, cy + 0.050, 0.325), (cx + 0.030, cy + 0.130, 0.385),
          (150, 110, 64), (196, 150, 92), (196, 150, 92))
    # Head: ribbed off-white cylinder (hero) + dial ring + cap.
    _cylinder(q, cx, cy, 0.415, 0.70, 0.105,
              (238, 241, 233), (178, 190, 178), (242, 245, 238), n=28)
    for i in range(10):
        a = 0.35 + i * (math.pi - 0.7) / 9
        px, py = cx + 0.108 * math.cos(a), cy + 0.108 * math.sin(a)
        q.line([(px, py, 0.45), (px, py, 0.66)], (190, 200, 190), 0.9)
    _cylinder(q, cx, cy, 0.55, 0.60, 0.109,
              (150, 162, 150), (116, 130, 118), (168, 180, 168), n=28)
    _cylinder(q, cx, cy, 0.695, 0.74, 0.07,
              (150, 162, 150), (116, 130, 118), (168, 180, 168), n=16)
    q.dot((cx, cy + 0.071, 0.745), 1.0, (120, 134, 122, 255))
    # Setting dot on the +X flank.
    q.dot((cx + 0.106, cy, 0.575), 1.2, (198, 110, 80, 255))


def phone(q, cx, cy, P):
    """Smartphone on a dock: chart lines and bars on screen, no text."""
    w, d, h = 0.42, 0.05, 0.85
    x0, x1, y0, y1, z0, z1 = cx - w / 2, cx + w / 2, cy - d, cy, 0.10, 0.10 + h
    # Dock bar + phone slab sunk into it.
    q.box((cx - 0.28, cy - 0.10, 0.0), (cx + 0.28, cy + 0.06, 0.12),
          (96, 112, 100), (78, 94, 84), (118, 134, 122))
    q.box((x0, y0, z0 - 0.02), (x1, y1, z1),
          (150, 162, 152), (120, 134, 124), (172, 184, 174))
    q.box((x0 - 0.008, y0 - 0.008, z1 - 0.005), (x1 + 0.008, y1 + 0.008, z1 + 0.02),
          (120, 134, 124), (120, 134, 124), (120, 134, 124))
    # Screen glass on the +Y face with chart + bars + edge light.
    sx0, sx1, sz0, sz1 = cx - 0.17, cx + 0.17, 0.20, 0.86
    q.fp(sx0, sx1, y1 + 0.004, sz0, sz1, (18, 32, 28))
    pts = []
    for i in range(12):
        fx = sx0 + 0.03 + (sx1 - sx0 - 0.06) * i / 11
        fz = 0.52 + 0.10 * math.sin(i * 0.9) + 0.012 * i
        pts.append((fx, y1 + 0.006, fz))
    q.line(pts, (140, 230, 180), 1.2)
    for k, (bw, bh, col) in enumerate(((0.05, 0.10, (140, 230, 180)),
                                       (0.05, 0.16, (230, 180, 110)),
                                       (0.05, 0.08, (170, 205, 225)),
                                       (0.05, 0.13, (140, 230, 180)))):
        bx = sx0 + 0.05 + k * 0.075
        q.fp(bx, bx + bw, y1 + 0.006, 0.26, 0.26 + bh, col)
    q.fp(sx0 + 0.04, sx1 - 0.04, y1 + 0.005, sz1 - 0.055, sz1 - 0.035,
         (255, 255, 255, 70))
    q.dot((cx + 0.13, y1 + 0.006, 0.80), 1.2, (200, 110, 80, 255))
    # Side button on the +X flank.
    q.box((x1 - 0.002, cy - 0.06, 0.55), (x1 + 0.012, cy + 0.02, 0.63),
          (96, 112, 100), (96, 112, 100), (96, 112, 100))


PROPS = {
    "softener": {"fn": softener, "focus": (0.0, 0.15, 0.87), "k": 320,
                 "plinth": (0.0, 0.15, 0.62, 0.38),
                 "brief": "water softener: tall slim tank plus brine tank"},
    "filters": {"fn": filters, "focus": (0.0, 0.15, 0.52), "k": 420,
                "plinth": (0.0, 0.15, 0.70, 0.40),
                "brief": "filter station: two blue housings on bracket with valves"},
    "cabinet": {"fn": cabinet, "focus": (0.0, 0.15, 0.56), "k": 360,
                "plinth": (0.0, 0.15, 0.62, 0.38),
                "brief": "open manifold cabinet with mini brass manifold inside"},
    "thermo-head": {"fn": thermo_head, "focus": (0.0, 0.15, 0.41), "k": 640,
                    "plinth": (0.0, 0.15, 0.42, 0.28),
                    "brief": "thermostatic radiator head with valve body"},
    "phone": {"fn": phone, "focus": (0.0, 0.15, 0.50), "k": 480,
              "plinth": (0.0, 0.15, 0.42, 0.28),
              "brief": "smartphone with chart lines and bars on screen, no text"},
}
