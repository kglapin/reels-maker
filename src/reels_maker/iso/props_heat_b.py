"""Gallery props batch heat_b: valves, separator, safety, slab, AC, DC box.

Builders take ``(q, cx, cy, P)`` with all coordinates relative to the
placement center, mid-tone flat palette (area colors stay at/above
RGB 60; only tiny dots may go darker/brighter), overlapped (never
exact-touch) joints, NO contact shadows, no text decals (embossed
lines only). Paint order is the depth buffer: shell first, proud
details after their parents. Stubs start AT parent surfaces.
"""
from __future__ import annotations

import math

from reels_maker.iso.world import _cylinder, _on_cylinder

# Mid-tone shared palette (all channels >= 60 for area fills).
BRASS_L = (158, 136, 86)
BRASS_D = (116, 96, 62)
BRASS_T = (178, 156, 104)
GDARK = (66, 80, 70)
GMID = (96, 110, 100)
GLIGHT = (150, 164, 150)
GTOP = (178, 188, 176)
STEEL_L = (150, 164, 152)
STEEL_D = (100, 114, 104)
STEEL_T = (180, 192, 180)
CREAM = (243, 238, 220)
RED_L = (168, 84, 64)
RED_D = (124, 64, 54)
WHITE_F = (236, 240, 230)
WHITE_S = (210, 218, 204)
WHITE_T = (246, 248, 240)


def three_way(q, cx, cy, P):
    """Brass three-way valve: run stubs along X, branch down, actuator up."""
    zc = 0.42
    # Valve body first (hero mass, center).
    q.box((cx - 0.13, cy - 0.13, 0.30), (cx + 0.13, cy + 0.13, 0.60),
          BRASS_L, BRASS_D, BRASS_T)
    # Run stubs along X start AT the body faces (overlap 0.005).
    q.box((cx - 0.50, cy - 0.055, 0.365), (cx - 0.125, cy + 0.055, 0.475),
          BRASS_L, BRASS_D, BRASS_T)
    q.box((cx + 0.125, cy - 0.055, 0.365), (cx + 0.50, cy + 0.055, 0.475),
          BRASS_L, BRASS_D, BRASS_T)
    # End flanges + dark bore mouths (proud of the stub ends).
    for s in (-1.0, 1.0):
        xe = cx + s * 0.50
        q.box((min(xe, xe + s * 0.06), cy - 0.078, 0.345),
              (max(xe, xe + s * 0.06), cy + 0.078, 0.495),
              BRASS_D, BRASS_D, BRASS_D)
        q.disc_x(xe + s * 0.062, cy, zc, 0.038, (60, 72, 66))
    # Branch stub down from the body bottom (top overlaps into body).
    _cylinder(q, cx, cy, 0.06, 0.305, 0.055,
              BRASS_L, BRASS_D, BRASS_T, n=16)
    _cylinder(q, cx, cy, 0.24, 0.30, 0.082,
              BRASS_D, (96, 80, 52), (132, 112, 76), n=16)
    q.ground_ellipse(cx, cy, 0.075, 0.075, GDARK, z=0.06)
    # Actuator: grey block + lid, overlapping the body top.
    q.box((cx - 0.11, cy - 0.10, 0.595), (cx + 0.11, cy + 0.10, 0.85),
          GLIGHT, GMID, GTOP)
    q.box((cx - 0.12, cy - 0.11, 0.845), (cx + 0.12, cy + 0.11, 0.88),
          GMID, GDARK, GLIGHT)
    # Proud details on the +Y faces, painted last.
    q.dot((cx - 0.06, cy + 0.103, 0.76), 1.6, (140, 230, 180, 255))
    q.dot((cx + 0.06, cy + 0.103, 0.76), 1.1, (90, 104, 94, 255))
    for fz in (0.66, 0.70):
        q.line([(cx - 0.07, cy + 0.102, fz), (cx + 0.07, cy + 0.102, fz)],
               (110, 124, 114), 0.8)
    # Manual lever on the +X face + flow marks on the body +Y face.
    q.box((cx + 0.125, cy - 0.02, 0.50), (cx + 0.20, cy + 0.02, 0.54),
          RED_L, RED_D, RED_L)
    q.box((cx + 0.195, cy - 0.015, 0.50), (cx + 0.225, cy + 0.015, 0.62),
          RED_L, RED_D, RED_L)
    for fz in (0.38, 0.42):
        q.line([(cx - 0.08, cy + 0.132, fz), (cx + 0.08, cy + 0.132, fz)],
               (110, 92, 60), 0.8)


def separator(q, cx, cy, P):
    """Brass air separator pot: skirt, weld ring, top vent, side ports."""
    r, z0, z1 = 0.26, 0.10, 0.86
    # Feet pads + legs, then skirt (shell painted after covers leg tops).
    for lt in (0.785, 0.785 + 2.09, 0.785 - 2.09):
        lx, ly = cx + 0.17 * math.cos(lt), cy + 0.17 * math.sin(lt)
        q.box((lx - 0.05, ly - 0.05, 0.0), (lx + 0.05, ly + 0.05, 0.04),
              GLIGHT, GMID, GTOP)
        q.box((lx - 0.03, ly - 0.03, 0.035), (lx + 0.03, ly + 0.03, z0 + 0.02),
              GMID, GDARK, GMID)
    _cylinder(q, cx, cy, z0 - 0.02, z0 + 0.06, r * 1.09,
              BRASS_D, (96, 80, 52), (132, 112, 76), n=40)
    q.ground_ellipse(cx, cy, r * 1.09, r * 1.09, BRASS_L, z=z0 + 0.06)
    # Hero pot with stave shading.
    _cylinder(q, cx, cy, z0, z1, r, BRASS_L, BRASS_D, BRASS_T)
    for g0, g1, alpha in ((0.98, 1.06, 60), (1.06, 1.10, 30)):
        q.poly([_on_cylinder(cx, cy, r + 0.004, g0, z0 + 0.08),
                _on_cylinder(cx, cy, r + 0.004, g1, z0 + 0.08),
                _on_cylinder(cx, cy, r + 0.004, g1, z1 - 0.05),
                _on_cylinder(cx, cy, r + 0.004, g0, z1 - 0.05)],
               (255, 255, 255, alpha))
    # Weld ring splitting the shell into two courses.
    wz = z0 + (z1 - z0) / 2
    q.ground_ellipse(cx, cy, r * 1.008, r * 1.008, (110, 90, 58), z=wz)
    q.ground_ellipse(cx, cy, r * 1.008, r * 1.008, (168, 146, 96), z=wz + 0.018)
    # Side ports start AT the shell surface: inlet +X, outlet +Y.
    q.box((cx + r - 0.005, cy - 0.05, 0.50), (cx + r + 0.17, cy + 0.05, 0.60),
          BRASS_L, BRASS_D, BRASS_T)
    q.box((cx + r + 0.11, cy - 0.07, 0.48), (cx + r + 0.17, cy + 0.07, 0.62),
          BRASS_D, BRASS_D, BRASS_D)
    q.disc_x(cx + r + 0.172, cy, 0.55, 0.036, (60, 72, 66))
    q.box((cx - 0.05, cy + r - 0.005, 0.32), (cx + 0.05, cy + r + 0.17, 0.42),
          BRASS_L, BRASS_D, BRASS_T)
    q.box((cx - 0.07, cy + r + 0.11, 0.30), (cx + 0.07, cy + r + 0.17, 0.44),
          BRASS_D, BRASS_D, BRASS_D)
    # Top auto-vent: stem seated on the lid + grey cap.
    _cylinder(q, cx, cy, z1 + 0.05, z1 + 0.14, 0.035,
              BRASS_L, BRASS_D, BRASS_T, n=12)
    _cylinder(q, cx, cy, z1 + 0.135, z1 + 0.19, 0.052,
              GMID, GDARK, GLIGHT, n=12)
    q.ground_ellipse(cx, cy, 0.052, 0.052, GDARK, z=z1 + 0.19)
    # Drain stub low on +Y + embossed plate rows on the +Y face.
    q.box((cx + 0.02, cy + r - 0.005, 0.16), (cx + 0.10, cy + r + 0.10, 0.24),
          BRASS_L, BRASS_D, BRASS_T)
    q.box((cx + 0.03, cy + r + 0.10, 0.17), (cx + 0.09, cy + r + 0.13, 0.23),
          BRASS_D, BRASS_D, BRASS_D)
    m0, m1, mz0, mz1 = 1.30, 1.52, 0.60, 0.78
    q.poly([_on_cylinder(cx, cy, r + 0.008, m0, mz0),
            _on_cylinder(cx, cy, r + 0.008, m1, mz0),
            _on_cylinder(cx, cy, r + 0.008, m1, mz1),
            _on_cylinder(cx, cy, r + 0.008, m0, mz1)], (96, 78, 50))
    for fz in (0.65, 0.70, 0.74):
        q.line([_on_cylinder(cx, cy, r + 0.012, m0 + 0.05, fz),
                _on_cylinder(cx, cy, r + 0.012, m1 - 0.05, fz)],
               (190, 168, 118), 0.8)


def safety_group(q, cx, cy, P):
    """Safety group: brass bar with dial, relief valve and vent on top."""
    zc, zh = 0.42, 0.54
    # Foot flange + bottom inlet stub (top overlaps into the bar).
    q.box((cx - 0.05, cy - 0.07, 0.0), (cx + 0.09, cy + 0.07, 0.06),
          GMID, GDARK, GLIGHT)
    _cylinder(q, cx + 0.02, cy, 0.055, zh + 0.005, 0.055,
              BRASS_L, BRASS_D, BRASS_T, n=16)
    _cylinder(q, cx + 0.02, cy, 0.30, 0.38, 0.080,
              BRASS_D, (96, 80, 52), (132, 112, 76), n=16)
    # Hero brass bar + end collars + dark bore mouths.
    q.box((cx - 0.42, cy - 0.07, zc), (cx + 0.42, cy + 0.07, zh),
          BRASS_L, BRASS_D, BRASS_T)
    for s in (-1.0, 1.0):
        xe = cx + s * 0.42
        q.box((min(xe, xe + s * 0.05), cy - 0.09, zc - 0.02),
              (max(xe, xe + s * 0.05), cy + 0.09, zh + 0.02),
              BRASS_D, BRASS_D, BRASS_D)
        q.disc_x(xe + s * 0.052, cy, 0.48, 0.034, (60, 72, 66))
    # Manometer on the +Y face: neck, bezel block, rim, cream face.
    dx = cx - 0.28
    _cylinder(q, dx, cy + 0.02, zh - 0.005, 0.66, 0.032,
              BRASS_L, BRASS_D, BRASS_T, n=12)
    q.box((dx - 0.10, cy + 0.015, 0.64), (dx + 0.10, cy + 0.055, 0.92),
          GMID, GDARK, GLIGHT)
    q.disc_y(dx, cy + 0.058, 0.78, 0.125, GDARK)
    q.disc_y(dx, cy + 0.061, 0.78, 0.105, CREAM)
    for k in range(7):
        ang = math.pi * (0.15 + 0.70 * k / 6)
        hot = k >= 5
        q.line([(dx + 0.072 * math.cos(ang), cy + 0.062,
                 0.78 + 0.072 * math.sin(ang)),
                (dx + 0.090 * math.cos(ang), cy + 0.062,
                 0.78 + 0.090 * math.sin(ang))],
               RED_D if hot else (90, 104, 96), 0.8)
    q.line([(dx, cy + 0.063, 0.78),
            (dx + 0.066 * math.cos(0.9), cy + 0.063,
             0.78 + 0.066 * math.sin(0.9))], (170, 80, 55), 1.0)
    q.dot((dx, cy + 0.063, 0.78), 1.5, (60, 72, 64, 255))
    # Relief valve (middle): brass stem + red cap + side outlet pip.
    vx = cx + 0.04
    _cylinder(q, vx, cy, zh - 0.005, 0.70, 0.045,
              BRASS_L, BRASS_D, BRASS_T, n=12)
    _cylinder(q, vx, cy, 0.695, 0.755, 0.058,
              RED_L, RED_D, (182, 98, 76), n=12)
    q.ground_ellipse(vx, cy, 0.058, 0.058, RED_D, z=0.755)
    q.box((vx + 0.04, cy - 0.025, 0.60), (vx + 0.13, cy + 0.025, 0.65),
          BRASS_L, BRASS_D, BRASS_T)
    # Auto vent (right): stem + grey cap + dark top.
    ex = cx + 0.30
    _cylinder(q, ex, cy, zh - 0.005, 0.66, 0.030,
              BRASS_L, BRASS_D, BRASS_T, n=12)
    _cylinder(q, ex, cy, 0.655, 0.71, 0.050,
              GMID, GDARK, GLIGHT, n=12)
    q.ground_ellipse(ex, cy, 0.050, 0.050, (80, 92, 82), z=0.71)
    # Embossed flow marks on the bar +Y face.
    for fz in (0.455, 0.485, 0.515):
        q.line([(cx - 0.10, cy + 0.072, fz), (cx + 0.02, cy + 0.072, fz)],
               (110, 92, 60), 0.8)


def underfloor(q, cx, cy, P):
    """Underfloor loop: serpentine PEX pipes stapled on a slab cutaway."""
    SLAB_F, SLAB_S, SLAB_T = (178, 186, 174), (132, 144, 132), (196, 204, 192)
    PIPE_L, PIPE_D = (220, 140, 95), (170, 100, 64)
    # Slab cutaway + insulation strip proud of the +Y face.
    q.box((cx - 0.55, cy - 0.38, 0.0), (cx + 0.55, cy + 0.38, 0.14),
          SLAB_F, SLAB_S, SLAB_T)
    q.box((cx - 0.55, cy + 0.375, 0.02), (cx + 0.55, cy + 0.392, 0.07),
          (120, 150, 132), (120, 150, 132), (120, 150, 132))
    # Four runs along X sitting ON the slab top (overlap 0.005).
    ys = (cy - 0.27, cy - 0.09, cy + 0.09, cy + 0.27)
    for yy in ys:
        q.box((cx - 0.50, yy - 0.032, 0.135), (cx + 0.40, yy + 0.032, 0.195),
              PIPE_L, PIPE_D, PIPE_L)
    # U-bends tie the runs into one serpentine (overlap both ends).
    q.box((cx + 0.395, ys[0] - 0.032, 0.135), (cx + 0.475, ys[1] + 0.032, 0.195),
          PIPE_L, PIPE_D, PIPE_L)
    q.box((cx - 0.575, ys[1] - 0.032, 0.135), (cx - 0.495, ys[2] + 0.032, 0.195),
          PIPE_L, PIPE_D, PIPE_L)
    q.box((cx + 0.395, ys[2] - 0.032, 0.135), (cx + 0.475, ys[3] + 0.032, 0.195),
          PIPE_L, PIPE_D, PIPE_L)
    # Feed/return risers on the two free ends + collars + dark mouths.
    for yy in (ys[0], ys[3]):
        _cylinder(q, cx - 0.50, yy, 0.19, 0.42, 0.034,
                  PIPE_L, PIPE_D, PIPE_L, n=12)
        _cylinder(q, cx - 0.50, yy, 0.185, 0.25, 0.052,
                  BRASS_D, (96, 80, 52), (132, 112, 76), n=12)
        q.ground_ellipse(cx - 0.50, yy, 0.034, 0.034, (60, 72, 66), z=0.42)
    # Edge light on the slab top rim.
    q.line([(cx - 0.55, cy - 0.38, 0.142), (cx + 0.55, cy - 0.38, 0.142)],
           (214, 222, 210), 0.8)
    q.line([(cx + 0.55, cy - 0.38, 0.142), (cx + 0.55, cy + 0.38, 0.142)],
           (214, 222, 210), 0.8)


def wall_ac(q, cx, cy, P):
    """White wall-split AC on a wall chip: flap, slot, LED, drain."""
    # Wall chip + cap (backs stay clean).
    q.box((cx - 0.45, cy - 0.04, 0.0), (cx + 0.45, cy + 0.04, 1.145),
          (226, 232, 218), (200, 210, 194), (238, 242, 232))
    q.box((cx - 0.46, cy - 0.05, 1.15), (cx + 0.46, cy + 0.05, 1.19),
          (200, 210, 194), (200, 210, 194), (200, 210, 194))
    # Drain conduit first (body painted after covers the joint).
    q.box((cx + 0.30, cy + 0.035, 0.0), (cx + 0.36, cy + 0.10, 0.556),
          GMID, GDARK, GLIGHT)
    # Hero white body + top lid.
    q.box((cx - 0.40, cy + 0.035, 0.55), (cx + 0.40, cy + 0.28, 1.00),
          WHITE_F, WHITE_S, WHITE_T)
    q.box((cx - 0.41, cy + 0.03, 0.995), (cx + 0.41, cy + 0.285, 1.03),
          WHITE_S, WHITE_S, WHITE_T)
    # Outlet slot recessed on the +Y face, open flap angled out below it.
    q.box((cx - 0.32, cy + 0.278, 0.60), (cx + 0.32, cy + 0.286, 0.68),
          GDARK, GDARK, GDARK)
    q.poly([(cx - 0.34, cy + 0.282, 0.66), (cx + 0.34, cy + 0.282, 0.66),
            (cx + 0.34, cy + 0.365, 0.56), (cx - 0.34, cy + 0.365, 0.56)],
           WHITE_S)
    # Intake grille lines + status LED on the +Y face (painted last).
    for gz in (0.80, 0.85, 0.90):
        q.line([(cx - 0.25, cy + 0.282, gz), (cx + 0.25, cy + 0.282, gz)],
               (190, 200, 188), 0.8)
    q.dot((cx - 0.30, cy + 0.283, 0.71), 2.4, (140, 230, 180, 255))
    q.fp(cx + 0.14, cx + 0.26, cy + 0.282, 0.695, 0.735, (140, 230, 180))
    # Vent slots on the +X face.
    for gz in (0.74, 0.80, 0.86):
        q.line([(cx + 0.402, cy - 0.05, gz), (cx + 0.402, cy + 0.15, gz)],
               (190, 200, 188), 0.8)


def combiner(q, cx, cy, P):
    """Grey DC combiner box: door, switch, glands, feet, rain cap."""
    # Feet pads + legs (tops overlap the body underside).
    for fx in (cx - 0.24, cx + 0.24):
        for fy in (cy - 0.10, cy + 0.10):
            q.box((fx - 0.05, fy - 0.05, 0.0), (fx + 0.05, fy + 0.05, 0.05),
                  GLIGHT, GMID, GTOP)
            q.box((fx - 0.035, fy - 0.035, 0.045), (fx + 0.035, fy + 0.035, 0.31),
                  GMID, GDARK, GMID)
    # Hero body + rain cap overlapping the top.
    q.box((cx - 0.30, cy - 0.16, 0.30), (cx + 0.30, cy + 0.16, 0.95),
          GLIGHT, GMID, GTOP)
    q.box((cx - 0.32, cy - 0.18, 0.945), (cx + 0.32, cy + 0.18, 0.99),
          GMID, GDARK, GLIGHT)
    # Door panel proud of the +Y face + hinges on the right edge.
    q.box((cx - 0.26, cy + 0.155, 0.36), (cx + 0.26, cy + 0.175, 0.87),
          (170, 180, 168), (170, 180, 168), (186, 196, 184))
    for hz in (0.44, 0.78):
        q.box((cx + 0.20, cy + 0.17, hz), (cx + 0.25, cy + 0.205, hz + 0.06),
              GDARK, GDARK, GDARK)
    # Rotary switch: dark base + red handle, proud of the door.
    q.box((cx + 0.05, cy + 0.17, 0.52), (cx + 0.17, cy + 0.215, 0.64),
          GDARK, GDARK, GDARK)
    q.box((cx + 0.09, cy + 0.21, 0.55), (cx + 0.13, cy + 0.25, 0.61),
          RED_L, RED_D, RED_L)
    # Abstract amber mark + screws + LED on the door (no text).
    q.box((cx - 0.20, cy + 0.176, 0.68), (cx - 0.12, cy + 0.186, 0.76),
          (220, 150, 70), (220, 150, 70), (220, 150, 70))
    q.dot((cx - 0.22, cy + 0.178, 0.72), 0.9, (90, 104, 94, 255))
    q.dot((cx - 0.02, cy + 0.178, 0.40), 1.2, (140, 230, 180, 255))
    for fz in (0.44, 0.47, 0.50):
        q.line([(cx - 0.24, cy + 0.177, fz), (cx - 0.08, cy + 0.177, fz)],
               (110, 124, 112), 0.8)
    # Cable glands under the body (tops overlap into the underside).
    for gx in (cx - 0.18, cx, cx + 0.18):
        _cylinder(q, gx, cy, 0.22, 0.305, 0.045,
                  GMID, GDARK, GLIGHT, n=12)
        q.dot((gx, cy, 0.219), 1.0, (70, 84, 74, 255))
    # Vent slots on the +X face.
    for gz in (0.55, 0.61, 0.67):
        q.line([(cx + 0.302, cy - 0.06, gz), (cx + 0.302, cy + 0.06, gz)],
               (110, 124, 112), 0.8)


PROPS = {
    "three-way": {"fn": three_way, "focus": (0.0, 0.15, 0.45), "k": 520,
                   "plinth": (0.0, 0.15, 0.68, 0.40),
                   "brief": "brass three-way valve with actuator on pipe tee"},
    "separator": {"fn": separator, "focus": (0.0, 0.15, 0.55), "k": 500,
                  "plinth": (0.0, 0.15, 0.60, 0.38),
                  "brief": "brass air separator pot with top vent and side ports"},
    "safety-group": {"fn": safety_group, "focus": (0.0, 0.15, 0.55), "k": 520,
                     "plinth": (0.0, 0.15, 0.62, 0.38),
                     "brief": "safety group: manometer dial, valve and vent on a brass bar"},
    "underfloor": {"fn": underfloor, "focus": (0.0, 0.15, 0.26), "k": 480,
                   "plinth": (0.0, 0.15, 0.72, 0.44),
                   "brief": "underfloor loop: serpentine pipes set in a slab cutaway"},
    "wall-ac": {"fn": wall_ac, "focus": (0.0, 0.15, 0.62), "k": 340,
                "plinth": (0.0, 0.15, 0.64, 0.38),
                "brief": "white wall-split air conditioner with flap and LED"},
    "combiner": {"fn": combiner, "focus": (0.0, 0.15, 0.55), "k": 420,
                 "plinth": (0.0, 0.15, 0.58, 0.36),
                 "brief": "grey DC combiner box with cable glands and switch"},
}
