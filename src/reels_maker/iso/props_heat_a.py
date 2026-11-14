"""Gallery batch A: indoor heat-installation props (heat pump water side).

Builders take (q, cx, cy, P); all coordinates relative to the placement
center. Mid-tone palette (fills >= RGB 60), overlapped joints, no contact
shadows, no text decals (embossed lines only). Gallery calls fn(q, 0.0,
0.15, P).
"""
from __future__ import annotations

import math

from .world import _cylinder, _on_cylinder, chamfered_box

BRASS_F, BRASS_S, BRASS_T = (208, 160, 94), (158, 116, 66), (228, 182, 112)
BRASS_D = (120, 86, 50)
COPPER_L, COPPER_D, COPPER_T = (198, 112, 72), (148, 78, 48), (218, 140, 95)
STEEL_F, STEEL_S, STEEL_T = (150, 164, 152), (112, 128, 116), (172, 186, 174)
CREAM_F, CREAM_S, CREAM_T = (236, 240, 228), (170, 190, 168), (244, 248, 240)
BODY_F, BODY_S, BODY_T = (226, 234, 222), (158, 180, 158), (242, 248, 240)
PANEL = (62, 80, 72)
TRIM = (96, 112, 100)


def hydrobox(q, cx, cy, P):
    """Tall indoor heat-pump box: lid, screen bars, side pipes, feet."""
    # Feet pads + feet (tops overlap the body underside).
    for fx in (cx - 0.26, cx + 0.26):
        for fy in (cy - 0.17, cy + 0.17):
            q.box((fx - 0.06, fy - 0.06, 0.0), (fx + 0.06, fy + 0.06, 0.05),
                  (110, 124, 112), (88, 102, 92), (128, 142, 130))
            q.box((fx - 0.04, fy - 0.04, 0.04), (fx + 0.04, fy + 0.04, 0.16),
                  (70, 86, 74), (70, 86, 74), (70, 86, 74))
    # Hero body + overlapping lid: chamfered edges catch light like a
    # manufactured enclosure instead of a card block.
    chamfered_box(q, (cx - 0.35, cy - 0.25, 0.10), (cx + 0.35, cy + 0.25, 1.40),
                  chamfer=0.035, c=BODY_F)
    chamfered_box(q, (cx - 0.36, cy - 0.26, 1.36), (cx + 0.36, cy + 0.26, 1.46),
                  chamfer=0.03, c=BODY_S)
    # Screen panel + abstract bars + status dot on the +Y face.
    q.fp(cx - 0.20, cx + 0.20, cy + 0.252, 0.95, 1.22, PANEL)
    for j, (hgt, col) in enumerate(((0.10, (110, 190, 170)),
                                    (0.07, (220, 150, 60)),
                                    (0.05, (110, 190, 170)))):
        q.fp(cx - 0.16 + j * 0.11, cx - 0.16 + j * 0.11 + 0.08,
             cy + 0.254, 1.00, 1.00 + hgt, col)
    q.dot((cx + 0.16, cy + 0.254, 1.15), 0.9, (110, 190, 170, 255))
    # Embossed vent lines (abstract, low) on the +Y face.
    for dz in (0.35, 0.42, 0.49, 0.56):
        q.line([(cx - 0.25, cy + 0.252, dz), (cx + 0.25, cy + 0.252, dz)],
               (150, 172, 150), 0.8)
    # Two copper flow/return stubs on the +X face + collars straddling.
    for dz in (0.30, 0.52):
        q.box((cx + 0.35, cy - 0.05, dz - 0.045), (cx + 0.52, cy + 0.05, dz + 0.045),
              COPPER_D, COPPER_L, COPPER_L)
        q.box((cx + 0.33, cy - 0.075, dz - 0.07), (cx + 0.42, cy + 0.075, dz + 0.07),
              TRIM, TRIM, TRIM)
    # Condensate drain straddling the bottom-front edge.
    q.box((cx - 0.20, cy + 0.15, 0.02), (cx - 0.12, cy + 0.30, 0.16),
          STEEL_S, STEEL_S, STEEL_T)


def manifold(q, cx, cy, P):
    """Brass heating manifold bar: 4 top valves, 2 gauges, drains, feet."""
    zc, zh = 0.40, 0.52
    # Slim bracket posts rising into the bar underside (never past it:
    # tall posts in front steal the hero read from the brass bar).
    for fx in (cx - 0.30, cx + 0.30):
        q.box((fx - 0.07, cy - 0.09, 0.0), (fx + 0.07, cy + 0.09, 0.06),
              (110, 124, 112), (88, 102, 92), (128, 142, 130))
        q.box((fx - 0.045, cy - 0.035, 0.05), (fx + 0.045, cy + 0.035, zc + 0.02),
              TRIM, TRIM, TRIM)
    # Hero brass bar + end caps.
    q.box((cx - 0.45, cy - 0.06, zc), (cx + 0.45, cy + 0.06, zh),
          BRASS_F, BRASS_S, BRASS_T)
    for ex in (cx - 0.45, cx + 0.45):
        q.box((ex - 0.035, cy - 0.085, zc - 0.02), (ex + 0.035, cy + 0.085, zh + 0.02),
              BRASS_D, BRASS_D, BRASS_D)
    # Four top valves: stem starts AT the bar top, collar straddles joint.
    for i, vx in enumerate((cx - 0.30, cx - 0.10, cx + 0.10, cx + 0.30)):
        _cylinder(q, vx, cy, zh, zh + 0.13, 0.032,
                  COPPER_L, COPPER_D, COPPER_T, n=12)
        _cylinder(q, vx, cy, zh - 0.02, zh + 0.05, 0.050,
                  BRASS_S, BRASS_D, BRASS_F, n=12)
        cap = (200, 90, 70) if i % 2 == 0 else (90, 140, 190)
        q.box((vx - 0.045, cy - 0.045, zh + 0.12), (vx + 0.045, cy + 0.045, zh + 0.19),
              cap, cap, cap)
    # Two compact gauges fused on the +Y face: mount, rim, cream face.
    for gx in (cx - 0.20, cx + 0.20):
        q.box((gx - 0.06, cy + 0.055, zc - 0.01), (gx + 0.06, cy + 0.075, zh + 0.01),
              TRIM, TRIM, TRIM)
        q.disc_y(gx, cy + 0.078, 0.46, 0.050, (70, 84, 74))
        q.disc_y(gx, cy + 0.080, 0.46, 0.040, (243, 238, 220))
        for k in range(5):
            ang = math.pi * (0.15 + 0.70 * k / 4)
            q.line([(gx + 0.034 * math.cos(ang), cy + 0.081, 0.46 + 0.034 * math.sin(ang)),
                    (gx + 0.044 * math.cos(ang), cy + 0.081, 0.46 + 0.044 * math.sin(ang))],
                   (90, 104, 96), 0.8)
        q.line([(gx, cy + 0.082, 0.46),
                (gx + 0.032 * math.cos(0.9), cy + 0.082, 0.46 + 0.032 * math.sin(0.9))],
               (180, 90, 50), 1.0)
        q.dot((gx, cy + 0.082, 0.46), 1.0, (60, 72, 64, 255))
    # Drain cocks under both ends (overlap the end caps).
    for ex in (cx - 0.45, cx + 0.45):
        q.box((ex - 0.03, cy - 0.03, zc - 0.12), (ex + 0.03, cy + 0.03, zc + 0.0),
              COPPER_D, COPPER_L, COPPER_L)
        q.box((ex - 0.045, cy - 0.02, zc - 0.14), (ex + 0.045, cy + 0.02, zc - 0.10),
              BRASS_D, BRASS_D, BRASS_D)


def zone_valve(q, cx, cy, P):
    """Brass zone valve on a flanged pipe stub, actuator box on top."""
    zp = 0.32
    # Support foot + pad under the pipe (overlap the pipe underside).
    q.box((cx - 0.07, cy - 0.09, 0.0), (cx + 0.07, cy + 0.09, 0.06),
          (110, 124, 112), (88, 102, 92), (128, 142, 130))
    q.box((cx - 0.045, cy - 0.05, 0.05), (cx + 0.045, cy + 0.05, zp - 0.05),
          TRIM, TRIM, TRIM)
    # Copper pipe stub (contrast against the grey hardware around it) +
    # flange rings + gaskets.
    q.box((cx - 0.35, cy - 0.07, zp - 0.07), (cx + 0.35, cy + 0.07, zp + 0.07),
          COPPER_L, COPPER_D, COPPER_T)
    for ex in (cx - 0.29, cx + 0.29):
        q.box((ex - 0.04, cy - 0.11, zp - 0.11), (ex + 0.04, cy + 0.11, zp + 0.11),
              TRIM, TRIM, TRIM)
        out = 1 if ex > cx else -1
        q.box((ex + out * 0.04 - out * 0.005, cy - 0.085, zp - 0.085),
              (ex + out * 0.065, cy + 0.085, zp + 0.085),
              (70, 84, 74), (70, 84, 74), (70, 84, 74))
        q.dot((ex, cy + 0.112, zp + 0.06), 0.9, (150, 130, 80, 255))
        q.dot((ex, cy + 0.112, zp - 0.06), 0.9, (150, 130, 80, 255))
    # Brass valve body around the pipe center (overlaps the pipe).
    q.box((cx - 0.11, cy - 0.10, zp - 0.10), (cx + 0.11, cy + 0.10, zp + 0.10),
          BRASS_F, BRASS_S, BRASS_T)
    # Brass bonnet neck (wide, visible) + stem AT the body top + collar.
    q.box((cx - 0.07, cy - 0.07, zp + 0.06), (cx + 0.07, cy + 0.07, zp + 0.20),
          BRASS_F, BRASS_S, BRASS_T)
    _cylinder(q, cx, cy, zp + 0.10, zp + 0.21, 0.035,
              COPPER_L, COPPER_D, COPPER_T, n=12)
    _cylinder(q, cx, cy, zp + 0.06, zp + 0.15, 0.075,
              BRASS_S, BRASS_D, BRASS_F, n=12)
    # Coupling nut proud of the bonnet +Y face (after parents).
    q.box((cx - 0.05, cy + 0.065, zp + 0.095), (cx + 0.05, cy + 0.115, zp + 0.17),
          BRASS_D, BRASS_D, BRASS_D)
    # Compact actuator on a stepped skirt (a bulky box would swallow
    # the valve read; depth order: skirt, then box, then lid).
    q.box((cx - 0.12, cy - 0.09, zp + 0.18), (cx + 0.12, cy + 0.09, zp + 0.23),
          TRIM, TRIM, TRIM)
    q.box((cx - 0.10, cy - 0.085, zp + 0.21), (cx + 0.10, cy + 0.085, zp + 0.37),
          (130, 144, 130), (104, 120, 106), (152, 166, 152))
    q.box((cx - 0.105, cy - 0.09, zp + 0.35), (cx + 0.105, cy + 0.09, zp + 0.40),
          TRIM, TRIM, TRIM)
    # Status dot + embossed lines on the actuator +Y face (proud, after).
    q.dot((cx + 0.09, cy + 0.088, zp + 0.33), 1.0, (110, 190, 170, 255))
    for dz in (zp + 0.24, zp + 0.28):
        q.line([(cx - 0.08, cy + 0.087, dz), (cx + 0.08, cy + 0.087, dz)],
               (96, 112, 100), 0.8)


def plate_hx(q, cx, cy, P):
    """Ribbed plate heat exchanger: ribbed box, 4 side ports, rails."""
    # Foot rails + pads (body painted after covers the overlap).
    for fy in (cy - 0.11, cy + 0.11):
        q.box((cx - 0.20, fy - 0.05, 0.0), (cx + 0.20, fy + 0.05, 0.05),
              (110, 124, 112), (88, 102, 92), (128, 142, 130))
        q.box((cx - 0.18, fy - 0.035, 0.04), (cx + 0.18, fy + 0.035, 0.16),
              TRIM, TRIM, TRIM)
    # Hero ribbed body + overlapping top cap: chamfered edges.
    chamfered_box(q, (cx - 0.25, cy - 0.18, 0.10), (cx + 0.25, cy + 0.18, 0.80),
                  chamfer=0.025, c=CREAM_F)
    chamfered_box(q, (cx - 0.26, cy - 0.19, 0.76), (cx + 0.26, cy + 0.19, 0.85),
                  chamfer=0.02, c=STEEL_S)
    # Chevron ribs proud of the +Y face, then the +X face (after body).
    for i in range(6):
        rx = cx - 0.20 + i * 0.08
        q.box((rx - 0.02, cy + 0.18, 0.14), (rx + 0.02, cy + 0.205, 0.72),
              STEEL_F, STEEL_F, STEEL_T)
    for i in range(4):
        ry = cy - 0.12 + i * 0.08
        q.box((cx + 0.25, ry - 0.02, 0.14), (cx + 0.275, ry + 0.02, 0.72),
              STEEL_S, STEEL_S, STEEL_T)
    # Four side ports: stubs rooted INSIDE the body (painter draws them
    # after, so buried starts never overdraw the face), collars straddle.
    for dz in (0.30, 0.60):
        q.box((cx + 0.20, cy - 0.045, dz - 0.045), (cx + 0.40, cy + 0.045, dz + 0.045),
              COPPER_D, COPPER_L, COPPER_L)
        q.box((cx + 0.18, cy - 0.065, dz - 0.065), (cx + 0.28, cy + 0.065, dz + 0.065),
              TRIM, TRIM, TRIM)
        q.box((cx - 0.06, cy + 0.13, dz - 0.045), (cx + 0.06, cy + 0.33, dz + 0.045),
              COPPER_D, COPPER_D, COPPER_L)
        q.box((cx - 0.08, cy + 0.11, dz - 0.065), (cx + 0.08, cy + 0.21, dz + 0.065),
              TRIM, TRIM, TRIM)


def dhw_tank(q, cx, cy, P):
    """Tall slim DHW cylinder: skirt, shell, coil ports, thermometer, legs."""
    r, z0, z1 = 0.30, 0.18, 1.30
    # Leg pads + three legs (shell painted after covers leg tops).
    for lt in (0.785, 0.785 + 2.09, 0.785 - 2.09):
        lx, ly = cx + 0.20 * math.cos(lt), cy + 0.20 * math.sin(lt)
        q.box((lx - 0.06, ly - 0.06, 0.0), (lx + 0.06, ly + 0.06, 0.045),
              (150, 166, 154), (132, 148, 136), (165, 181, 169))
        q.box((lx - 0.035, ly - 0.035, 0.04), (lx + 0.035, ly + 0.035, z0 + 0.04),
              TRIM, TRIM, TRIM)
    # Skirt + cream shell (hero) with gloss bands on the visible flank.
    _cylinder(q, cx, cy, z0 - 0.02, z0 + 0.06, r * 1.08, (150, 164, 150),
              (104, 120, 104), (168, 182, 168), n=40)
    q.ground_ellipse(cx, cy, r * 1.08, r * 1.08, (150, 164, 150), z=z0 + 0.06)
    _cylinder(q, cx, cy, z0, z1, r, CREAM_F, CREAM_S, CREAM_T)
    for g0, g1, alpha in ((0.98, 1.06, 60), (1.06, 1.10, 30)):
        q.poly([_on_cylinder(cx, cy, r + 0.004, g0, z0 + 0.10),
                _on_cylinder(cx, cy, r + 0.004, g1, z0 + 0.10),
                _on_cylinder(cx, cy, r + 0.004, g1, z1 - 0.08),
                _on_cylinder(cx, cy, r + 0.004, g0, z1 - 0.08)],
               (255, 255, 255, alpha))
    # Weld ring splitting the shell into two courses.
    wz = z0 + (z1 - z0) / 2
    q.ground_ellipse(cx, cy, r * 1.008, r * 1.008, (150, 172, 158), z=wz)
    q.ground_ellipse(cx, cy, r * 1.008, r * 1.008, (210, 224, 210), z=wz + 0.018)
    # Two coil ports on the +Y face: stubs sunk into the shell + collars.
    for dz in (0.50, 0.92):
        q.box((cx - 0.05, cy + r - 0.06, dz - 0.045),
              (cx + 0.05, cy + r + 0.09, dz + 0.045),
              COPPER_D, COPPER_D, COPPER_L)
        q.box((cx - 0.07, cy + r - 0.05, dz - 0.065),
              (cx + 0.07, cy + r + 0.02, dz + 0.065),
              TRIM, TRIM, TRIM)
    # Thermometer dial wrapped ON the shell surface via _on_cylinder —
    # conforms to the curve, so nothing is buried or floating.
    rs = r + 0.004
    th = math.pi / 2 + 0.267          # ~x offset -0.08 on the +Y flank
    q.poly([_on_cylinder(cx, cy, rs, th - 0.165, 0.968),
            _on_cylinder(cx, cy, rs, th + 0.165, 0.968),
            _on_cylinder(cx, cy, rs, th + 0.165, 1.072),
            _on_cylinder(cx, cy, rs, th - 0.165, 1.072)], TRIM)
    q.poly([_on_cylinder(cx, cy, rs, th - 0.125, 0.982),
            _on_cylinder(cx, cy, rs, th + 0.125, 0.982),
            _on_cylinder(cx, cy, rs, th + 0.125, 1.058),
            _on_cylinder(cx, cy, rs, th - 0.125, 1.058)], (243, 238, 220))
    hub = _on_cylinder(cx, cy, rs, th, 1.02)
    tip = _on_cylinder(cx, cy, rs, th + 0.021, 1.041)
    q.line([hub, tip], (180, 90, 50), 1.0)
    q.dot(hub, 1.2, (60, 72, 64, 255))
    # Top vent: stubby brass stem + cap seated on the lid.
    _cylinder(q, cx, cy, z1 + 0.05, z1 + 0.10, 0.040,
              (150, 130, 80), (110, 92, 58), (170, 150, 100), n=12)
    q.box((cx - 0.028, cy - 0.028, z1 + 0.10), (cx + 0.028, cy + 0.028, z1 + 0.13),
          (110, 92, 58), (110, 92, 58), (130, 110, 70))


PROPS = {
    "hydrobox": {"fn": hydrobox, "focus": (0.0, 0.15, 0.75), "k": 300,
                 "plinth": (0.0, 0.15, 0.62, 0.40),
                 "brief": "tall indoor heat-pump box with screen bars, pipes at bottom, feet"},
    "manifold": {"fn": manifold, "focus": (0.0, 0.15, 0.30), "k": 480,
                 "plinth": (0.0, 0.15, 0.62, 0.36),
                 "brief": "brass heating manifold bar with 4 valves, 2 gauges, drain cocks on bracket feet"},
    "zone-valve": {"fn": zone_valve, "focus": (0.0, 0.15, 0.25), "k": 500,
                   "plinth": (0.0, 0.15, 0.55, 0.34),
                   "brief": "brass zone valve with actuator box on a flanged pipe stub"},
    "plate-hx": {"fn": plate_hx, "focus": (0.0, 0.15, 0.40), "k": 440,
                 "plinth": (0.0, 0.15, 0.55, 0.34),
                 "brief": "ribbed plate heat exchanger box with 4 side ports"},
    "dhw-tank": {"fn": dhw_tank, "focus": (0.0, 0.15, 0.65), "k": 330,
                 "plinth": (0.0, 0.15, 0.55, 0.36),
                 "brief": "tall slim DHW cylinder with coil ports, thermometer dot, feet"},
}
