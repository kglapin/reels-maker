"""Gallery props batch hvac2 (97-111): ducts, grilles, fans, AHU, filters, AC.

Builders take ``(q, cx, cy, P)`` with all coordinates relative to the
placement center, mid-tone flat palette (area colors stay at/above
RGB 60; only tiny dots may go darker), overlapped (never exact-touch)
joints, NO contact shadows, no text decals (embossed lines only).
Paint order is the depth buffer: far parts first, proud details after
their parents. Stubs start INSIDE the parent surface.
"""
from __future__ import annotations

import math

from reels_maker.iso.world import _cylinder

# Mid-tone shared palette (all channels >= 60 for area fills).
DUCT_L = (168, 182, 170)
DUCT_D = (110, 124, 112)
DUCT_T = (196, 206, 196)
GDARK = (66, 80, 70)
GMID = (96, 110, 100)
GLIGHT = (150, 164, 150)
GTOP = (178, 188, 176)
WHITE_F = (236, 240, 230)
WHITE_S = (200, 210, 198)
WHITE_T = (246, 248, 240)
TANK_L = (150, 182, 202)
TANK_D = (104, 134, 152)
TANK_T = (182, 206, 220)
RED_L = (168, 84, 64)
RED_D = (124, 64, 54)
BORE = (60, 72, 66)
AMBER = (240, 170, 90)


def duct(q, cx, cy, P):
    """Sheet-metal duct section: saddles, hero tube, end flanges, seams."""
    for lx in (cx - 0.30, cx + 0.30):
        q.box((lx - 0.06, cy - 0.10, 0.0), (lx + 0.06, cy + 0.10, 0.05),
              GDARK, GDARK, GMID)
        q.box((lx - 0.04, cy - 0.06, 0.045), (lx + 0.04, cy + 0.06, 0.36),
              GMID, GDARK, GLIGHT)
    q.box((cx - 0.50, cy - 0.15, 0.30), (cx + 0.50, cy + 0.15, 0.70),
          DUCT_L, DUCT_D, DUCT_T)
    for s in (-1.0, 1.0):
        xe = cx + s * 0.50
        q.box((min(xe, xe + s * 0.06), cy - 0.18, 0.27),
              (max(xe, xe + s * 0.06), cy + 0.18, 0.73),
              DUCT_D, DUCT_D, DUCT_D)
        q.disc_x(xe + s * 0.062, cy, 0.50, 0.09, BORE)
    for lx in (cx - 0.30, cx + 0.30):
        q.box((lx - 0.03, cy - 0.05, 0.695), (lx + 0.03, cy + 0.05, 0.80),
              GMID, GDARK, GLIGHT)
    fy = cy + 0.152
    for fz in (0.38, 0.62):
        q.line([(cx - 0.44, fy, fz), (cx + 0.44, fy, fz)], (96, 110, 100), 0.8)
    for fx in (cx - 0.17, cx + 0.17):
        q.line([(fx, fy, 0.32), (fx, fy, 0.68)], (96, 110, 100), 0.8)


def vent_grille(q, cx, cy, P):
    """Square ventilation grille: neck, frame, panel, five slats."""
    for lx in (cx - 0.20, cx + 0.20):
        q.box((lx - 0.05, cy - 0.10, 0.0), (lx + 0.05, cy + 0.10, 0.05),
              GDARK, GDARK, GMID)
        q.box((lx - 0.03, cy - 0.06, 0.045), (lx + 0.03, cy + 0.06, 0.20),
              GMID, GDARK, GLIGHT)
    q.box((cx - 0.18, cy - 0.20, 0.35), (cx + 0.18, cy + 0.03, 0.75),
          DUCT_L, DUCT_D, DUCT_T)
    q.box((cx - 0.30, cy + 0.015, 0.10), (cx + 0.30, cy + 0.10, 0.90),
          WHITE_F, WHITE_S, WHITE_T)
    q.fp(cx - 0.24, cx + 0.24, cy + 0.102, 0.16, 0.84, (214, 222, 210))
    for z in (0.24, 0.36, 0.48, 0.60, 0.72):
        q.box((cx - 0.24, cy + 0.094, z - 0.014),
              (cx + 0.24, cy + 0.112, z + 0.014),
              GDARK, GDARK, GDARK)
    for sx in (cx - 0.26, cx + 0.26):
        for sz in (0.14, 0.86):
            q.dot((sx, cy + 0.113, sz), 0.8, (60, 72, 64, 255))


def wall_fan(q, cx, cy, P):
    """Round wall exhaust fan: plate, ring, hub, grille bars."""
    for lx in (cx - 0.18, cx + 0.18):
        q.box((lx - 0.05, cy - 0.12, 0.0), (lx + 0.05, cy + 0.04, 0.05),
              GDARK, GDARK, GMID)
        q.box((lx - 0.03, cy - 0.08, 0.045), (lx + 0.03, cy + 0.02, 0.20),
              GMID, GDARK, GLIGHT)
    q.box((cx - 0.28, cy - 0.06, 0.15), (cx + 0.28, cy + 0.02, 0.95),
          WHITE_S, WHITE_S, WHITE_T)
    q.disc_y(cx, cy + 0.025, 0.55, 0.26, WHITE_F)
    q.disc_y(cx, cy + 0.027, 0.55, 0.21, (214, 222, 210))
    for ang in (0.0, math.pi / 3, 2 * math.pi / 3):
        dx, dz = 0.19 * math.cos(ang), 0.19 * math.sin(ang)
        q.line([(cx - dx, cy + 0.030, 0.55 - dz),
                (cx + dx, cy + 0.030, 0.55 + dz)], (110, 124, 112), 1.0)
    q.disc_y(cx, cy + 0.031, 0.55, 0.07, GMID)
    q.dot((cx, cy + 0.033, 0.55), 1.0, (60, 72, 64, 255))
    for sx in (cx - 0.24, cx + 0.24):
        for sz in (0.19, 0.91):
            q.dot((sx, cy + 0.022, sz), 0.8, (60, 72, 64, 255))


def ahu(q, cx, cy, P):
    """Air handling unit: feet, hero box, lid, doors, +X fan grille."""
    for lx in (cx - 0.33, cx + 0.33):
        for ly in (cy - 0.12, cy + 0.12):
            q.box((lx - 0.05, ly - 0.05, 0.0), (lx + 0.05, ly + 0.05, 0.06),
                  GDARK, GDARK, GMID)
            q.box((lx - 0.03, ly - 0.03, 0.055), (lx + 0.03, ly + 0.03, 0.20),
                  GMID, GDARK, GLIGHT)
    q.box((cx - 0.45, cy - 0.20, 0.15), (cx + 0.45, cy + 0.20, 0.95),
          WHITE_F, WHITE_S, WHITE_T)
    q.box((cx - 0.47, cy - 0.22, 0.945), (cx + 0.47, cy + 0.22, 0.99),
          GLIGHT, GMID, GTOP)
    q.disc_x(cx + 0.452, cy, 0.55, 0.13, GDARK)
    q.disc_x(cx + 0.454, cy, 0.55, 0.10, (214, 222, 210))
    q.dot((cx + 0.456, cy, 0.55), 1.2, (60, 72, 64, 255))
    fy = cy + 0.202
    for fx in (cx - 0.15, cx + 0.15):
        q.line([(fx, fy, 0.22), (fx, fy, 0.88)], (150, 162, 150), 0.8)
    q.line([(cx - 0.41, fy, 0.30), (cx + 0.41, fy, 0.30)], (150, 162, 150), 0.8)
    q.dot((cx - 0.10, fy, 0.55), 1.0, (66, 80, 70, 255))
    q.dot((cx + 0.10, fy, 0.55), 1.0, (66, 80, 70, 255))
    q.dot((cx + 0.30, fy, 0.80), 1.1, (240, 170, 90, 255))


def recuperator(q, cx, cy, P):
    """Wall heat recovery unit: feet, box, lid, twin top ducts, vents."""
    for lx in (cx - 0.25, cx + 0.25):
        q.box((lx - 0.05, cy - 0.10, 0.0), (lx + 0.05, cy + 0.10, 0.05),
              GDARK, GDARK, GMID)
        q.box((lx - 0.03, cy - 0.06, 0.045), (lx + 0.03, cy + 0.06, 0.17),
              GMID, GDARK, GLIGHT)
    q.box((cx - 0.35, cy - 0.18, 0.12), (cx + 0.35, cy + 0.18, 0.80),
          WHITE_F, WHITE_S, WHITE_T)
    q.box((cx - 0.37, cy - 0.20, 0.795), (cx + 0.37, cy + 0.20, 0.85),
          GLIGHT, GMID, GTOP)
    for dx in (cx - 0.15, cx + 0.15):
        _cylinder(q, dx, cy, 0.80, 1.02, 0.09,
                  DUCT_L, DUCT_D, DUCT_T, n=24)
        q.ground_ellipse(dx, cy, 0.055, 0.055, BORE, z=1.075)
    fy = cy + 0.182
    q.fp(cx - 0.28, cx + 0.28, fy, 0.22, 0.68, (214, 222, 210))
    for z in (0.30, 0.40, 0.50, 0.60):
        q.box((cx - 0.24, fy - 0.002, z - 0.013),
              (cx + 0.24, fy + 0.010, z + 0.013),
              GMID, GMID, GMID)
    q.dot((cx + 0.22, fy + 0.001, 0.66), 1.0, (240, 170, 90, 255))
    q.dot((cx - 0.22, fy + 0.001, 0.66), 0.9, (66, 80, 70, 255))


def filter_box(q, cx, cy, P):
    """Filter box: feet, shell, lid, proud filter panel with rails."""
    for lx in (cx - 0.22, cx + 0.22):
        q.box((lx - 0.05, cy - 0.10, 0.0), (lx + 0.05, cy + 0.10, 0.05),
              GDARK, GDARK, GMID)
        q.box((lx - 0.03, cy - 0.06, 0.045), (lx + 0.03, cy + 0.06, 0.17),
              GMID, GDARK, GLIGHT)
    q.box((cx - 0.32, cy - 0.18, 0.12), (cx + 0.32, cy + 0.18, 0.78),
          DUCT_L, DUCT_D, DUCT_T)
    q.box((cx - 0.34, cy - 0.20, 0.775), (cx + 0.34, cy + 0.20, 0.82),
          GLIGHT, GMID, GTOP)
    q.box((cx - 0.26, cy + 0.174, 0.20), (cx + 0.26, cy + 0.205, 0.70),
          (190, 206, 196), (150, 168, 156), (206, 218, 208))
    for sx in (cx - 0.26, cx + 0.26):
        q.box((sx - 0.035, cy + 0.178, 0.18), (sx + 0.035, cy + 0.208, 0.72),
              GMID, GDARK, GLIGHT)
    fy = cy + 0.209
    for fz in (0.30, 0.42, 0.54, 0.64):
        q.line([(cx - 0.20, fy, fz), (cx + 0.20, fy, fz)], (120, 136, 124), 0.8)
    q.box((cx - 0.05, fy - 0.006, 0.22), (cx + 0.05, fy + 0.010, 0.28),
          RED_L, RED_D, RED_L)


def damper(q, cx, cy, P):
    """Round damper: feet, shell, flange rings, axle stub, lever."""
    for lx in (cx - 0.13, cx + 0.13):
        q.box((lx - 0.05, cy - 0.05, 0.0), (lx + 0.05, cy + 0.05, 0.05),
              GDARK, GDARK, GMID)
        q.box((lx - 0.03, cy - 0.03, 0.045), (lx + 0.03, cy + 0.03, 0.16),
              GMID, GDARK, GLIGHT)
    _cylinder(q, cx, cy, 0.10, 0.62, 0.22, DUCT_L, DUCT_D, DUCT_T, n=40)
    q.ground_ellipse(cx, cy, 0.246, 0.246, DUCT_D, z=0.13)
    q.ground_ellipse(cx, cy, 0.246, 0.246, (150, 164, 152), z=0.148)
    q.ground_ellipse(cx, cy, 0.246, 0.246, DUCT_D, z=0.56)
    q.ground_ellipse(cx, cy, 0.246, 0.246, (150, 164, 152), z=0.578)
    q.box((cx + 0.16, cy - 0.03, 0.40), (cx + 0.30, cy + 0.03, 0.46),
          GMID, GDARK, GLIGHT)
    q.box((cx + 0.26, cy - 0.025, 0.45), (cx + 0.31, cy + 0.025, 0.58),
          RED_L, RED_D, RED_L)
    q.dot((cx + 0.312, cy, 0.52), 1.0, (66, 80, 70, 255))
    fy = cy + 0.222
    q.line([(cx - 0.14, fy, 0.34), (cx + 0.14, fy, 0.34)], (96, 110, 100), 0.8)


def diffuser(q, cx, cy, P):
    """Round ceiling diffuser: feet, trim ring, cone, neck, cap."""
    for lt in (0.785, 0.785 + 2.09, 0.785 - 2.09):
        lx, ly = cx + 0.24 * math.cos(lt), cy + 0.24 * math.sin(lt)
        q.box((lx - 0.04, ly - 0.04, 0.0), (lx + 0.04, ly + 0.04, 0.05),
              GDARK, GDARK, GMID)
        q.box((lx - 0.025, ly - 0.025, 0.045),
              (lx + 0.025, ly + 0.025, 0.12),
              GMID, GDARK, GLIGHT)
    _cylinder(q, cx, cy, 0.08, 0.16, 0.30, WHITE_F, WHITE_S, WHITE_T, n=40)
    _cylinder(q, cx, cy, 0.155, 0.30, 0.22, WHITE_F, WHITE_S, WHITE_T, n=36)
    q.ground_ellipse(cx, cy, 0.233, 0.233, WHITE_S, z=0.30)
    q.ground_ellipse(cx, cy, 0.233, 0.233, WHITE_T, z=0.318)
    _cylinder(q, cx, cy, 0.295, 0.60, 0.14, DUCT_L, DUCT_D, DUCT_T, n=28)
    q.ground_ellipse(cx, cy, 0.154, 0.154, DUCT_D, z=0.44)
    q.ground_ellipse(cx, cy, 0.154, 0.154, (150, 164, 152), z=0.458)
    q.dot((cx, cy + 0.302, 0.12), 1.0, (66, 80, 70, 255))


def humidifier(q, cx, cy, P):
    """Small humidifier: feet, body, lid, tank, level lines, controls."""
    for lx in (cx - 0.17, cx + 0.17):
        q.box((lx - 0.05, cy - 0.08, 0.0), (lx + 0.05, cy + 0.08, 0.05),
              GDARK, GDARK, GMID)
        q.box((lx - 0.03, cy - 0.05, 0.045), (lx + 0.03, cy + 0.05, 0.10),
              GMID, GDARK, GLIGHT)
    q.box((cx - 0.25, cy - 0.16, 0.09), (cx + 0.25, cy + 0.16, 0.55),
          WHITE_F, WHITE_S, WHITE_T)
    q.box((cx - 0.27, cy - 0.18, 0.545), (cx + 0.27, cy + 0.18, 0.60),
          GLIGHT, GMID, GTOP)
    q.box((cx - 0.15, cy - 0.10, 0.595), (cx + 0.15, cy + 0.10, 0.85),
          TANK_L, TANK_D, TANK_T)
    q.box((cx - 0.17, cy - 0.12, 0.845), (cx + 0.17, cy + 0.12, 0.89),
          GMID, GDARK, GLIGHT)
    fy = cy + 0.162
    q.fp(cx - 0.19, cx + 0.19, fy, 0.14, 0.46, (214, 222, 210))
    q.line([(cx - 0.19, fy, 0.30), (cx + 0.19, fy, 0.30)], (110, 124, 114), 0.8)
    q.dot((cx - 0.12, fy, 0.38), 1.0, (66, 80, 70, 255))
    q.dot((cx + 0.12, fy, 0.38), 1.0, (240, 170, 90, 255))
    ty = cy + 0.102
    for tz in (0.66, 0.72, 0.78):
        q.line([(cx - 0.11, ty, tz), (cx + 0.11, ty, tz)], (90, 120, 140), 0.8)


def dehumidifier(q, cx, cy, P):
    """Portable dehumidifier: casters, body, lid, tank seams, display."""
    for lx in (cx - 0.20, cx + 0.20):
        _cylinder(q, lx, cy + 0.05, 0.0, 0.10, 0.06,
                  GMID, GDARK, GLIGHT, n=16)
    q.box((cx - 0.28, cy - 0.17, 0.08), (cx + 0.28, cy + 0.17, 0.75),
          WHITE_F, WHITE_S, WHITE_T)
    q.box((cx - 0.30, cy - 0.19, 0.745), (cx + 0.30, cy + 0.19, 0.79),
          GLIGHT, GMID, GTOP)
    q.box((cx - 0.10, cy - 0.06, 0.785), (cx + 0.10, cy + 0.06, 0.84),
          GMID, GDARK, GLIGHT)
    fy = cy + 0.172
    q.fp(cx - 0.22, cx + 0.22, fy, 0.16, 0.68, (214, 222, 210))
    q.line([(cx - 0.22, fy, 0.34), (cx + 0.22, fy, 0.34)], (110, 124, 114), 0.8)
    q.box((cx - 0.10, fy - 0.004, 0.52), (cx + 0.10, fy + 0.008, 0.62),
          GDARK, GDARK, GDARK)
    q.dot((cx, fy + 0.010, 0.57), 1.1, (240, 170, 90, 255))
    q.dot((cx - 0.16, fy, 0.24), 0.9, (66, 80, 70, 255))
    q.dot((cx + 0.16, fy, 0.24), 0.9, (66, 80, 70, 255))


def cassette_ac(q, cx, cy, P):
    """Ceiling cassette AC: legs, trim, hero body, neck, side slots."""
    for lx in (cx - 0.30, cx + 0.30):
        for ly in (cy - 0.20, cy + 0.20):
            q.box((lx - 0.04, ly - 0.04, 0.0), (lx + 0.04, ly + 0.04, 0.05),
                  GDARK, GDARK, GMID)
            q.box((lx - 0.025, ly - 0.025, 0.045),
                  (lx + 0.025, ly + 0.025, 0.18),
                  GMID, GDARK, GLIGHT)
    q.box((cx - 0.40, cy - 0.28, 0.10), (cx + 0.40, cy + 0.28, 0.17),
          WHITE_S, WHITE_S, WHITE_T)
    q.box((cx - 0.38, cy - 0.26, 0.14), (cx + 0.38, cy + 0.26, 0.50),
          WHITE_F, WHITE_S, WHITE_T)
    q.box((cx - 0.12, cy - 0.12, 0.495), (cx + 0.12, cy + 0.12, 0.70),
          DUCT_L, DUCT_D, DUCT_T)
    fy = cy + 0.262
    for z in (0.22, 0.30, 0.38):
        q.box((cx - 0.28, fy - 0.006, z - 0.012),
              (cx + 0.28, fy + 0.006, z + 0.012),
              GMID, GMID, GMID)
    fx = cx + 0.382
    for z in (0.24, 0.32, 0.40):
        q.box((fx - 0.006, cy - 0.20, z - 0.012),
              (fx + 0.006, cy + 0.20, z + 0.012),
              GMID, GMID, GMID)
    q.dot((cx + 0.30, fy + 0.001, 0.44), 1.0, (110, 200, 130, 255))


def console_ac(q, cx, cy, P):
    """Floor console AC: feet, body, lid, top outlet slots, panel."""
    for lx in (cx - 0.24, cx + 0.24):
        q.box((lx - 0.05, cy - 0.08, 0.0), (lx + 0.05, cy + 0.08, 0.05),
              GDARK, GDARK, GMID)
        q.box((lx - 0.03, cy - 0.05, 0.045), (lx + 0.03, cy + 0.05, 0.11),
              GMID, GDARK, GLIGHT)
    q.box((cx - 0.32, cy - 0.14, 0.06), (cx + 0.32, cy + 0.14, 0.62),
          WHITE_F, WHITE_S, WHITE_T)
    q.box((cx - 0.34, cy - 0.16, 0.615), (cx + 0.34, cy + 0.16, 0.66),
          GLIGHT, GMID, GTOP)
    for oy in (cy - 0.08, cy + 0.0, cy + 0.08):
        q.box((cx - 0.25, oy - 0.025, 0.655), (cx + 0.25, oy + 0.025, 0.68),
              GDARK, GDARK, GDARK)
    fy = cy + 0.142
    q.fp(cx - 0.26, cx + 0.26, fy, 0.14, 0.54, (214, 222, 210))
    q.line([(cx - 0.26, fy, 0.34), (cx + 0.26, fy, 0.34)], (110, 124, 114), 0.8)
    q.dot((cx + 0.20, fy, 0.46), 1.0, (110, 200, 130, 255))
    q.dot((cx - 0.20, fy, 0.24), 0.9, (66, 80, 70, 255))


def air_curtain(q, cx, cy, P):
    """Door air curtain: posts, hero bar, end caps, vent slots."""
    for ex in (cx - 0.45, cx + 0.45):
        q.box((ex - 0.05, cy - 0.07, 0.0), (ex + 0.05, cy + 0.07, 0.05),
              GDARK, GDARK, GMID)
        q.box((ex - 0.035, cy - 0.05, 0.045), (ex + 0.035, cy + 0.05, 0.78),
              GMID, GDARK, GLIGHT)
    q.box((cx - 0.49, cy - 0.10, 0.72), (cx + 0.49, cy + 0.10, 1.00),
          WHITE_F, WHITE_S, WHITE_T)
    for s in (-1.0, 1.0):
        xe = cx + s * 0.49
        q.box((min(xe, xe + s * 0.04), cy - 0.11, 0.70),
              (max(xe, xe + s * 0.04), cy + 0.11, 1.02),
              GMID, GDARK, GLIGHT)
    fy = cy + 0.102
    for i in range(4):
        x0 = cx - 0.36 + i * 0.18
        q.box((x0, fy - 0.006, 0.76), (x0 + 0.12, fy + 0.006, 0.80),
              GDARK, GDARK, GDARK)
    q.line([(cx - 0.40, fy, 0.90), (cx + 0.40, fy, 0.90)], (110, 124, 114), 0.8)
    q.dot((cx + 0.42, fy, 0.90), 1.0, (110, 200, 130, 255))


def silencer(q, cx, cy, P):
    """Duct silencer: saddles, hero shell, flanges, baffle ribs."""
    for lx in (cx - 0.28, cx + 0.28):
        q.box((lx - 0.06, cy - 0.12, 0.0), (lx + 0.06, cy + 0.12, 0.05),
              GDARK, GDARK, GMID)
        q.box((lx - 0.04, cy - 0.07, 0.045), (lx + 0.04, cy + 0.07, 0.31),
              GMID, GDARK, GLIGHT)
    q.box((cx - 0.45, cy - 0.20, 0.25), (cx + 0.45, cy + 0.20, 0.85),
          DUCT_L, DUCT_D, DUCT_T)
    for s in (-1.0, 1.0):
        xe = cx + s * 0.45
        q.box((min(xe, xe + s * 0.06), cy - 0.15, 0.30),
              (max(xe, xe + s * 0.06), cy + 0.15, 0.80),
              DUCT_D, DUCT_D, DUCT_D)
        q.disc_x(xe + s * 0.062, cy, 0.55, 0.10, BORE)
    fy = cy + 0.202
    for rx in (cx - 0.22, cx, cx + 0.22):
        q.box((rx - 0.03, fy - 0.006, 0.32), (rx + 0.03, fy + 0.006, 0.78),
              (130, 144, 132), DUCT_D, (150, 164, 152))
    for lx in (cx - 0.28, cx + 0.28):
        q.box((lx - 0.03, cy - 0.05, 0.845), (lx + 0.03, cy + 0.05, 0.93),
              GMID, GDARK, GLIGHT)


def fan_coil(q, cx, cy, P):
    """Fan coil unit: pipes, feet, body, lid, grille slots."""
    for px in (cx - 0.12, cx + 0.12):
        _cylinder(q, px, cy + 0.05, 0.02, 0.30, 0.045,
                  DUCT_L, DUCT_D, DUCT_T, n=16)
        _cylinder(q, px, cy + 0.05, 0.08, 0.14, 0.062,
                  GMID, GDARK, GLIGHT, n=16)
    for lx in (cx - 0.24, cx + 0.24):
        q.box((lx - 0.05, cy - 0.09, 0.0), (lx + 0.05, cy + 0.09, 0.05),
              GDARK, GDARK, GMID)
        q.box((lx - 0.03, cy - 0.06, 0.045), (lx + 0.03, cy + 0.06, 0.15),
              GMID, GDARK, GLIGHT)
    q.box((cx - 0.34, cy - 0.17, 0.10), (cx + 0.34, cy + 0.17, 0.72),
          WHITE_F, WHITE_S, WHITE_T)
    q.box((cx - 0.36, cy - 0.19, 0.715), (cx + 0.36, cy + 0.19, 0.76),
          GLIGHT, GMID, GTOP)
    fy = cy + 0.172
    q.fp(cx - 0.28, cx + 0.28, fy, 0.20, 0.64, (214, 222, 210))
    for z in (0.26, 0.36, 0.46, 0.56):
        q.box((cx - 0.26, fy - 0.005, z - 0.013),
              (cx + 0.26, fy + 0.007, z + 0.013),
              GMID, GMID, GMID)
    q.dot((cx + 0.24, fy + 0.001, 0.62), 1.0, (240, 170, 90, 255))


PROPS = {
    "duct": {"fn": duct, "focus": (0.0, 0.15, 0.45), "k": 520,
             "plinth": (0.0, 0.15, 0.72, 0.42),
             "brief": "sheet-metal ventilation duct section with flanges"},
    "vent-grille": {"fn": vent_grille, "focus": (0.0, 0.15, 0.50), "k": 520,
                    "plinth": (0.0, 0.15, 0.58, 0.36),
                    "brief": "square ventilation grille with slats"},
    "wall-fan": {"fn": wall_fan, "focus": (0.0, 0.15, 0.52), "k": 500,
                 "plinth": (0.0, 0.15, 0.58, 0.36),
                 "brief": "round wall exhaust fan with grille"},
    "ahu": {"fn": ahu, "focus": (0.0, 0.15, 0.55), "k": 400,
            "plinth": (0.0, 0.15, 0.72, 0.44),
            "brief": "air handling unit box with filters and fan section"},
    "recuperator": {"fn": recuperator, "focus": (0.0, 0.15, 0.60), "k": 460,
                    "plinth": (0.0, 0.15, 0.62, 0.38),
                    "brief": "wall heat recovery unit with ducts"},
    "filter-box": {"fn": filter_box, "focus": (0.0, 0.15, 0.47), "k": 520,
                   "plinth": (0.0, 0.15, 0.60, 0.37),
                   "brief": "filter box with replaceable filter"},
    "damper": {"fn": damper, "focus": (0.0, 0.15, 0.38), "k": 560,
               "plinth": (0.0, 0.15, 0.56, 0.35),
               "brief": "round damper with blade and handle"},
    "diffuser": {"fn": diffuser, "focus": (0.0, 0.15, 0.36), "k": 560,
                 "plinth": (0.0, 0.15, 0.56, 0.35),
                 "brief": "round ceiling diffuser with rings"},
    "humidifier": {"fn": humidifier, "focus": (0.0, 0.15, 0.47), "k": 540,
                   "plinth": (0.0, 0.15, 0.56, 0.35),
                   "brief": "small humidifier box with tank"},
    "dehumidifier": {"fn": dehumidifier, "focus": (0.0, 0.15, 0.45), "k": 540,
                     "plinth": (0.0, 0.15, 0.58, 0.36),
                     "brief": "portable dehumidifier with tank and display"},
    "cassette-ac": {"fn": cassette_ac, "focus": (0.0, 0.15, 0.38), "k": 480,
                    "plinth": (0.0, 0.15, 0.66, 0.42),
                    "brief": "ceiling cassette AC with grille"},
    "console-ac": {"fn": console_ac, "focus": (0.0, 0.15, 0.37), "k": 540,
                   "plinth": (0.0, 0.15, 0.60, 0.37),
                   "brief": "floor console AC unit"},
    "air-curtain": {"fn": air_curtain, "focus": (0.0, 0.15, 0.55), "k": 390,
                    "plinth": (0.0, 0.15, 0.74, 0.42),
                    "brief": "door air curtain bar with vents"},
    "silencer": {"fn": silencer, "focus": (0.0, 0.15, 0.50), "k": 500,
                 "plinth": (0.0, 0.15, 0.70, 0.42),
                 "brief": "duct silencer section with baffles"},
    "fan-coil": {"fn": fan_coil, "focus": (0.0, 0.15, 0.42), "k": 520,
                 "plinth": (0.0, 0.15, 0.62, 0.38),
                 "brief": "fan coil unit with grille and pipes"},
}
