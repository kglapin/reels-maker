"""Iso gallery props: buildings batch (halls, garage, housing, farm, carport).

Builders take ``(q, cx, cy, P)`` with all coordinates relative to the
placement center. Joints overlap (>=0.005, never exact-touch), no
contact shadows, no text decals (embossed lines only), mid-tone palette
(nothing below RGB 60 except tiny dots).
"""
from __future__ import annotations

import math

# --------------------------------------------------------------------------
# 36-hala: production hall


def hall(q, cx, cy, P):
    # Foundation skirt, walls, roof slab (overlap at every joint).
    q.box((cx - 1.14, cy - 0.84, -0.02), (cx + 1.14, cy + 0.84, 0.10),
          (150, 166, 150), (128, 148, 128), (190, 200, 184))
    q.box((cx - 1.10, cy - 0.80, 0.095), (cx + 1.10, cy + 0.80, 1.05),
          (236, 241, 230), (198, 212, 194), (240, 244, 232))
    # Corner pilasters proud of the visible faces.
    for px in (cx - 1.10, cx + 1.10):
        q.box((px - 0.05, cy + 0.795, 0.095), (px + 0.05, cy + 0.865, 1.05),
              (170, 188, 170), (158, 178, 158), (190, 206, 190))
        q.box((cx + 1.095 if px > cx else px - 0.05, cy - 0.84, 0.095),
              (cx + 1.165 if px > cx else px + 0.05, cy + 0.84, 1.05),
              (170, 188, 170), (158, 178, 158), (190, 206, 190))
    # Roof slab with overhang + fascia shadow gap.
    q.box((cx - 1.18, cy - 0.88, 1.045), (cx + 1.18, cy + 0.88, 1.16),
          (150, 166, 152), (128, 146, 132), (226, 232, 222))
    q.box((cx - 1.18, cy - 0.88, 1.10), (cx + 1.18, cy + 0.88, 1.13),
          (110, 126, 114), (96, 112, 100), (150, 166, 152))
    # Skylight strips: curbs sunk into the slab, glassy tops.
    for i in (-1, 0, 1):
        sx = cx + i * 0.62
        q.box((sx - 0.22, cy - 0.55, 1.125), (sx + 0.22, cy + 0.55, 1.20),
              (150, 180, 195), (130, 160, 178), (196, 218, 230))
        q.line([(sx - 0.22, cy + 0.556, 1.17), (sx + 0.22, cy + 0.556, 1.17)],
               (240, 248, 250), 0.8)
    # Dock door (+Y): recessed panel, slats, jambs, lintel.
    yf = cy + 0.80
    q.fp(cx - 0.78, cx + 0.02, yf + 0.004, 0.10, 0.88, (118, 132, 122))
    for k in range(5):
        z = 0.10 + (0.78 / 5) * (k + 1)
        q.line([(cx - 0.78, yf + 0.006, z), (cx + 0.02, yf + 0.006, z)],
               (152, 166, 156), 0.8)
    for jx0, jx1 in ((cx - 0.86, cx - 0.78), (cx + 0.02, cx + 0.10)):
        q.box((jx0, yf - 0.005, 0.095), (jx1, yf + 0.05, 0.94),
              (170, 188, 170), (150, 170, 150), (190, 206, 190))
    q.box((cx - 0.86, yf - 0.005, 0.88), (cx + 0.10, yf + 0.05, 0.95),
          (170, 188, 170), (150, 170, 150), (190, 206, 190))
    # Plain signage band (embossed lines only, no text) above the doors.
    q.fp(cx - 1.04, cx + 1.04, yf + 0.004, 0.90, 1.02, (84, 104, 92))
    for z in (0.935, 0.975):
        q.line([(cx - 1.00, yf + 0.006, z), (cx + 1.00, yf + 0.006, z)],
               (150, 170, 155), 0.8)
    # Personnel door + window (+Y).
    q.fp(cx + 0.30, cx + 0.62, yf + 0.004, 0.10, 0.78, (96, 116, 102))
    q.fp(cx + 0.35, cx + 0.57, yf + 0.006, 0.50, 0.70, (178, 208, 216))
    q.dot((cx + 0.57, yf + 0.008, 0.42), 1.0, (200, 210, 198, 255))
    q.fp(cx + 0.74, cx + 1.02, yf + 0.004, 0.45, 0.80, (170, 205, 215))
    q.line([(cx + 0.88, yf + 0.006, 0.45), (cx + 0.88, yf + 0.006, 0.80)],
           (110, 130, 120), 0.9)
    q.line([(cx + 0.74, yf + 0.006, 0.625), (cx + 1.02, yf + 0.006, 0.625)],
           (110, 130, 120), 0.9)
    q.box((cx + 0.72, yf - 0.005, 0.40), (cx + 1.04, yf + 0.045, 0.45),
          (200, 212, 198), (180, 194, 178), (220, 230, 216))
    # Side windows + vent (+X).
    xf = cx + 1.10
    for wy in (cy - 0.45, cy + 0.05, cy + 0.55):
        q.poly([(xf + 0.004, wy - 0.14, 0.45), (xf + 0.004, wy + 0.14, 0.45),
                (xf + 0.004, wy + 0.14, 0.80), (xf + 0.004, wy - 0.14, 0.80)],
               (170, 205, 215))
        q.line([(xf + 0.006, wy, 0.45), (xf + 0.006, wy, 0.80)],
               (110, 130, 120), 0.9)
    q.poly([(xf + 0.004, cy - 0.72, 0.55), (xf + 0.004, cy - 0.48, 0.55),
            (xf + 0.004, cy - 0.48, 0.85), (xf + 0.004, cy - 0.72, 0.85)],
           (140, 156, 146))
    for k in range(4):
        z = 0.60 + k * 0.07
        q.line([(xf + 0.006, cy - 0.70, z), (xf + 0.006, cy - 0.50, z)],
               (170, 186, 172), 0.9)


# --------------------------------------------------------------------------
# 37-regal: warehouse rack with stocked boxes


def rack(q, cx, cy, P):
    UPR = ((90, 110, 140), (70, 90, 120), (110, 130, 160))
    BEAM = ((205, 130, 70), (180, 110, 60), (220, 150, 90))
    # Feet plates + 4 uprights.
    for sx in (-0.70, 0.70):
        for sy in (-0.30, 0.30):
            q.box((cx + sx - 0.07, cy + sy - 0.07, -0.02),
                  (cx + sx + 0.07, cy + sy + 0.07, 0.04),
                  (110, 120, 110), (90, 102, 92), (140, 150, 140))
            q.box((cx + sx - 0.045, cy + sy - 0.045, 0.035),
                  (cx + sx + 0.045, cy + sy + 0.045, 1.50),
                  *UPR)
    # Beams along X (front/back) and along Y (sides) at 3 levels.
    for lz in (0.42, 0.90, 1.38):
        for sy in (-0.30, 0.30):
            q.box((cx - 0.745, cy + sy - 0.035, lz),
                  (cx + 0.745, cy + sy + 0.035, lz + 0.09), *BEAM)
        for sx in (-0.70, 0.70):
            q.box((cx + sx - 0.035, cy - 0.345, lz),
                  (cx + sx + 0.035, cy + 0.345, lz + 0.09), *BEAM)
    # Shelf slabs on the two lower levels (top beams stay an open cap).
    for lz in (0.42, 0.90):
        q.box((cx - 0.70, cy - 0.30, lz + 0.085),
              (cx + 0.70, cy + 0.30, lz + 0.105),
              (150, 160, 150), (130, 142, 132), (180, 188, 178))
    # Pallets + cartons on the floor.
    for px, hw in ((cx - 0.45, 0.22), (cx + 0.30, 0.34)):
        q.box((px - hw, cy - 0.20, -0.015), (px + hw, cy + 0.20, 0.06),
              (170, 140, 100), (150, 122, 86), (188, 160, 118))
    cartons = [
        # (x0, x1, y0, y1, z0, h, front, side, top)
        (cx - 0.62, cx - 0.30, cy - 0.18, cy + 0.16, 0.055, 0.30,
         (206, 186, 150), (182, 162, 128), (220, 202, 168)),
        (cx - 0.28, cx + 0.02, cy - 0.16, cy + 0.14, 0.055, 0.22,
         (150, 176, 158), (128, 156, 136), (172, 194, 178)),
        (cx - 0.05, cx + 0.33, cy - 0.18, cy + 0.18, 0.055, 0.34,
         (168, 188, 208), (146, 166, 188), (188, 204, 220)),
        (cx + 0.38, cx + 0.64, cy - 0.14, cy + 0.12, 0.055, 0.24,
         (210, 170, 130), (188, 150, 112), (224, 188, 150)),
        (cx - 0.60, cx - 0.26, cy - 0.16, cy + 0.14, 0.52, 0.30,
         (188, 204, 220), (166, 184, 200), (204, 216, 228)),
        (cx - 0.20, cx + 0.14, cy - 0.18, cy + 0.16, 0.52, 0.36,
         (206, 186, 150), (182, 162, 128), (220, 202, 168)),
        (cx + 0.20, cx + 0.52, cy - 0.14, cy + 0.16, 0.52, 0.28,
         (160, 184, 164), (138, 162, 142), (180, 200, 182)),
        (cx - 0.45, cx - 0.05, cy - 0.28, cy - 0.02, 1.00, 0.30,
         (210, 170, 130), (188, 150, 112), (224, 188, 150)),
        (cx + 0.05, cx + 0.45, cy - 0.10, cy + 0.22, 1.00, 0.32,
         (150, 176, 158), (128, 156, 136), (172, 194, 178)),
    ]
    for (x0, x1, y0, y1, z0, h, cf, cs, ct) in cartons:
        q.box((x0, y0, z0 - 0.005), (x1, y1, z0 + h), cf, cs, ct)
        # Tape band across the lid + small embossed label plate.
        q.line([(x0 + 0.02, (y0 + y1) / 2, z0 + h + 0.001),
                (x1 - 0.02, (y0 + y1) / 2, z0 + h + 0.001)],
               (235, 232, 220), 0.8)
        q.fp(x0 + 0.05, x0 + 0.17, y1 + 0.002, z0 + 0.06, z0 + 0.14,
             (232, 230, 218))


# --------------------------------------------------------------------------
# 38-garaz: detached garage with sectional door


def garage(q, cx, cy, P):
    q.box((cx - 0.84, cy - 0.64, -0.02), (cx + 0.84, cy + 0.64, 0.10),
          (150, 166, 150), (128, 148, 128), (190, 200, 184))
    q.box((cx - 0.80, cy - 0.60, 0.095), (cx + 0.80, cy + 0.60, 0.95),
          (234, 238, 226), (196, 210, 190), (240, 244, 230))
    # Gable roof, ridge along X: two slopes + gable triangles + ridge cap.
    q.poly([(cx - 0.80, cy - 0.60, 0.945), (cx + 0.80, cy - 0.60, 0.945),
            (cx + 0.80, cy, 1.345), (cx - 0.80, cy, 1.345)], (150, 146, 140))
    q.poly([(cx - 0.88, cy + 0.68, 0.945), (cx + 0.88, cy + 0.68, 0.945),
            (cx + 0.88, cy, 1.385), (cx - 0.88, cy, 1.385)], (168, 164, 156))
    q.poly([(cx - 0.88, cy - 0.68, 0.945), (cx + 0.88, cy - 0.68, 0.945),
            (cx + 0.88, cy, 1.385), (cx - 0.88, cy, 1.385)], (140, 136, 130))
    for gx in (cx - 0.80, cx + 0.80):
        s = 1.0 if gx > cx else -1.0
        q.poly([(gx, cy - 0.60, 0.945), (gx, cy + 0.60, 0.945),
                (gx, cy, 1.345)], (234, 238, 226) if s > 0 else (210, 222, 204))
    q.box((cx - 0.89, cy - 0.06, 1.375), (cx + 0.89, cy + 0.06, 1.45),
          (120, 116, 110), (104, 100, 96), (150, 146, 140))
    for i in range(7):
        rx = cx - 0.80 + i * (1.60 / 6)
        q.line([(rx, cy + 0.681, 0.95), (rx, cy, 1.38)], (150, 146, 140), 0.7)
    # Sectional door (+Y): 4 slats, jambs, lintel.
    yf = cy + 0.60
    q.fp(cx - 0.50, cx + 0.50, yf + 0.004, 0.10, 0.80, (150, 162, 152))
    for k in range(1, 4):
        z = 0.10 + k * (0.70 / 4)
        q.line([(cx - 0.50, yf + 0.006, z), (cx + 0.50, yf + 0.006, z)],
               (110, 124, 112), 0.9)
    q.line([(cx, yf + 0.006, 0.10), (cx, yf + 0.006, 0.80)],
           (110, 124, 112), 0.9)
    for jx0, jx1 in ((cx - 0.58, cx - 0.50), (cx + 0.50, cx + 0.58)):
        q.box((jx0, yf - 0.005, 0.095), (jx1, yf + 0.05, 0.86),
              (200, 212, 198), (180, 194, 178), (220, 230, 216))
    q.box((cx - 0.58, yf - 0.005, 0.80), (cx + 0.58, yf + 0.05, 0.88),
          (200, 212, 198), (180, 194, 178), (220, 230, 216))
    # Personnel door + window (+X).
    xf = cx + 0.80
    q.poly([(xf + 0.004, cy - 0.42, 0.10), (xf + 0.004, cy - 0.10, 0.10),
            (xf + 0.004, cy - 0.10, 0.78), (xf + 0.004, cy - 0.42, 0.78)],
           (96, 116, 102))
    q.poly([(xf + 0.006, cy - 0.38, 0.50), (xf + 0.006, cy - 0.14, 0.50),
            (xf + 0.006, cy - 0.14, 0.70), (xf + 0.006, cy - 0.38, 0.70)],
           (178, 208, 216))
    q.poly([(xf + 0.004, cy + 0.08, 0.40), (xf + 0.004, cy + 0.40, 0.40),
            (xf + 0.004, cy + 0.40, 0.72), (xf + 0.004, cy + 0.08, 0.72)],
           (170, 205, 215))
    q.line([(xf + 0.006, cy + 0.24, 0.40), (xf + 0.006, cy + 0.24, 0.72)],
           (110, 130, 120), 0.9)


# --------------------------------------------------------------------------
# 39-blok: 3-storey apartment block


def block(q, cx, cy, P):
    q.box((cx - 1.04, cy - 0.59, -0.02), (cx + 1.04, cy + 0.59, 0.10),
          (150, 166, 150), (128, 148, 128), (190, 200, 184))
    q.box((cx - 1.00, cy - 0.55, 0.095), (cx + 1.00, cy + 0.55, 1.95),
          (232, 226, 208), (196, 190, 168), (238, 234, 220))
    # Floor bands wrapping the shaft at each slab line.
    for fz in (0.68, 1.31):
        q.box((cx - 1.015, cy - 0.565, fz - 0.03),
              (cx + 1.015, cy + 0.565, fz + 0.03),
              (200, 192, 168), (178, 170, 148), (216, 208, 186))
    # Parapet + roof slab.
    q.box((cx - 1.00, cy - 0.55, 1.945), (cx + 1.00, cy + 0.55, 2.02),
          (216, 208, 186), (196, 190, 168), (228, 222, 202))
    q.box((cx - 1.02, cy - 0.57, 2.015), (cx + 1.02, cy + 0.57, 2.10),
          (200, 192, 168), (178, 170, 148), (216, 208, 186))
    # Stairwell strip (glazed, slightly proud) on +Y.
    yf = cy + 0.55
    q.fp(cx - 0.14, cx + 0.14, yf + 0.004, 0.30, 1.90, (170, 205, 215))
    for z in (0.85, 1.25, 1.65):
        q.line([(cx - 0.14, yf + 0.006, z), (cx + 0.14, yf + 0.006, z)],
               (110, 130, 120), 0.9)
    # Window grid (+Y): 3 floors x 3 cols beside the stairwell.
    for fz in (0.30, 0.93, 1.56):
        for wx in (cx - 0.82, cx - 0.44, cx + 0.44, cx + 0.82):
            q.fp(wx - 0.13, wx + 0.13, yf + 0.004, fz, fz + 0.32,
                 (170, 205, 215))
            q.line([(wx, yf + 0.006, fz), (wx, yf + 0.006, fz + 0.32)],
                   (110, 130, 120), 0.9)
            q.line([(wx - 0.13, yf + 0.006, fz + 0.16),
                    (wx + 0.13, yf + 0.006, fz + 0.16)],
                   (110, 130, 120), 0.9)
            q.box((wx - 0.15, yf - 0.005, fz - 0.05),
                  (wx + 0.15, yf + 0.045, fz - 0.005),
                  (220, 214, 196), (200, 194, 176), (232, 228, 212))
    # Balconies (+Y): slab sunk into the wall, panel + rails after.
    for fz in (0.30, 0.93, 1.56):
        for bx in (cx - 0.63, cx + 0.63):
            q.box((bx - 0.28, yf - 0.06, fz - 0.02),
                  (bx + 0.28, yf + 0.30, fz + 0.06),
                  (200, 192, 168), (178, 170, 148), (222, 214, 192))
            q.box((bx - 0.28, yf + 0.26, fz + 0.055),
                  (bx + 0.28, yf + 0.30, fz + 0.42),
                  (120, 140, 128), (104, 124, 112), (140, 158, 146))
            q.box((bx - 0.28, yf + 0.26, fz + 0.40),
                  (bx + 0.28, yf + 0.30, fz + 0.45),
                  (90, 108, 96), (90, 108, 96), (110, 128, 116))
            for side in (bx - 0.28, bx + 0.28):
                s0 = side - 0.02 if side < bx else side - 0.005
                s1 = side + 0.005 if side < bx else side + 0.02
                q.box((s0, yf - 0.02, fz + 0.055), (s1, yf + 0.28, fz + 0.44),
                      (120, 140, 128), (104, 124, 112), (140, 158, 146))
    # Entrance: canopy slab, door, step.
    q.box((cx - 0.25, yf - 0.02, 0.55), (cx + 0.25, yf + 0.35, 0.62),
          (150, 166, 152), (128, 146, 132), (190, 200, 188))
    q.box((cx - 0.22, yf + 0.04, 0.095), (cx - 0.20, yf + 0.06, 0.55),
          (90, 108, 96), (90, 108, 96), (90, 108, 96))
    q.box((cx + 0.20, yf + 0.04, 0.095), (cx + 0.22, yf + 0.06, 0.55),
          (90, 108, 96), (90, 108, 96), (90, 108, 96))
    q.fp(cx - 0.18, cx + 0.18, yf + 0.004, 0.10, 0.56, (96, 116, 102))
    q.fp(cx - 0.12, cx + 0.12, yf + 0.006, 0.30, 0.50, (178, 208, 216))
    q.box((cx - 0.24, yf + 0.0, -0.015), (cx + 0.24, yf + 0.42, 0.10),
          (180, 190, 178), (160, 172, 160), (205, 212, 200))
    # Side windows (+X).
    xf = cx + 1.00
    for fz in (0.30, 0.93, 1.56):
        for wy in (cy - 0.28, cy + 0.28):
            q.poly([(xf + 0.004, wy - 0.12, fz), (xf + 0.004, wy + 0.12, fz),
                    (xf + 0.004, wy + 0.12, fz + 0.32),
                    (xf + 0.004, wy - 0.12, fz + 0.32)], (170, 205, 215))
            q.line([(xf + 0.006, wy, fz), (xf + 0.006, wy, fz + 0.32)],
                   (110, 130, 120), 0.9)


# --------------------------------------------------------------------------
# 40-stodola: farm barn


def barn(q, cx, cy, P):
    # Stone foundation + red board walls.
    q.box((cx - 0.94, cy - 0.74, -0.02), (cx + 0.94, cy + 0.74, 0.16),
          (160, 162, 154), (138, 142, 134), (186, 188, 180))
    q.box((cx - 0.90, cy - 0.70, 0.155), (cx + 0.90, cy + 0.70, 0.95),
          (172, 96, 72), (148, 80, 60), (188, 112, 86))
    # Vertical board seams on the visible faces.
    for bx in [cx - 0.60, cx - 0.30, cx, cx + 0.30, cx + 0.60]:
        q.line([(bx, cy + 0.704, 0.16), (bx, cy + 0.704, 0.94)],
               (150, 80, 60), 0.7)
    for by in [cy - 0.35, cy, cy + 0.35]:
        q.line([(cx + 0.904, by, 0.16), (cx + 0.904, by, 0.94)],
               (128, 68, 52), 0.7)
    # Gable roof, ridge along X.
    q.poly([(cx - 0.98, cy + 0.78, 0.945), (cx + 0.98, cy + 0.78, 0.945),
            (cx + 0.98, cy, 1.60), (cx - 0.98, cy, 1.60)], (120, 110, 100))
    q.poly([(cx - 0.98, cy - 0.78, 0.945), (cx + 0.98, cy - 0.78, 0.945),
            (cx + 0.98, cy, 1.60), (cx - 0.98, cy, 1.60)], (104, 96, 88))
    for gx, col in ((cx - 0.90, (148, 80, 60)), (cx + 0.90, (172, 96, 72))):
        q.poly([(gx, cy - 0.70, 0.945), (gx, cy + 0.70, 0.945),
                (gx, cy, 1.595)], col)
    q.box((cx - 0.99, cy - 0.06, 1.59), (cx + 0.99, cy + 0.06, 1.67),
          (90, 84, 78), (78, 72, 66), (130, 122, 112))
    for i in range(8):
        rx = cx - 0.90 + i * (1.80 / 7)
        q.line([(rx, cy + 0.781, 0.95), (rx, cy, 1.595)], (104, 96, 88), 0.7)
    # Big double doors (+Y) with X braces.
    yf = cy + 0.70
    q.fp(cx - 0.45, cx + 0.45, yf + 0.004, 0.16, 0.90, (120, 70, 52))
    q.fp(cx - 0.39, cx - 0.02, yf + 0.006, 0.20, 0.86, (150, 88, 64))
    q.fp(cx + 0.02, cx + 0.39, yf + 0.006, 0.20, 0.86, (150, 88, 64))
    for dx0, dx1 in ((cx - 0.39, cx - 0.02), (cx + 0.02, cx + 0.39)):
        q.line([(dx0, yf + 0.008, 0.20), (dx1, yf + 0.008, 0.86)],
               (110, 64, 48), 1.0)
        q.line([(dx0, yf + 0.008, 0.86), (dx1, yf + 0.008, 0.20)],
               (110, 64, 48), 1.0)
    q.box((cx - 0.51, yf - 0.005, 0.155), (cx + 0.51, yf + 0.05, 0.22),
          (235, 228, 210), (215, 208, 190), (245, 240, 224))
    q.box((cx - 0.51, yf - 0.005, 0.84), (cx + 0.51, yf + 0.05, 0.92),
          (235, 228, 210), (215, 208, 190), (245, 240, 224))
    # Hayloft window + side door and windows (+X).
    q.fp(cx - 0.15, cx + 0.15, yf + 0.004, 1.00, 1.28, (178, 208, 216))
    q.line([(cx, yf + 0.006, 1.00), (cx, yf + 0.006, 1.28)],
           (110, 130, 120), 0.9)
    q.line([(cx - 0.15, yf + 0.006, 1.14), (cx + 0.15, yf + 0.006, 1.14)],
           (110, 130, 120), 0.9)
    xf = cx + 0.90
    q.poly([(xf + 0.004, cy - 0.45, 0.16), (xf + 0.004, cy - 0.05, 0.16),
            (xf + 0.004, cy - 0.05, 0.86), (xf + 0.004, cy - 0.45, 0.86)],
           (120, 70, 52))
    q.poly([(xf + 0.004, cy + 0.15, 0.45), (xf + 0.004, cy + 0.45, 0.45),
            (xf + 0.004, cy + 0.45, 0.75), (xf + 0.004, cy + 0.15, 0.75)],
           (178, 208, 216))
    q.line([(xf + 0.006, cy + 0.30, 0.45), (xf + 0.006, cy + 0.30, 0.75)],
           (110, 130, 120), 0.9)


# --------------------------------------------------------------------------
# 41-wiata-pv: carport with tilted PV roof


def carport(q, cx, cy, P):
    # Foot plates + 4 posts (tops run into the slab, painted before it).
    roof_z = {(sx, sy): 1.28 - 0.1538 * (sy + 0.65)
              for sx in (-0.85, 0.85) for sy in (-0.55, 0.55)}
    for sx in (-0.85, 0.85):
        for sy in (-0.55, 0.55):
            q.box((cx + sx - 0.09, cy + sy - 0.09, -0.02),
                  (cx + sx + 0.09, cy + sy + 0.09, 0.05),
                  (140, 148, 138), (120, 130, 120), (165, 172, 162))
            q.box((cx + sx - 0.05, cy + sy - 0.05, 0.045),
                  (cx + sx + 0.05, cy + sy + 0.05,
                   roof_z[(sx, sy)] + 0.03),
                  (110, 122, 112), (92, 104, 94), (130, 142, 132))
    # Cross beams under the slab along X at both ends.
    for sy in (-0.55, 0.55):
        rz = roof_z[(-0.85, sy)]
        q.box((cx - 0.92, cy + sy - 0.045, rz - 0.12),
              (cx + 0.92, cy + sy + 0.045, rz - 0.03),
              (110, 122, 112), (92, 104, 94), (130, 142, 132))
    # Tilted slab: high edge at -Y, low edge at +Y.
    A = (cx - 0.95, cy - 0.65, 1.28)
    B = (cx + 0.95, cy - 0.65, 1.28)
    C = (cx + 0.95, cy + 0.65, 1.08)
    D = (cx - 0.95, cy + 0.65, 1.08)

    def drop(p, dz):
        return (p[0], p[1], p[2] - dz)

    th = 0.07
    q.poly([drop(A, th), drop(B, th), drop(C, th), drop(D, th)],
           (70, 86, 78))
    q.poly([D, C, drop(C, th), drop(D, th)], (96, 112, 102))
    q.poly([B, C, drop(C, th), drop(B, th)], (82, 98, 88))
    q.poly([A, B, drop(B, th), drop(A, th)], (82, 98, 88))
    q.poly([A, B, C, D], (150, 160, 152))

    # PV field: 2 rows x 3 cols with gutters, strictly inside the roof.
    def lerp(P0, P1, f):
        return (P0[0] + (P1[0] - P0[0]) * f, P0[1] + (P1[1] - P0[1]) * f,
                P0[2] + (P1[2] - P0[2]) * f + 0.012)

    for r, (f0, f1) in enumerate(((0.06, 0.47), (0.53, 0.94))):
        for c, (g0, g1) in enumerate(
                ((0.05, 0.35), (0.375, 0.625), (0.65, 0.95))):
            p00 = lerp(lerp(A, D, f0), lerp(B, C, f0), g0)
            p10 = lerp(lerp(A, D, f0), lerp(B, C, f0), g1)
            p11 = lerp(lerp(A, D, f1), lerp(B, C, f1), g1)
            p01 = lerp(lerp(A, D, f1), lerp(B, C, f1), g0)
            q.poly([p00, p10, p11, p01], (72, 110, 150))
            # Cell grid: 2 dividers each way, subtle light lines.
            for f in (1 / 3, 2 / 3):
                e0 = lerp(p00, p01, f)
                e1 = lerp(p10, p11, f)
                q.line([e0, e1], (140, 180, 210), 0.7)
                e0 = lerp(p00, p10, f)
                e1 = lerp(p01, p11, f)
                q.line([e0, e1], (140, 180, 210), 0.7)
            # One diagonal sheen quad per panel, inside its outline.
            q.poly([lerp(p00, p10, 0.10), lerp(p00, p10, 0.35),
                    lerp(p01, p11, 0.25), lerp(p01, p11, 0.02)],
                   (255, 255, 255, 40))
    _ = (r, c)


# --------------------------------------------------------------------------
# 42-komin: brick chimney with cap


def chimney(q, cx, cy, P):
    # Concrete base + brick shaft.
    q.box((cx - 0.34, cy - 0.34, -0.02), (cx + 0.34, cy + 0.34, 0.14),
          (170, 176, 166), (148, 156, 146), (196, 200, 192))
    q.box((cx - 0.28, cy - 0.28, 0.135), (cx + 0.28, cy + 0.28, 0.30),
          (150, 158, 148), (130, 140, 130), (176, 182, 174))
    q.box((cx - 0.22, cy - 0.22, 0.295), (cx + 0.22, cy + 0.22, 1.55),
          (168, 105, 80), (146, 88, 66), (186, 124, 96))
    # Brick courses: mortar beds + staggered perpends on +Y/+X faces.
    yf = cy + 0.22
    xf = cx + 0.22
    course = 0
    z = 0.36
    while z < 1.52:
        q.line([(cx - 0.22, yf + 0.002, z), (cx + 0.22, yf + 0.002, z)],
               (210, 190, 170), 0.8)
        q.line([(xf + 0.002, cy - 0.22, z), (xf + 0.002, cy + 0.22, z)],
               (190, 172, 152), 0.8)
        off = 0.055 if course % 2 else 0.0
        xx = cx - 0.22 + off
        while xx < cx + 0.20:
            q.line([(xx, yf + 0.002, z), (xx, yf + 0.002, z + 0.115)],
                   (190, 172, 152), 0.6)
            xx += 0.11
        yy = cy - 0.22 + off
        while yy < cy + 0.20:
            q.line([(xf + 0.002, yy, z), (xf + 0.002, yy, z + 0.115)],
                   (172, 154, 136), 0.6)
            yy += 0.11
        course += 1
        z += 0.12
    # Flashing collar + cap slab + clay flue.
    q.box((cx - 0.26, cy - 0.26, 1.42), (cx + 0.26, cy + 0.26, 1.50),
          (130, 140, 130), (112, 124, 114), (155, 163, 153))
    q.box((cx - 0.30, cy - 0.30, 1.495), (cx + 0.30, cy + 0.30, 1.60),
          (196, 200, 192), (170, 176, 168), (216, 220, 212))
    q.box((cx - 0.26, cy - 0.26, 1.595), (cx + 0.26, cy + 0.26, 1.63),
          (170, 176, 168), (170, 176, 168), (170, 176, 168))
    from .world import _cylinder as _cyl

    _cyl(q, cx, cy, 1.625, 1.78, 0.13,
         (150, 116, 92), (118, 90, 70), (168, 134, 108), n=24)
    q.ground_ellipse(cx, cy, 0.13, 0.13, (66, 72, 66), z=1.835)
    q.ground_ellipse(cx, cy, 0.09, 0.09, (88, 96, 88), z=1.836)


PROPS = {
    "hall": {"fn": hall, "focus": (0.0, 0.15, 0.76), "k": 212,
             "plinth": (0.0, 0.15, 1.55, 1.15),
             "brief": "production hall: big box, skylight strips, dock door, plain signage band"},
    "rack": {"fn": rack, "focus": (0.0, 0.15, 0.88), "k": 258,
             "plinth": (0.0, 0.15, 1.05, 0.65),
             "brief": "warehouse rack frame with stocked boxes"},
    "garage": {"fn": garage, "focus": (0.0, 0.15, 0.74), "k": 253,
               "plinth": (0.0, 0.15, 1.20, 0.95),
               "brief": "detached garage with sectional door"},
    "block": {"fn": block, "focus": (0.0, 0.15, 1.20), "k": 182,
              "plinth": (0.0, 0.15, 1.40, 1.00),
              "brief": "3-storey apartment block with balconies and entrance"},
    "barn": {"fn": barn, "focus": (0.0, 0.15, 0.86), "k": 222,
             "plinth": (0.0, 0.15, 1.30, 1.05),
             "brief": "farm barn with big doors and roof"},
    "carport": {"fn": carport, "focus": (0.0, 0.15, 0.785), "k": 235,
                "plinth": (0.0, 0.15, 1.30, 1.00),
                "brief": "carport with tilted PV panel roof on posts"},
    "chimney": {"fn": chimney, "focus": (0.0, 0.15, 0.90), "k": 297,
                "plinth": (0.0, 0.15, 0.60, 0.50),
                "brief": "brick chimney with cap"},
}
