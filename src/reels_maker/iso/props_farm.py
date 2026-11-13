"""Farm props batch (67-81): tractor, cow, hay bale, silo, trough, coop,
greenhouse, beehive, orchard tree, windmill, auger, scarecrow, polytunnel,
dog house, pond.

Builders take ``(q, cx, cy, P)`` with all coordinates relative to the
placement center. Mid-tone flat palette (no channel below RGB 60 except
tiny dots), overlapped (never exact-touch) joints, NO contact shadows,
no text decals (embossed lines only). Details live on +X/+Y faces.
"""
from __future__ import annotations

import math

from .world import _cylinder, _on_cylinder


def tractor(q, cx, cy, P):
    """Small farm tractor: red body hero, cab glass, 4 wheels, exhaust."""
    # Chassis hero first, then hood and cab overlapping into it.
    q.box((cx - 0.42, cy - 0.14, 0.28), (cx + 0.44, cy + 0.14, 0.52),
          (198, 84, 66), (150, 62, 50), (214, 104, 84))
    q.box((cx + 0.10, cy - 0.12, 0.50), (cx + 0.48, cy + 0.12, 0.70),
          (190, 78, 60), (144, 58, 46), (206, 98, 78))
    q.box((cx - 0.44, cy - 0.13, 0.50), (cx - 0.02, cy + 0.13, 1.02),
          (198, 84, 66), (150, 62, 50), (214, 104, 84))
    q.box((cx - 0.47, cy - 0.16, 1.00), (cx + 0.01, cy + 0.16, 1.08),
          (238, 234, 220), (200, 198, 184), (246, 244, 232))
    # Cab glass on the +Y flank and the +X cab face, then grille + lights.
    q.fp(cx - 0.40, cx - 0.06, cy + 0.131, 0.62, 0.94, (168, 198, 212))
    q.poly([(cx - 0.019, cy - 0.08, 0.62), (cx - 0.019, cy + 0.08, 0.62),
            (cx - 0.019, cy + 0.08, 0.94), (cx - 0.019, cy - 0.08, 0.94)],
           (168, 198, 212))
    q.poly([(cx - 0.30, cy + 0.132, 0.66), (cx - 0.16, cy + 0.132, 0.66),
            (cx - 0.20, cy + 0.132, 0.90), (cx - 0.32, cy + 0.132, 0.90)],
           (255, 255, 255, 70))
    q.box((cx + 0.47, cy - 0.10, 0.30), (cx + 0.495, cy + 0.10, 0.55),
          (80, 90, 84), (80, 90, 84), (80, 90, 84))
    q.dot((cx + 0.496, cy - 0.06, 0.48), 1.2, (255, 240, 180, 255))
    q.dot((cx + 0.496, cy + 0.06, 0.48), 1.2, (255, 240, 180, 255))
    # Exhaust stub starts inside the hood, cap dot on top.
    _cylinder(q, cx + 0.35, cy - 0.05, 0.60, 0.95, 0.035,
              (90, 100, 94), (70, 80, 74), (110, 120, 114), n=12)
    q.dot((cx + 0.35, cy - 0.05, 1.005), 0.9, (60, 70, 64, 255))
    # Footstep proud of the +Y flank.
    q.box((cx - 0.02, cy + 0.135, 0.30), (cx + 0.14, cy + 0.20, 0.35),
          (110, 120, 112), (88, 98, 90), (130, 140, 132))
    # Wheels proud of the +Y flank, hubs after the tyres.
    for wx, wr in ((cx - 0.28, 0.17), (cx + 0.30, 0.115)):
        q.disc_y(wx, cy + 0.142, 0.17 if wr > 0.15 else 0.115, wr,
                 (70, 78, 70))
    for wx, wr, hr in ((cx - 0.28, 0.17, 0.075), (cx + 0.30, 0.115, 0.05)):
        q.disc_y(wx, cy + 0.144, wr, hr, (190, 190, 180))
        q.dot((wx, cy + 0.146, wr), 1.0, (90, 100, 92, 255))


def cow(q, cx, cy, P):
    """Standing dairy cow: body, head, legs, udder, spots, tail."""
    # Far legs first (behind the body), near legs last.
    for lx in (cx - 0.30, cx + 0.22):
        q.box((lx - 0.045, cy - 0.145, -0.01), (lx + 0.045, cy - 0.055, 0.45),
              (225, 228, 220), (200, 204, 196), (235, 238, 230))
        q.box((lx - 0.05, cy - 0.15, -0.01), (lx + 0.05, cy - 0.05, 0.06),
              (90, 80, 70), (70, 62, 54), (110, 100, 88))
    q.box((cx - 0.45, cy - 0.16, 0.40), (cx + 0.32, cy + 0.16, 0.72),
          (238, 240, 232), (206, 212, 200), (246, 248, 242))
    # Brown patches flat on the +Y flank.
    q.fp(cx - 0.38, cx - 0.16, cy + 0.161, 0.48, 0.68, (150, 110, 80))
    q.fp(cx - 0.02, cx + 0.20, cy + 0.161, 0.44, 0.62, (150, 110, 80))
    # Head overlaps the body front; muzzle overlaps the head.
    q.box((cx + 0.28, cy - 0.10, 0.55), (cx + 0.55, cy + 0.10, 0.90),
          (235, 237, 229), (203, 209, 197), (244, 246, 240))
    q.box((cx + 0.53, cy - 0.07, 0.58), (cx + 0.62, cy + 0.07, 0.72),
          (205, 150, 140), (175, 125, 118), (218, 168, 158))
    q.line([(cx + 0.53, cy + 0.071, 0.62), (cx + 0.62, cy + 0.071, 0.62)],
           (150, 105, 95), 0.8)
    # Ear + horns on top, eyes on the +Y face.
    q.box((cx + 0.34, cy + 0.095, 0.82), (cx + 0.46, cy + 0.15, 0.90),
          (225, 228, 220), (200, 204, 196), (235, 238, 230))
    for hx in (cx + 0.36, cx + 0.48):
        _cylinder(q, hx, cy, 0.885, 0.96, 0.022,
                  (210, 195, 170), (175, 160, 140), (220, 205, 180), n=8)
    q.dot((cx + 0.44, cy + 0.101, 0.76), 0.9, (40, 44, 40, 255))
    # Udder tucked under the belly.
    q.box((cx - 0.15, cy - 0.08, 0.28), (cx + 0.05, cy + 0.08, 0.42),
          (240, 200, 190), (215, 170, 160), (246, 214, 204))
    for ux in (cx - 0.10, cx + 0.0):
        q.dot((ux, cy + 0.02, 0.275), 0.6, (200, 150, 140, 255))
    # Near legs + tail switch.
    for lx in (cx - 0.30, cx + 0.22):
        q.box((lx - 0.045, cy + 0.055, -0.01), (lx + 0.045, cy + 0.145, 0.45),
              (232, 235, 227), (206, 210, 202), (240, 243, 236))
        q.box((lx - 0.05, cy + 0.05, -0.01), (lx + 0.05, cy + 0.15, 0.06),
              (90, 80, 70), (70, 62, 54), (110, 100, 88))
    q.line([(cx - 0.44, cy, 0.68), (cx - 0.52, cy - 0.02, 0.30)],
           (225, 228, 220), 1.0)
    q.dot((cx - 0.52, cy - 0.02, 0.28), 1.0, (90, 80, 70, 255))


def hay_bale(q, cx, cy, P):
    """Round hay bale: stave-shaded cylinder with twine lines."""
    # No foot ring: the buried foot grounds itself; the rim ellipse
    # would read as a stray dark halo on the plinth (triage DISC).
    _cylinder(q, cx, cy, -0.01, 0.55, 0.42,
              (214, 180, 120), (160, 128, 84), (226, 194, 134), n=36,
              rim=False)
    # Twine lines running over the top on the visible quadrant.
    for th in (0.85, 1.05, 1.25):
        q.line([_on_cylinder(cx, cy, 0.424, th, 0.06),
                _on_cylinder(cx, cy, 0.424, th, 0.53)],
               (150, 120, 80), 1.0)
    # Spiral hint on the cap: two smaller rings just above the top.
    q.ground_ellipse(cx, cy, 0.26, 0.26, (206, 170, 112), z=0.606)
    q.ground_ellipse(cx, cy, 0.12, 0.12, (196, 160, 104), z=0.612)
    # Loose straw band shading low on the visible face.
    q.poly([_on_cylinder(cx, cy, 0.424, 0.80, 0.10),
            _on_cylinder(cx, cy, 0.424, 1.30, 0.10),
            _on_cylinder(cx, cy, 0.424, 1.30, 0.20),
            _on_cylinder(cx, cy, 0.424, 0.80, 0.20)],
           (255, 240, 200, 45))


def silo(q, cx, cy, P):
    """Farm silo tower: slab, stave body, cone roof, ladder, hatch."""
    q.box((cx - 0.42, cy - 0.30, -0.01), (cx + 0.42, cy + 0.30, 0.10),
          (202, 208, 198), (172, 184, 172), (222, 228, 218))
    _cylinder(q, cx, cy, 0.08, 1.50, 0.34,
              (210, 220, 215), (150, 170, 160), (225, 235, 228), n=36)
    # Hoop rings as closed line loops at three heights.
    for z in (0.45, 0.85, 1.25):
        pts = [_on_cylinder(cx, cy, 0.344, a, z)
               for a in [i * math.tau / 24 for i in range(25)]]
        q.line(pts, (130, 150, 142), 0.9)
    # Cone roof: three shrinking stacked drums + vent cap.
    _cylinder(q, cx, cy, 1.48, 1.58, 0.30,
              (196, 128, 104), (150, 94, 76), (210, 144, 120), n=32)
    _cylinder(q, cx, cy, 1.56, 1.66, 0.22,
              (196, 128, 104), (150, 94, 76), (210, 144, 120), n=28)
    _cylinder(q, cx, cy, 1.64, 1.74, 0.13,
              (196, 128, 104), (150, 94, 76), (210, 144, 120), n=20)
    _cylinder(q, cx, cy, 1.72, 1.82, 0.05,
              (120, 130, 124), (96, 106, 100), (140, 150, 144), n=10)
    # Ladder rails buried at the drum face, rungs after the rails.
    # Feet stop inside the base slab (top z=0.10) — starting at z=-0.01
    # made them read as legs piercing the plinth.
    for rx in (cx - 0.07, cx + 0.07):
        q.box((rx - 0.016, cy + 0.315, 0.05), (rx + 0.016, cy + 0.365, 1.45),
              (110, 120, 112), (88, 98, 90), (130, 140, 132))
    for z in [0.20 + i * 0.15 for i in range(8)]:
        q.line([(cx - 0.086, cy + 0.366, z), (cx + 0.086, cy + 0.366, z)],
               (90, 100, 92), 0.9)
    # Base hatch proud of the +Y face.
    q.box((cx - 0.10, cy + 0.30, 0.10), (cx + 0.10, cy + 0.38, 0.35),
          (150, 170, 160), (120, 142, 132), (170, 190, 180))
    q.dot((cx + 0.06, cy + 0.381, 0.24), 0.8, (70, 84, 76, 255))


def water_trough(q, cx, cy, P):
    """Cattle water trough: galvanised body, water inset, rim, legs."""
    # Far legs first, then the body over their tops.
    for lx in (cx - 0.32, cx + 0.32):
        q.box((lx - 0.04, cy - 0.16, -0.01), (lx + 0.04, cy - 0.08, 0.42),
              (110, 120, 112), (88, 98, 90), (130, 140, 132))
    q.box((cx - 0.48, cy - 0.18, 0.35), (cx + 0.48, cy + 0.18, 0.62),
          (170, 190, 195), (130, 155, 160), (190, 208, 212))
    # Water surface sunk below the rim.
    q.box((cx - 0.44, cy - 0.14, 0.50), (cx + 0.44, cy + 0.14, 0.575),
          (120, 180, 200), (120, 180, 200), (150, 200, 215))
    q.poly([_on_cylinder(cx - 0.2, cy, 0.10, 0.9, 0.576),
            _on_cylinder(cx - 0.2, cy, 0.10, 1.2, 0.576),
            _on_cylinder(cx + 0.2, cy, 0.10, 1.2, 0.576),
            _on_cylinder(cx + 0.2, cy, 0.10, 0.9, 0.576)],
           (255, 255, 255, 60))
    # Rim rails on the wall tops: ends first, front rail after.
    for ex in (cx - 0.48, cx + 0.42):
        q.box((ex, cy - 0.18, 0.61), (ex + 0.06, cy + 0.18, 0.665),
              (150, 170, 175), (120, 142, 147), (172, 192, 197))
    q.box((cx - 0.48, cy + 0.155, 0.61), (cx + 0.48, cy + 0.205, 0.665),
          (150, 170, 175), (120, 142, 147), (172, 192, 197))
    # Near legs + float valve dot on the +Y face.
    for lx in (cx - 0.32, cx + 0.32):
        q.box((lx - 0.04, cy + 0.08, -0.01), (lx + 0.04, cy + 0.16, 0.42),
              (120, 130, 122), (96, 106, 98), (140, 150, 142))
    q.box((cx + 0.20, cy + 0.18, 0.40), (cx + 0.30, cy + 0.22, 0.52),
          (200, 170, 110), (170, 142, 90), (214, 186, 128))
    q.dot((cx + 0.25, cy + 0.221, 0.50), 0.8, (110, 90, 60, 255))


def chicken_coop(q, cx, cy, P):
    """Small chicken coop: legged hut, cap roof, door, ramp, nest box."""
    for lx in (cx - 0.30, cx + 0.30):
        for ly in (cy - 0.20, cy + 0.20):
            q.box((lx - 0.035, ly - 0.035, -0.01),
                  (lx + 0.035, ly + 0.035, 0.30),
                  (140, 112, 80), (114, 90, 64), (160, 132, 98))
    q.box((cx - 0.38, cy - 0.26, 0.26), (cx + 0.38, cy + 0.26, 0.34),
          (140, 112, 80), (114, 90, 64), (160, 132, 98))
    q.box((cx - 0.35, cy - 0.23, 0.32), (cx + 0.35, cy + 0.23, 0.85),
          (200, 160, 110), (164, 128, 86), (216, 178, 128))
    q.fp(cx - 0.35, cx + 0.35, cy + 0.231, 0.36, 0.44, (164, 128, 86))
    q.box((cx - 0.42, cy - 0.30, 0.83), (cx + 0.42, cy + 0.30, 0.92),
          (150, 115, 85), (122, 94, 68), (170, 135, 103))
    q.box((cx - 0.43, cy - 0.31, 0.915), (cx + 0.43, cy + 0.31, 0.95),
          (122, 94, 68), (122, 94, 68), (122, 94, 68))
    # Nest box bump on the +Y flank + round vent above it.
    q.box((cx - 0.20, cy + 0.225, 0.40), (cx + 0.10, cy + 0.35, 0.60),
          (190, 150, 102), (156, 120, 80), (206, 168, 120))
    q.disc_y(cx - 0.05, cy + 0.351, 0.52, 0.045, (110, 86, 62))
    # Door on the +X face with frame lines, ramp running down to grade.
    q.poly([(cx + 0.351, cy - 0.08, 0.38), (cx + 0.351, cy + 0.08, 0.38),
            (cx + 0.351, cy + 0.08, 0.70), (cx + 0.351, cy - 0.08, 0.70)],
           (110, 85, 60))
    q.line([(cx + 0.352, cy - 0.08, 0.38), (cx + 0.352, cy - 0.08, 0.70)],
           (140, 112, 80), 0.9)
    q.line([(cx + 0.352, cy + 0.08, 0.38), (cx + 0.352, cy + 0.08, 0.70)],
           (140, 112, 80), 0.9)
    q.poly([(cx + 0.36, cy - 0.09, 0.40), (cx + 0.36, cy + 0.09, 0.40),
            (cx + 0.78, cy + 0.09, -0.01), (cx + 0.78, cy - 0.09, -0.01)],
           (190, 150, 102))
    for t, zw in ((0.3, 0.30), (0.55, 0.205), (0.8, 0.10)):
        xx = cx + 0.36 + (0.78 - 0.36) * t
        q.line([(xx, cy - 0.09, zw + 0.012), (xx, cy + 0.09, zw + 0.012)],
               (140, 112, 80), 0.9)


def greenhouse(q, cx, cy, P):
    """Glass greenhouse: slab, beds, ally frame, glasshouse glazing, door."""
    q.boxg((cx - 0.50, cy - 0.32, -0.01), (cx + 0.50, cy + 0.32, 0.08),
          (202, 208, 198), (172, 184, 172), (222, 228, 218))
    # Soil beds + seedlings first (deepest), glazing later (translucent).
    for bx in (cx - 0.25, cx + 0.25):
        q.boxg((bx - 0.14, cy - 0.18, 0.06), (bx + 0.14, cy + 0.18, 0.20),
              (150, 120, 85), (120, 96, 66), (168, 138, 100))
        for px in (bx - 0.07, bx + 0.07):
            _cylinder(q, px, cy, 0.18, 0.34, 0.045,
                      (126, 176, 112), (82, 128, 82), (140, 188, 126), n=12)
            q.dot((px, cy, 0.395), 0.9, (220, 90, 80, 255))
    # Corner + mid posts (far -Y row first, near +Y row last).
    for py in (cy - 0.28, cy):
        for px in (cx - 0.46, cx + 0.46):
            q.box((px - 0.03, py - 0.03, 0.06), (px + 0.03, py + 0.03, 0.95),
                  (200, 210, 200), (168, 182, 170), (218, 228, 218))
    for px in (cx - 0.46, cx + 0.46):
        q.box((px - 0.03, cy + 0.25, 0.06), (px + 0.03, cy + 0.31, 0.95),
              (200, 210, 200), (168, 182, 170), (218, 228, 218))
    # Eaves beams along both flanks + end beams.
    for by in (cy - 0.28, cy + 0.28):
        q.box((cx - 0.49, by - 0.03, 0.90), (cx + 0.49, by + 0.03, 0.97),
              (190, 200, 190), (160, 174, 162), (208, 218, 208))
    for ex in (cx - 0.46, cx + 0.46):
        q.box((ex - 0.03, cy - 0.31, 0.90), (ex + 0.03, cy + 0.31, 0.97),
              (190, 200, 190), (160, 174, 162), (208, 218, 208))
    # Ridge beam, then translucent roof + wall glazing (inside the frame).
    q.box((cx - 0.49, cy - 0.035, 1.20), (cx + 0.49, cy + 0.035, 1.27),
          (190, 200, 190), (160, 174, 162), (208, 218, 208))
    q.poly([(cx - 0.46, cy - 0.28, 0.95), (cx + 0.46, cy - 0.28, 0.95),
            (cx + 0.46, cy, 1.22), (cx - 0.46, cy, 1.22)],
           (210, 235, 230, 80))
    q.poly([(cx - 0.46, cy + 0.28, 0.95), (cx + 0.46, cy + 0.28, 0.95),
            (cx + 0.46, cy, 1.22), (cx - 0.46, cy, 1.22)],
           (210, 235, 230, 80))
    q.poly([(cx - 0.46, cy - 0.28, 0.10), (cx + 0.46, cy - 0.28, 0.10),
            (cx + 0.46, cy - 0.28, 0.92), (cx - 0.46, cy - 0.28, 0.92)],
           (205, 230, 228, 70))
    q.poly([(cx - 0.46, cy + 0.28, 0.10), (cx + 0.46, cy + 0.28, 0.10),
            (cx + 0.46, cy + 0.28, 0.92), (cx - 0.46, cy + 0.28, 0.92)],
           (205, 230, 228, 70))
    q.poly([(cx + 0.46, cy - 0.28, 0.10), (cx + 0.46, cy + 0.28, 0.10),
            (cx + 0.46, cy + 0.28, 0.92), (cx + 0.46, cy - 0.28, 0.92)],
           (205, 230, 228, 70))
    q.poly([(cx - 0.46, cy - 0.28, 0.10), (cx - 0.46, cy + 0.28, 0.10),
            (cx - 0.46, cy + 0.28, 0.92), (cx - 0.46, cy - 0.28, 0.92)],
           (200, 225, 223, 70))
    # Door frame proud of the +X end + translucent door leaf.
    q.box((cx + 0.455, cy - 0.11, 0.075), (cx + 0.495, cy + 0.11, 0.80),
          (170, 185, 172), (145, 160, 148), (190, 203, 192))
    q.poly([(cx + 0.496, cy - 0.08, 0.12), (cx + 0.496, cy + 0.08, 0.12),
            (cx + 0.496, cy + 0.08, 0.76), (cx + 0.496, cy - 0.08, 0.76)],
           (190, 220, 215, 110))
    q.dot((cx + 0.497, cy + 0.05, 0.45), 0.7, (90, 105, 95, 255))


def beehive(q, cx, cy, P):
    """Stacked beehive boxes: pallet, three supers, roof, entrance."""
    q.box((cx - 0.32, cy - 0.26, -0.01), (cx + 0.32, cy + 0.26, 0.12),
          (150, 122, 88), (122, 98, 70), (170, 142, 106))
    q.box((cx - 0.28, cy - 0.22, 0.10), (cx + 0.28, cy + 0.22, 0.38),
          (240, 235, 220), (206, 200, 184), (248, 244, 232))
    q.box((cx - 0.28, cy - 0.22, 0.36), (cx + 0.28, cy + 0.22, 0.64),
          (180, 215, 170), (148, 182, 140), (196, 228, 186))
    q.box((cx - 0.28, cy - 0.22, 0.62), (cx + 0.28, cy + 0.22, 0.90),
          (240, 235, 220), (206, 200, 184), (248, 244, 232))
    # Handhold grooves as embossed lines on the +Y faces.
    for z in (0.24, 0.50, 0.76):
        q.line([(cx - 0.14, cy + 0.221, z), (cx + 0.14, cy + 0.221, z)],
               (170, 164, 148), 0.9)
    # Roof cap overlapping the top super.
    q.box((cx - 0.32, cy - 0.26, 0.88), (cx + 0.32, cy + 0.26, 0.98),
          (170, 185, 180), (142, 158, 152), (190, 203, 198))
    q.box((cx - 0.33, cy - 0.27, 0.975), (cx + 0.33, cy + 0.27, 1.01),
          (142, 158, 152), (142, 158, 152), (142, 158, 152))
    # Entrance slot + landing board on the +Y face.
    q.box((cx - 0.12, cy + 0.215, 0.13), (cx + 0.12, cy + 0.26, 0.20),
          (80, 70, 60), (64, 56, 48), (96, 86, 74))
    q.box((cx - 0.14, cy + 0.22, 0.10), (cx + 0.14, cy + 0.34, 0.14),
          (190, 160, 118), (160, 132, 96), (206, 178, 136))
    for bx in (cx - 0.08, cx + 0.02, cx + 0.10):
        q.dot((bx, cy + 0.30, 0.145), 0.55, (60, 52, 44, 255))


def orchard_tree(q, cx, cy, P):
    """Small orchard tree: flared trunk, lumpy triple canopy, bold fruits."""
    _cylinder(q, cx, cy, -0.01, 0.16, 0.15,
              (132, 102, 70), (96, 74, 60), (132, 102, 70), n=20)
    _cylinder(q, cx, cy, 0.12, 0.62, 0.095,
              (140, 108, 74), (100, 76, 60), (150, 118, 82), n=16)
    # Three overlapping canopy blobs: wide low crown, side puff, top dome.
    _cylinder(q, cx, cy, 0.55, 1.00, 0.40,
              (126, 176, 112), (82, 128, 82), (140, 188, 126), n=40)
    _cylinder(q, cx + 0.28, cy + 0.10, 0.62, 0.95, 0.26,
              (132, 182, 118), (86, 132, 86), (146, 194, 132), n=28)
    _cylinder(q, cx - 0.05, cy - 0.05, 0.93, 1.22, 0.27,
              (120, 170, 108), (78, 122, 78), (134, 182, 120), n=28)
    # Round fruits seated proud on the visible canopy surface.
    fruits = [(cx, cy, 0.404, 0.90, 0.70), (cx, cy, 0.404, 1.10, 0.78),
              (cx, cy, 0.404, 1.28, 0.66), (cx, cy, 0.404, 1.00, 0.90),
              (cx, cy, 0.404, 1.20, 0.88),
              (cx + 0.28, cy + 0.10, 0.264, 0.95, 0.74),
              (cx + 0.28, cy + 0.10, 0.264, 1.20, 0.82),
              (cx - 0.05, cy - 0.05, 0.274, 1.05, 1.02),
              (cx - 0.05, cy - 0.05, 0.274, 1.30, 1.10),
              (cx - 0.05, cy - 0.05, 0.274, 0.85, 1.12)]
    for fx, fy, fr, th, fz in fruits:
        q.dot(_on_cylinder(fx, fy, fr, th, fz), 1.6, (232, 132, 70, 255))
        q.dot(_on_cylinder(fx, fy, fr + 0.001, th + 0.03, fz + 0.012), 0.5,
              (250, 200, 140, 255))
    q.dot((cx + 0.32, cy + 0.28, 0.005), 0.9, (232, 132, 70, 255))
    q.dot((cx - 0.36, cy + 0.20, 0.005), 0.9, (222, 122, 65, 255))


def windmill(q, cx, cy, P):
    """Farm windmill: four-leg tower, braces, nacelle, four-blade rotor."""
    for lx in (cx - 0.22, cx + 0.22):
        for ly in (cy - 0.16, cy + 0.16):
            q.box((lx - 0.03, ly - 0.03, -0.01),
                  (lx + 0.03, ly + 0.03, 1.30),
                  (150, 160, 150), (120, 132, 122), (172, 182, 172))
    # Solid brace bars socketed through the legs on the visible faces.
    for z0 in (0.50, 0.95):
        q.box((cx - 0.25, cy + 0.13, z0), (cx + 0.25, cy + 0.19, z0 + 0.06),
              (120, 132, 122), (96, 108, 98), (140, 152, 142))
        q.box((cx + 0.19, cy - 0.19, z0), (cx + 0.25, cy + 0.19, z0 + 0.06),
              (120, 132, 122), (96, 108, 98), (140, 152, 142))
    q.box((cx - 0.14, cy - 0.12, 1.26), (cx + 0.14, cy + 0.12, 1.36),
          (170, 180, 170), (140, 152, 142), (190, 200, 190))
    q.box((cx - 0.10, cy - 0.08, 1.34), (cx + 0.30, cy + 0.08, 1.52),
          (200, 105, 85), (160, 80, 64), (216, 125, 103))
    # Hub stub starts inside the nacelle; blades sit proud of the stub.
    q.box((cx + 0.28, cy - 0.04, 1.40), (cx + 0.38, cy + 0.04, 1.48),
          (120, 130, 122), (96, 106, 98), (140, 150, 142))
    bx = cx + 0.385
    hub = 1.44
    q.poly([(bx, cy - 0.05, hub + 0.01), (bx, cy + 0.05, hub + 0.01),
            (bx, cy + 0.05, hub + 0.43), (bx, cy - 0.05, hub + 0.43)],
           (212, 216, 212))
    q.poly([(bx, cy - 0.05, hub - 0.01), (bx, cy + 0.05, hub - 0.01),
            (bx, cy + 0.05, hub - 0.43), (bx, cy - 0.05, hub - 0.43)],
           (196, 202, 196))
    q.poly([(bx, cy + 0.01, hub - 0.05), (bx, cy + 0.01, hub + 0.05),
            (bx, cy + 0.43, hub + 0.05), (bx, cy + 0.43, hub - 0.05)],
           (212, 216, 212))
    q.poly([(bx, cy - 0.01, hub - 0.05), (bx, cy - 0.01, hub + 0.05),
            (bx, cy - 0.43, hub + 0.05), (bx, cy - 0.43, hub - 0.05)],
           (196, 202, 196))
    q.dot((bx + 0.001, cy, hub), 1.2, (110, 120, 112, 255))
    # Tail vane: boom rooted in the nacelle, fin in the boom plane.
    q.box((cx - 0.34, cy - 0.02, 1.44), (cx - 0.06, cy + 0.02, 1.48),
          (120, 132, 122), (96, 108, 98), (140, 152, 142))
    q.poly([(cx - 0.36, cy - 0.012, 1.36), (cx - 0.14, cy - 0.012, 1.36),
            (cx - 0.14, cy - 0.012, 1.58), (cx - 0.36, cy - 0.012, 1.58)],
           (200, 105, 85))
    q.poly([(cx - 0.36, cy + 0.012, 1.36), (cx - 0.14, cy + 0.012, 1.36),
            (cx - 0.14, cy + 0.012, 1.58), (cx - 0.36, cy + 0.012, 1.58)],
           (216, 125, 103))


def grain_auger(q, cx, cy, P):
    """Grain auger: hopper, inclined tube, collars, wheels, outlet."""
    # Wheels + axle frame first (deepest), tube over the frame top.
    for wy in (cy - 0.062, cy + 0.062):
        q.disc_y(cx - 0.05, wy, 0.19, 0.20, (70, 78, 70))
    # Visible axle bar through both wheels into the frame (was missing
    # — corpus gate 2026-11-12).
    q.box((cx - 0.09, cy - 0.085, 0.15), (cx - 0.01, cy + 0.085, 0.27),
          (96, 106, 98), (78, 88, 80), (114, 124, 116))
    q.disc_y(cx - 0.05, cy + 0.064, 0.19, 0.085, (190, 190, 180))
    q.dot((cx - 0.05, cy + 0.066, 0.19), 1.0, (90, 100, 92, 255))
    q.box((cx - 0.13, cy - 0.06, 0.25), (cx + 0.03, cy + 0.06, 0.75),
          (150, 160, 150), (120, 132, 122), (172, 182, 172))
    # Hopper bin at the low end with mounded grain.
    q.box((cx - 0.66, cy - 0.14, 0.10), (cx - 0.36, cy + 0.14, 0.40),
          (120, 155, 125), (94, 126, 100), (142, 175, 145))
    q.box((cx - 0.64, cy - 0.12, 0.36), (cx - 0.38, cy + 0.12, 0.43),
          (214, 178, 110), (178, 144, 86), (228, 194, 128))
    yf, yb = cy + 0.06, cy - 0.06
    # Inclined tube: back face, top strip, front face, end caps.
    q.poly([(cx - 0.52, yb, 0.42), (cx + 0.42, yb, 1.02),
            (cx + 0.42, yb, 1.16), (cx - 0.52, yb, 0.56)],
           (200, 150, 70))
    q.poly([(cx - 0.52, yb, 0.56), (cx + 0.42, yb, 1.16),
            (cx + 0.42, yf, 1.16), (cx - 0.52, yf, 0.56)],
           (244, 196, 110))
    q.poly([(cx - 0.52, yf, 0.42), (cx + 0.42, yf, 1.02),
            (cx + 0.42, yf, 1.16), (cx - 0.52, yf, 0.56)],
           (230, 180, 92))
    q.poly([(cx - 0.52, yb, 0.42), (cx - 0.52, yf, 0.42),
            (cx - 0.52, yf, 0.56), (cx - 0.52, yb, 0.56)],
           (170, 128, 60))
    q.poly([(cx + 0.42, yb, 1.02), (cx + 0.42, yf, 1.02),
            (cx + 0.42, yf, 1.16), (cx + 0.42, yb, 1.16)],
           (170, 128, 60))
    # Collars straddling the tube + motor riding on top.
    for t in (0.33, 0.66):
        mx = cx - 0.52 + (0.94) * t
        mz0 = 0.42 + 0.60 * t - 0.015
        mz1 = 0.56 + 0.60 * t + 0.015
        q.poly([(mx - 0.035, yf + 0.002, mz0), (mx + 0.035, yf + 0.002, mz0),
                (mx + 0.035, yf + 0.002, mz1), (mx - 0.035, yf + 0.002, mz1)],
               (150, 110, 60))
    q.box((cx + 0.16, cy - 0.06, 1.00), (cx + 0.32, cy + 0.075, 1.16),
          (110, 120, 112), (88, 98, 90), (130, 140, 132))
    # Outlet spout under the high end + support leg.
    q.box((cx + 0.34, cy - 0.05, 0.70), (cx + 0.46, cy + 0.05, 1.06),
          (200, 150, 70), (170, 128, 60), (214, 166, 86))
    # Support saddle straddling the tube where it crosses the leg
    # (was an ambiguous miss — corpus gate 2026-11-12).
    q.box((cx + 0.22, cy - 0.07, 0.90), (cx + 0.34, cy + 0.07, 1.02),
          (150, 110, 60), (150, 110, 60), (150, 110, 60))
    q.box((cx + 0.24, cy - 0.04, -0.01), (cx + 0.32, cy + 0.04, 1.00),
          (130, 140, 130), (104, 114, 104), (150, 160, 150))


def scarecrow(q, cx, cy, P):
    """Scarecrow: post, crossbar, shirt torso, straw, head, hat."""
    q.box((cx - 0.04, cy - 0.04, -0.01), (cx + 0.04, cy + 0.04, 1.15),
          (140, 110, 78), (112, 88, 62), (160, 130, 96))
    q.box((cx - 0.35, cy - 0.03, 0.80), (cx + 0.35, cy + 0.03, 0.88),
          (140, 110, 78), (112, 88, 62), (160, 130, 96))
    q.box((cx - 0.16, cy - 0.10, 0.55), (cx + 0.16, cy + 0.10, 0.95),
          (130, 155, 200), (102, 126, 168), (150, 173, 214))
    # Shirt patch + buttons on the +Y face.
    q.fp(cx - 0.12, cx + 0.02, cy + 0.101, 0.60, 0.74, (200, 170, 120))
    q.dot((cx + 0.08, cy + 0.102, 0.80), 0.7, (90, 80, 60, 255))
    q.dot((cx + 0.08, cy + 0.102, 0.70), 0.7, (90, 80, 60, 255))
    # Straw tufts where the arms leave the sleeves.
    for sx in (cx - 0.36, cx + 0.30):
        q.box((sx, cy - 0.035, 0.795), (sx + 0.06, cy + 0.035, 0.885),
              (220, 185, 120), (184, 152, 94), (232, 200, 138))
    # Head seated into the torso top, brim + crown after the head.
    _cylinder(q, cx, cy + 0.01, 0.93, 1.15, 0.11,
              (226, 196, 158), (188, 160, 126), (236, 208, 172), n=20)
    q.dot((cx - 0.04, cy + 0.115, 1.06), 0.7, (50, 44, 38, 255))
    q.dot((cx + 0.04, cy + 0.115, 1.06), 0.7, (50, 44, 38, 255))
    q.poly([(cx - 0.10, cy + 0.08, 1.00), (cx - 0.05, cy + 0.115, 1.00),
            (cx - 0.06, cy + 0.115, 0.94), (cx - 0.11, cy + 0.08, 0.94)],
           (220, 185, 120))
    q.poly([(cx + 0.10, cy + 0.08, 1.00), (cx + 0.05, cy + 0.115, 1.00),
            (cx + 0.06, cy + 0.115, 0.94), (cx + 0.11, cy + 0.08, 0.94)],
           (220, 185, 120))
    q.ground_ellipse(cx, cy + 0.01, 0.17, 0.17, (150, 118, 80), z=1.12)
    _cylinder(q, cx, cy + 0.01, 1.10, 1.30, 0.10,
              (150, 118, 80), (118, 92, 62), (168, 136, 96), n=20)
    q.ground_ellipse(cx, cy + 0.01, 0.10, 0.10, (168, 136, 96), z=1.356)


def polytunnel(q, cx, cy, P):
    """Polytunnel: rails, soil bed, seedlings, hoops, film, end door."""
    for ry in (cy - 0.33, cy + 0.33):
        q.box((cx - 0.65, ry - 0.03, -0.01), (cx + 0.65, ry + 0.03, 0.10),
              (150, 160, 150), (120, 132, 122), (172, 182, 172))
    q.box((cx - 0.55, cy - 0.22, -0.005), (cx + 0.55, cy + 0.22, 0.14),
          (150, 120, 85), (120, 96, 66), (168, 138, 100))
    for px in (cx - 0.35, cx - 0.12, cx + 0.12, cx + 0.35):
        for py in (cy - 0.10, cy + 0.10):
            _cylinder(q, px, py, 0.12, 0.26, 0.035,
                      (126, 176, 112), (82, 128, 82), (140, 188, 126), n=10)
    # Five hoops arcing over the bed, ends buried in the rails.
    for hx in (cx - 0.55, cx - 0.275, cx, cx + 0.275, cx + 0.55):
        pts = [(hx, cy + 0.36 * math.cos(a), 0.08 + 0.64 * math.sin(a))
               for a in [i * math.pi / 12 for i in range(13)]]
        q.line(pts, (190, 200, 190), 1.2)
    # End-wall frames: far -X simple posts, near +X with a door opening.
    for ex, door in ((cx - 0.55, False), (cx + 0.55, True)):
        q.box((ex - 0.025, cy - 0.335, 0.06), (ex + 0.025, cy + 0.335, 0.16),
              (170, 180, 170), (142, 154, 144), (190, 200, 190))
        for py in (cy - 0.30, cy + 0.30):
            q.box((ex - 0.025, py - 0.025, 0.08), (ex + 0.025, py + 0.025, 0.62),
                  (170, 180, 170), (142, 154, 144), (190, 200, 190))
        if door:
            q.box((ex - 0.02, cy - 0.10, 0.08), (ex + 0.02, cy + 0.10, 0.55),
                  (170, 180, 170), (142, 154, 144), (190, 200, 190))
    # Translucent film: two slopes + crest + far end wall + door leaf.
    q.poly([(cx - 0.58, cy - 0.33, 0.10), (cx + 0.58, cy - 0.33, 0.10),
            (cx + 0.58, cy - 0.10, 0.66), (cx - 0.58, cy - 0.10, 0.66)],
           (215, 230, 215, 70))
    q.poly([(cx - 0.58, cy + 0.33, 0.10), (cx + 0.58, cy + 0.33, 0.10),
            (cx + 0.58, cy + 0.10, 0.66), (cx - 0.58, cy + 0.10, 0.66)],
           (215, 230, 215, 70))
    q.poly([(cx - 0.58, cy - 0.10, 0.66), (cx + 0.58, cy - 0.10, 0.66),
            (cx + 0.58, cy + 0.10, 0.66), (cx - 0.58, cy + 0.10, 0.66)],
           (220, 235, 220, 70))
    q.poly([(cx - 0.551, cy - 0.30, 0.08), (cx - 0.551, cy + 0.30, 0.08),
            (cx - 0.551, cy + 0.30, 0.60), (cx - 0.551, cy - 0.30, 0.60)],
           (210, 228, 212, 70))
    q.poly([(cx + 0.571, cy - 0.08, 0.10), (cx + 0.571, cy + 0.08, 0.10),
            (cx + 0.571, cy + 0.08, 0.53), (cx + 0.571, cy - 0.08, 0.53)],
           (190, 220, 205, 110))


def dog_house(q, cx, cy, P):
    """Dog house: base, walls, gable roof, dark opening, food bowl."""
    q.box((cx - 0.35, cy - 0.28, -0.01), (cx + 0.35, cy + 0.28, 0.08),
          (150, 122, 88), (122, 98, 70), (170, 142, 106))
    q.box((cx - 0.30, cy - 0.23, 0.06), (cx + 0.30, cy + 0.23, 0.55),
          (200, 100, 85), (164, 80, 66), (216, 120, 103))
    # Gable triangles on both ends.
    q.poly([(cx - 0.30, cy - 0.23, 0.55), (cx - 0.30, cy + 0.23, 0.55),
            (cx - 0.30, cy, 0.78)], (200, 100, 85))
    q.poly([(cx + 0.30, cy - 0.23, 0.55), (cx + 0.30, cy + 0.23, 0.55),
            (cx + 0.30, cy, 0.78)], (200, 100, 85))
    # Roof quads from eaves (sunk into the walls) to the ridge.
    q.poly([(cx - 0.37, cy - 0.30, 0.50), (cx + 0.37, cy - 0.30, 0.50),
            (cx + 0.37, cy, 0.80), (cx - 0.37, cy, 0.80)],
           (150, 115, 85))
    q.poly([(cx - 0.37, cy + 0.30, 0.50), (cx + 0.37, cy + 0.30, 0.50),
            (cx + 0.37, cy, 0.80), (cx - 0.37, cy, 0.80)],
           (170, 133, 99))
    q.line([(cx - 0.37, cy, 0.80), (cx + 0.37, cy, 0.80)], (120, 92, 68), 1.0)
    # Dark opening proud of the +X face + frame lines.
    q.box((cx + 0.295, cy - 0.10, 0.075), (cx + 0.36, cy + 0.10, 0.40),
          (70, 80, 72), (60, 70, 62), (84, 94, 86))
    q.line([(cx + 0.361, cy - 0.10, 0.40), (cx + 0.361, cy + 0.10, 0.40)],
           (150, 115, 85), 0.9)
    q.line([(cx + 0.361, cy - 0.10, 0.08), (cx + 0.361, cy - 0.10, 0.40)],
           (150, 115, 85), 0.9)
    q.line([(cx + 0.361, cy + 0.10, 0.08), (cx + 0.361, cy + 0.10, 0.40)],
           (150, 115, 85), 0.9)
    # Bone emblem (two dots + bar) above the opening, food bowl aside.
    q.dot((cx + 0.361, cy - 0.035, 0.47), 0.7, (235, 230, 215, 255))
    q.dot((cx + 0.361, cy + 0.035, 0.47), 0.7, (235, 230, 215, 255))
    _cylinder(q, cx + 0.48, cy + 0.32, 0.0, 0.10, 0.09,
              (150, 170, 175), (120, 142, 147), (172, 192, 197), n=16)
    q.ground_ellipse(cx + 0.48, cy + 0.32, 0.06, 0.06,
                     (150, 118, 80), z=0.105)


def pond(q, cx, cy, P):
    """Small pond: water blob, lily pads, rim stones, reeds."""
    q.ground_ellipse(cx, cy, 0.55, 0.38, (140, 190, 205), z=0.0)
    q.ground_ellipse(cx, cy, 0.36, 0.25, (160, 205, 215), z=0.006)
    q.poly([(cx - 0.20, cy + 0.05, 0.007), (cx + 0.05, cy + 0.05, 0.007),
            (cx + 0.10, cy + 0.12, 0.007), (cx - 0.15, cy + 0.12, 0.007)],
           (255, 255, 255, 60))
    # Lily pads + one flower.
    q.ground_ellipse(cx - 0.12, cy + 0.02, 0.075, 0.075,
                     (110, 170, 120), z=0.012)
    q.ground_ellipse(cx + 0.18, cy - 0.08, 0.06, 0.06,
                     (116, 176, 126), z=0.012)
    q.dot((cx - 0.12, cy + 0.02, 0.02), 0.8, (240, 170, 200, 255))
    # Rim stones (painted after the water), reeds rooted at the rim.
    stones = [(cx - 0.52, cy + 0.10), (cx - 0.30, cy + 0.30),
              (cx + 0.05, cy + 0.36), (cx + 0.40, cy + 0.24),
              (cx + 0.55, cy - 0.05), (cx - 0.55, cy - 0.18)]
    for sx, sy in stones:
        q.box((sx - 0.05, sy - 0.05, -0.01), (sx + 0.05, sy + 0.05, 0.08),
              (170, 178, 170), (142, 152, 144), (190, 198, 190))
    for rx, ry, h in ((cx - 0.40, cy - 0.28, 0.55),
                      (cx + 0.30, cy + 0.30, 0.62),
                      (cx + 0.48, cy + 0.10, 0.48)):
        q.box((rx - 0.02, ry - 0.02, -0.01), (rx + 0.02, ry + 0.02, h),
              (110, 160, 110), (86, 130, 88), (130, 178, 130))
        _cylinder(q, rx, ry, h - 0.005, h + 0.10, 0.025,
                  (150, 110, 75), (120, 88, 60), (168, 130, 92), n=8)


PROPS = {
    "tractor": {"fn": tractor, "focus": (0.0, 0.15, 0.70), "k": 430,
                "plinth": (0.0, 0.15, 0.70, 0.42),
                "brief": "small farm tractor with cab, wheels and exhaust"},
    "cow": {"fn": cow, "focus": (0.0, 0.15, 0.45), "k": 520,
            "plinth": (0.0, 0.15, 0.72, 0.42),
            "brief": "standing dairy cow, body head legs udder"},
    "hay-bale": {"fn": hay_bale, "focus": (0.0, 0.15, 0.30), "k": 520,
                 "plinth": (0.0, 0.15, 0.60, 0.38),
                 "brief": "round hay bale with wrap lines"},
    "silo": {"fn": silo, "focus": (0.0, 0.15, 0.90), "k": 320,
             "plinth": (0.0, 0.15, 0.60, 0.38),
             "brief": "farm silo tower with cone roof and ladder"},
    "water-trough": {"fn": water_trough, "focus": (0.0, 0.15, 0.35), "k": 520,
                     "plinth": (0.0, 0.15, 0.72, 0.42),
                     "brief": "cattle water trough on legs"},
    "chicken-coop": {"fn": chicken_coop, "focus": (0.0, 0.15, 0.45), "k": 370,
                     "plinth": (0.0, 0.15, 0.72, 0.44),
                     "brief": "small chicken coop with ramp and roof"},
    "greenhouse": {"fn": greenhouse, "focus": (0.0, 0.15, 0.60), "k": 350,
                   "plinth": (0.0, 0.15, 0.72, 0.44),
                   "brief": "glass greenhouse with frame and door"},
    "beehive": {"fn": beehive, "focus": (0.0, 0.15, 0.50), "k": 400,
                "plinth": (0.0, 0.15, 0.55, 0.36),
                "brief": "stacked beehive boxes with roof and entrance"},
    "orchard-tree": {"fn": orchard_tree, "focus": (0.0, 0.15, 0.58), "k": 360,
                     "plinth": (0.0, 0.15, 0.62, 0.40),
                     "brief": "small orchard tree with round fruits"},
    "windmill": {"fn": windmill, "focus": (0.0, 0.15, 0.90), "k": 380,
                 "plinth": (0.0, 0.15, 0.62, 0.40),
                 "brief": "farm windmill tower with rotor"},
    "grain-auger": {"fn": grain_auger, "focus": (0.0, 0.15, 0.55), "k": 460,
                    "plinth": (0.0, 0.15, 0.80, 0.44),
                    "brief": "grain auger tube on wheels with hopper"},
    "scarecrow": {"fn": scarecrow, "focus": (0.0, 0.15, 0.68), "k": 440,
                  "plinth": (0.0, 0.15, 0.55, 0.36),
                  "brief": "scarecrow with hat on post"},
    "polytunnel": {"fn": polytunnel, "focus": (0.0, 0.15, 0.38), "k": 440,
                   "plinth": (0.0, 0.15, 0.85, 0.50),
                   "brief": "polytunnel arc greenhouse with door"},
    "dog-house": {"fn": dog_house, "focus": (0.0, 0.15, 0.40), "k": 520,
                  "plinth": (0.0, 0.15, 0.68, 0.42),
                  "brief": "dog house with roof and opening"},
    "pond": {"fn": pond, "focus": (0.0, 0.15, 0.30), "k": 420,
             "plinth": (0.0, 0.15, 0.75, 0.50),
             "brief": "small pond disc with reeds and stones"},
}
