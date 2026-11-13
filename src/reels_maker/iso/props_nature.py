"""Nature / outdoor props for the ASTA gallery (batch props_nature).

Builders take ``(q, cx, cy, P)`` with all coordinates relative to the
placement center. Mid-tone flat palette (no channel below RGB 60 except
tiny dots), overlapped (never exact-touch) joints, NO contact shadows,
no text decals (embossed lines only).
"""
from __future__ import annotations

from .world import _cylinder, _on_cylinder


def tree(q, cx, cy, P):
    """Leafy tree: trunk with root flare and two canopy blobs."""
    _cylinder(q, cx, cy, -0.01, 0.12, 0.14,
              (132, 102, 70), (96, 74, 60), (132, 102, 70), n=20)
    _cylinder(q, cx, cy, 0.10, 0.88, 0.10,
              (140, 108, 74), (100, 76, 60), (150, 118, 82), n=20)
    lx, ly = cx - 0.03, cy + 0.02
    _cylinder(q, lx, ly, 0.80, 1.16, 0.45,
              (126, 176, 112), (82, 128, 82), (140, 188, 126), n=44)
    for g0, g1, alpha in ((0.98, 1.06, 60), (1.06, 1.10, 30)):
        q.poly([_on_cylinder(lx, ly, 0.454, g0, 0.90),
                _on_cylinder(lx, ly, 0.454, g1, 0.90),
                _on_cylinder(lx, ly, 0.454, g1, 1.10),
                _on_cylinder(lx, ly, 0.454, g0, 1.10)],
               (255, 255, 255, alpha))
    ux, uy = cx + 0.10, cy - 0.06
    _cylinder(q, ux, uy, 1.11, 1.40, 0.30,
              (132, 182, 118), (86, 132, 86), (146, 194, 132), n=32)
    q.poly([_on_cylinder(ux, uy, 0.304, 0.98, 1.18),
            _on_cylinder(ux, uy, 0.304, 1.06, 1.18),
            _on_cylinder(ux, uy, 0.304, 1.06, 1.34),
            _on_cylinder(ux, uy, 0.304, 0.98, 1.34)],
           (255, 255, 255, 55))


def conifer(q, cx, cy, P):
    """Conifer: short trunk with three stacked green tiers and a tip."""
    _cylinder(q, cx, cy, -0.01, 0.30, 0.07,
              (140, 108, 74), (100, 76, 60), (150, 118, 82), n=14)
    tiers = (
        (0.38, 0.24, 0.56, (118, 164, 104), (78, 120, 78), (132, 178, 118)),
        (0.29, 0.51, 0.80, (124, 170, 110), (82, 124, 82), (138, 184, 124)),
        (0.20, 0.75, 1.00, (130, 176, 116), (86, 128, 86), (144, 190, 130)),
    )
    for r, z0, z1, cl, cd, ct in tiers:
        _cylinder(q, cx, cy, z0, z1, r, cl, cd, ct, n=36)
        q.poly([_on_cylinder(cx, cy, r + 0.004, 0.98, z0 + 0.06),
                _on_cylinder(cx, cy, r + 0.004, 1.06, z0 + 0.06),
                _on_cylinder(cx, cy, r + 0.004, 1.06, z1 - 0.05),
                _on_cylinder(cx, cy, r + 0.004, 0.98, z1 - 0.05)],
               (255, 255, 255, 50))
    _cylinder(q, cx, cy, 0.95, 1.10, 0.06,
              (130, 176, 116), (86, 128, 86), (144, 190, 130), n=10)


def fence(q, cx, cy, P):
    """Fence bay: two posts with caps joined by two rails."""
    for px in (cx - 0.55, cx + 0.55):
        q.box((px - 0.05, cy - 0.05, -0.01), (px + 0.05, cy + 0.05, 0.60),
              (158, 124, 88), (128, 100, 70), (178, 146, 108))
        q.box((px - 0.065, cy - 0.065, 0.595),
              (px + 0.065, cy + 0.065, 0.65),
              (140, 108, 76), (114, 88, 62), (162, 130, 96))
    for z0, z1 in ((0.16, 0.24), (0.40, 0.48)):
        q.box((cx - 0.63, cy + 0.02, z0), (cx + 0.63, cy + 0.055, z1),
              (158, 124, 88), (128, 100, 70), (170, 138, 100))
        q.line([(cx - 0.60, cy + 0.056, z0 + 0.03),
                (cx + 0.60, cy + 0.056, z0 + 0.03)], (120, 94, 66), 0.7)
    for px in (cx - 0.55, cx + 0.55):
        for z in (0.20, 0.44):
            q.dot((px, cy + 0.056, z), 1.0, (96, 74, 52, 255))


def gate(q, cx, cy, P):
    """Double driveway gate: two posts with ball finials, two framed leaves."""
    for px in (cx - 0.68, cx + 0.68):
        q.box((px - 0.07, cy - 0.07, -0.01), (px + 0.07, cy + 0.07, 0.88),
              (96, 134, 106), (76, 110, 88), (116, 154, 126))
        q.box((px - 0.09, cy - 0.09, 0.875), (px + 0.09, cy + 0.09, 0.94),
              (86, 122, 96), (68, 100, 80), (106, 142, 116))
        _cylinder(q, px, cy, 0.935, 1.00, 0.045,
                  (96, 134, 106), (76, 110, 88), (116, 154, 126), n=12)
    for sgn in (-1, 1):
        x_post = cx + sgn * 0.61
        x_mid = cx + sgn * 0.03
        x0, x1 = (x_post, x_mid) if sgn < 0 else (x_mid, x_post)
        q.box((x0, cy - 0.03, 0.12), (x1, cy + 0.03, 0.20),
              (96, 134, 106), (76, 110, 88), (96, 134, 106))
        q.box((x0, cy - 0.03, 0.70), (x1, cy + 0.03, 0.78),
              (96, 134, 106), (76, 110, 88), (96, 134, 106))
        for bx in (x0 + 0.015, (x0 + x1) / 2, x1 - 0.015):
            q.box((bx - 0.022, cy - 0.025, 0.195),
                  (bx + 0.022, cy + 0.025, 0.705),
                  (104, 142, 114), (82, 116, 92), (104, 142, 114))
        for bz in (0.30, 0.40, 0.50, 0.60):
            q.line([(x0 + 0.01, cy + 0.031, bz),
                    (x1 - 0.01, cy + 0.031, bz)], (70, 104, 82), 0.7)
    for px in (cx - 0.68, cx + 0.68):
        for hz in (0.30, 0.62):
            q.dot((px + (0.071 if px < cx else -0.071), cy, hz),
                  1.1, (150, 130, 80, 255))


def garden_lamp(q, cx, cy, P):
    """Solar garden bollard: plate, post, glowing head, cap, panel."""
    q.box((cx - 0.10, cy - 0.10, -0.01), (cx + 0.10, cy + 0.10, 0.05),
          (110, 120, 110), (86, 96, 88), (132, 142, 132))
    _cylinder(q, cx, cy, 0.04, 0.55, 0.055,
              (96, 110, 100), (72, 88, 78), (118, 132, 122), n=14)
    _cylinder(q, cx, cy, 0.50, 0.58, 0.075,
              (72, 88, 78), (60, 74, 66), (96, 110, 100), n=14)
    q.box((cx - 0.09, cy - 0.09, 0.575), (cx + 0.09, cy + 0.09, 0.75),
          (88, 102, 92), (68, 84, 74), (110, 124, 114))
    q.fp(cx - 0.06, cx + 0.06, cy + 0.092, 0.615, 0.71, (190, 225, 195))
    q.fp(cx - 0.06, cx + 0.06, cy + 0.093, 0.655, 0.668, (110, 160, 130))
    q.poly([(cx - 0.05, cy + 0.093, 0.625), (cx - 0.02, cy + 0.093, 0.625),
            (cx - 0.045, cy + 0.093, 0.70), (cx - 0.075, cy + 0.093, 0.70)],
           (255, 255, 255, 90))
    q.fp(cx + 0.092, cx + 0.093, cy - 0.06, 0.615, 0.71, (190, 225, 195))
    q.box((cx - 0.105, cy - 0.105, 0.745), (cx + 0.105, cy + 0.105, 0.79),
          (72, 88, 78), (60, 74, 66), (96, 110, 100))
    q.box((cx - 0.07, cy - 0.07, 0.785), (cx + 0.07, cy + 0.07, 0.815),
          (70, 95, 120), (62, 82, 104), (86, 112, 138))
    q.line([(cx - 0.07, cy, 0.816), (cx + 0.07, cy, 0.816)],
           (150, 170, 190), 0.7)
    q.line([(cx, cy - 0.07, 0.816), (cx, cy + 0.07, 0.816)],
           (150, 170, 190), 0.7)


def borehole(q, cx, cy, P):
    """Ground-source borehole: soil cutaway with U-loop, slab cap, wellhead."""
    q.box((cx - 0.45, cy - 0.30, -0.01), (cx + 0.45, cy + 0.30, 0.55),
          (134, 106, 76), (110, 86, 62), (150, 124, 92))
    q.fp(cx - 0.45, cx + 0.45, cy + 0.303, 0.38, 0.55, (110, 86, 62))
    q.fp(cx - 0.45, cx + 0.45, cy + 0.303, 0.20, 0.24, (160, 140, 110))
    q.fp(cx - 0.45, cx + 0.45, cy + 0.303, 0.02, 0.06, (120, 100, 76))
    q.line([(cx - 0.45, cy + 0.303, 0.375), (cx + 0.45, cy + 0.303, 0.375)],
           (92, 72, 52), 0.8)
    for px in (cx - 0.12, cx + 0.12):
        q.box((px - 0.035, cy + 0.065, 0.05),
              (px + 0.035, cy + 0.135, 0.63),
              (90, 140, 150), (70, 115, 125), (110, 160, 170))
    q.box((cx - 0.155, cy + 0.065, 0.05), (cx + 0.155, cy + 0.135, 0.12),
          (70, 115, 125), (70, 115, 125), (70, 115, 125))
    for px in (cx - 0.12, cx + 0.12):
        q.box((px - 0.042, cy + 0.058, 0.30), (px + 0.042, cy + 0.142, 0.35),
              (70, 115, 125), (70, 115, 125), (70, 115, 125))
    q.box((cx - 0.45, cy - 0.30, 0.545), (cx + 0.45, cy + 0.30, 0.575),
          (126, 170, 108), (100, 142, 88), (142, 186, 124))
    q.box((cx - 0.30, cy - 0.20, 0.57), (cx + 0.30, cy + 0.20, 0.65),
          (202, 208, 198), (172, 184, 172), (222, 228, 218))
    _cylinder(q, cx, cy, 0.645, 0.80, 0.09,
              (96, 110, 100), (72, 88, 78), (118, 132, 122), n=16)
    q.box((cx - 0.05, cy + 0.085, 0.68), (cx + 0.05, cy + 0.135, 0.76),
          (150, 130, 80), (110, 92, 58), (170, 150, 100))
    q.dot((cx, cy + 0.136, 0.72), 1.2, (220, 150, 60, 255))


def pad(q, cx, cy, P):
    """Concrete pad with mounting rails and anchor bolts."""
    q.box((cx - 0.45, cy - 0.35, -0.01), (cx + 0.45, cy + 0.35, 0.12),
          (202, 208, 198), (172, 184, 172), (222, 228, 218))
    q.line([(cx - 0.41, cy - 0.31, 0.121), (cx + 0.41, cy - 0.31, 0.121)],
           (150, 162, 150), 0.8)
    q.line([(cx - 0.41, cy + 0.31, 0.121), (cx + 0.41, cy + 0.31, 0.121)],
           (150, 162, 150), 0.8)
    for ry in (cy - 0.18, cy + 0.18):
        q.box((cx - 0.32, ry - 0.05, 0.115),
              (cx + 0.32, ry + 0.05, 0.17),
              (120, 134, 124), (96, 110, 100), (144, 158, 144))
    for bx in (cx - 0.26, cx + 0.26):
        for ry in (cy - 0.18, cy + 0.18):
            q.ground_ellipse(bx, ry, 0.045, 0.045, (96, 110, 100), z=0.171)
            _cylinder(q, bx, ry, 0.165, 0.24, 0.028,
                      (150, 130, 80), (110, 92, 58), (170, 150, 100), n=10)
            q.box((bx - 0.035, ry - 0.035, 0.235),
                  (bx + 0.035, ry + 0.035, 0.27),
                  (110, 92, 58), (92, 76, 48), (150, 130, 80))
            q.dot((bx, ry, 0.271), 1.0, (200, 210, 200, 255))


PROPS = {
    "tree": {"fn": tree, "focus": (0.0, 0.15, 0.70), "k": 325,
             "plinth": (0.0, 0.15, 0.80, 0.50),
             "brief": "leafy tree: trunk with two canopy blobs"},
    "conifer": {"fn": conifer, "focus": (0.0, 0.15, 0.55), "k": 480,
                "plinth": (0.0, 0.15, 0.65, 0.42),
                "brief": "conifer: stacked green cones on trunk"},
    "fence": {"fn": fence, "focus": (0.0, 0.15, 0.35), "k": 420,
              "plinth": (0.0, 0.15, 0.95, 0.55),
              "brief": "fence bay with post and rails"},
    "gate": {"fn": gate, "focus": (0.0, 0.15, 0.50), "k": 330,
             "plinth": (0.0, 0.15, 1.05, 0.60),
             "brief": "double driveway gate with posts"},
    "garden-lamp": {"fn": garden_lamp, "focus": (0.0, 0.15, 0.42), "k": 620,
                    "plinth": (0.0, 0.15, 0.45, 0.32),
                    "brief": "solar garden bollard lamp"},
    "borehole": {"fn": borehole, "focus": (0.0, 0.15, 0.35), "k": 500,
                 "plinth": (0.0, 0.15, 0.55, 0.36),
                 "brief": "ground-source borehole: soil cutaway with U-loop and cap"},
    "pad": {"fn": pad, "focus": (0.0, 0.15, 0.15), "k": 520,
            "plinth": (0.0, 0.15, 0.75, 0.55),
            "brief": "concrete pad with anchor bolts for an outdoor unit"},
}
