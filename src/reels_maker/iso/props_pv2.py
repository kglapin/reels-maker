"""Iso gallery props batch pv2 (112-126): PV panels, mounting, BOS, inverter, care."""

from __future__ import annotations

from reels_maker.iso.world import _cylinder

ALU = ((168, 178, 170), (138, 150, 142), (190, 198, 190))
ALU_D = ((120, 130, 122), (100, 110, 102), (140, 150, 142))
STEEL_D = ((96, 106, 98), (80, 90, 82), (116, 126, 118))
GREY = ((168, 176, 168), (140, 150, 142), (190, 198, 190))
CONCRETE = ((188, 190, 180), (160, 162, 152), (206, 208, 198))
CELL_T = (78, 118, 172)
CELL_F = (66, 100, 140)
CELL_S = (66, 96, 132)
COPPER_L, COPPER_D, COPPER_T = (196, 138, 88), (150, 100, 62), (210, 156, 104)
TERRA = ((186, 116, 84), (150, 90, 64), (202, 134, 100))
WOOD = ((196, 158, 108), (160, 124, 82), (210, 174, 124))

ROOF_EDGE_F, ROOF_EDGE_S, ROOF_EDGE_T = (112, 119, 127), (88, 96, 106), (139, 146, 153)
ROOF_F, ROOF_S, ROOF_T = (145, 152, 160), (119, 128, 138), (166, 173, 180)
BALLAST_F, BALLAST_S, BALLAST_T = (178, 171, 157), (147, 141, 130), (199, 192, 178)
SUPPORT_F, SUPPORT_S, SUPPORT_T = (129, 144, 158), (96, 111, 127), (160, 175, 188)
FRAME_F, FRAME_S, FRAME_T = (186, 198, 209), (143, 159, 175), (215, 224, 231)
PV_F, PV_S, PV_T = (72, 100, 132), (62, 81, 109), (80, 115, 151)
CELL_LINE = (130, 157, 183)


def _tilted_panel(q, x0, x1, y0, y1, zlo, zhi, cs, cf, ct):
    """Slab tilted around X: bottom zlo(y), top zhi(y), both linear in y.
    zlo/zhi are (value at y0, value at y1). Draws +X side, +Y edge, top."""
    l0, l1 = zlo
    h0, h1 = zhi

    def lo(y):
        return l0 + (l1 - l0) * (y - y0) / (y1 - y0)

    def hi(y):
        return h0 + (h1 - h0) * (y - y0) / (y1 - y0)

    q.poly([(x1, y0, lo(y0)), (x1, y1, lo(y1)),
            (x1, y1, hi(y1)), (x1, y0, hi(y0))], cs)
    q.poly([(x0, y1, lo(y1)), (x1, y1, lo(y1)),
            (x1, y1, hi(y1)), (x0, y1, hi(y1))], cf)
    q.poly([(x0, y0, hi(y0)), (x1, y0, hi(y0)),
            (x1, y1, hi(y1)), (x0, y1, hi(y1))], ct)


def _pv_zbot(y, y0, y1):
    return 0.205 + 0.100 * (y - y0) / (y1 - y0)


def _support_wedge(q, fx0, fx1, ys0, ys1, zt0, zt1):
    """Solid wedge over one ballast foot: flat bottom z=0.125, sloped top
    from zt0 (at ys0) to zt1 (at ys1), width 0.035 centred on the foot."""
    xc = (fx0 + fx1) / 2
    xs0, xs1 = xc - 0.0175, xc + 0.0175
    zb = 0.125
    q.poly([(xs1, ys0, zb), (xs1, ys1, zb),
            (xs1, ys1, zt1), (xs1, ys0, zt0)], SUPPORT_S)
    q.poly([(xs0, ys1, zb), (xs1, ys1, zb),
            (xs1, ys1, zt1), (xs0, ys1, zt1)], SUPPORT_F)
    q.poly([(xs0, ys0, zt0), (xs1, ys0, zt0),
            (xs1, ys1, zt1), (xs0, ys1, zt1)], SUPPORT_T)


def flat_roof_pv_array(q, cx, cy, P):
    """Cztery pochylone moduły fotowoltaiczne na konstrukcjach balastowych
    na płaskim dachu."""
    q.box((cx - 0.60, cy - 0.525, 0.0), (cx + 0.60, cy + 0.525, 0.065),
          ROOF_EDGE_F, ROOF_EDGE_S, ROOF_EDGE_T)
    q.box((cx - 0.595, cy - 0.520, 0.055), (cx + 0.595, cy + 0.520, 0.095),
          ROOF_F, ROOF_S, ROOF_T)

    cols = [(-0.49, -0.03), (0.03, 0.49)]
    rows = [(-0.40, -0.06), (0.06, 0.40)]
    modules = []
    for (x0, x1) in cols:
        for (y0, y1) in rows:
            modules.append((x0, x1, y0, y1))
    modules.sort(key=lambda m: (m[0] + m[1]) / 2 + (m[2] + m[3]) / 2)

    for x0, x1, y0, y1 in modules:
        X0, X1 = cx + x0, cx + x1
        Y0, Y1 = cy + y0, cy + y1
        foot_x = [(x0 + 0.045, x0 + 0.135), (x1 - 0.135, x1 - 0.045)]
        for fx0, fx1 in foot_x:
            q.box((cx + fx0, Y0 + 0.015, 0.085),
                  (cx + fx1, Y1 - 0.015, 0.135),
                  BALLAST_F, BALLAST_S, BALLAST_T)
        ys0, ys1 = Y0 + 0.02, Y1 - 0.02
        for fx0, fx1 in foot_x:
            zt0 = _pv_zbot(ys0, Y0, Y1) + 0.010
            zt1 = _pv_zbot(ys1, Y0, Y1) + 0.010
            _support_wedge(q, cx + fx0, cx + fx1, ys0, ys1, zt0, zt1)
        _tilted_panel(q, X0, X1, Y0, Y1,
                      (0.205, 0.305), (0.230, 0.330),
                      FRAME_S, FRAME_F, FRAME_T)
        xa, xb = X0 + 0.016, X1 - 0.016
        ya, yb = Y0 + 0.016, Y1 - 0.016
        zlo = (0.205 + 0.019, 0.305 + 0.019)
        zhi = (0.205 + 0.031, 0.305 + 0.031)

        def pv_top(y):
            return _pv_zbot(y, Y0, Y1) + 0.031

        _tilted_panel(q, xa, xb, ya, yb, zlo, zhi, PV_S, PV_F, PV_T)
        eps = 0.004
        xmid = (xa + xb) / 2
        q.line([(xmid, ya, pv_top(ya) + eps), (xmid, yb, pv_top(yb) + eps)],
               CELL_LINE, 0.9)
        for k in (1, 2, 3):
            yt = ya + (yb - ya) * k / 4
            z = pv_top(yt) + eps
            q.line([(xa, yt, z), (xb, yt, z)], CELL_LINE, 0.9)


def panel_single(q, cx, cy, P):
    """Single PV module: 18 raised navy cells with a hairline gap grid,
    alu frame, rail racking, clip clamps, jbox with conduits."""
    for px in (cx - 0.45, cx + 0.45):
        for ry in (cy - 0.14, cy + 0.14):
            q.boxg((px - 0.035, ry - 0.035, -0.02),
                  (px + 0.035, ry + 0.035, 0.10), *STEEL_D)
    for ry in (cy - 0.14, cy + 0.14):
        q.boxg((cx - 0.62, ry - 0.045, -0.02), (cx + 0.62, ry + 0.045, 0.24),
              *ALU_D)
    # Panel slab: dark backsheet, top at 0.375.
    q.boxg((cx - 0.55, cy - 0.265, 0.20), (cx + 0.55, cy + 0.265, 0.375),
          (16, 24, 38), (12, 18, 30), (24, 34, 52))
    # Alu frame rails rising around the raised cell field.
    for fy in (cy - 0.265, cy + 0.265):
        q.boxg((cx - 0.55, fy - 0.025, 0.36), (cx + 0.55, fy + 0.025, 0.495),
              *ALU)
    for fx in (cx - 0.525, cx + 0.525):
        q.boxg((fx - 0.025, cy - 0.265, 0.36), (fx + 0.025, cy + 0.265, 0.495),
              *ALU)
    # Hairline grid recessed in the cell gaps, just above the backsheet.
    for i in range(1, 6):
        gx = cx - 0.48 + i * 0.162 - 0.006
        q.line([(gx, cy - 0.222, 0.382), (gx, cy + 0.222, 0.382)],
               (150, 170, 200), 1)
    for j in range(1, 3):
        gy = cy - 0.222 + j * 0.152 - 0.006
        q.line([(cx - 0.48, gy, 0.382), (cx + 0.48, gy, 0.382)],
               (150, 170, 200), 1)
    # 6x3 raised navy cells with real gaps (not painted lines).
    for i in range(6):
        x0 = cx - 0.48 + i * (0.15 + 0.012)
        for j in range(3):
            y0 = cy - 0.222 + j * (0.14 + 0.012)
            q.boxg((x0, y0, 0.37), (x0 + 0.15, y0 + 0.14, 0.48),
                  (30, 54, 98), (22, 40, 74), (44, 72, 128))
    # Three silver busbar strips on the row centers.
    for by in (cy - 0.152, cy, cy + 0.152):
        q.fp(cx - 0.47, cx + 0.47, by, 0.481, 0.488, (190, 200, 215))
    # Slim clip clamps straddling the side rails above the cell tops.
    for sx in (cx - 0.525, cx + 0.525):
        for sy in (cy - 0.10, cy + 0.10):
            q.boxg((sx - 0.028, sy - 0.018, 0.455),
                  (sx + 0.028, sy + 0.018, 0.50), *STEEL_D)
    # Jbox sunk into the frame back, bridge boxes into the frame,
    # long conduits rail -> backsheet (every end buried).
    q.boxg((cx - 0.12, cy + 0.28, 0.16), (cx + 0.12, cy + 0.365, 0.23), *GREY)
    for ex in (cx - 0.06, cx + 0.06):
        q.boxg((ex - 0.015, cy + 0.28, 0.20), (ex + 0.015, cy + 0.30, 0.26),
               *STEEL_D)
    for ex in (cx - 0.25, cx + 0.25):
        q.boxg((ex - 0.015, cy + 0.12, 0.02), (ex + 0.015, cy + 0.16, 0.31),
               *STEEL_D)
    q.ao(cx, cy, 0.80)


def panel_roof(q, cx, cy, P):
    """Plain rooftop PV module: flat concrete roof, two rails, alu frame
    with 18 gapped navy cells, clamps, jbox with conduits into roof."""
    q.boxg((cx - 0.68, cy - 0.40, -0.02), (cx + 0.68, cy + 0.40, 0.08),
          (150, 152, 148), (128, 130, 126), (170, 172, 168))
    for ry in (cy - 0.14, cy + 0.14):
        q.boxg((cx - 0.62, ry - 0.045, 0.06), (cx + 0.62, ry + 0.045, 0.16),
              *ALU_D)
    for fy in (cy - 0.265, cy + 0.265):
        q.boxg((cx - 0.55, fy - 0.025, 0.15), (cx + 0.55, fy + 0.025, 0.31),
              *ALU)
    for fx in (cx - 0.525, cx + 0.525):
        q.boxg((fx - 0.025, cy - 0.265, 0.15), (fx + 0.025, cy + 0.265, 0.31),
              *ALU)
    q.boxg((cx - 0.49, cy - 0.23, 0.24), (cx + 0.49, cy + 0.23, 0.265),
          (16, 24, 38), (12, 18, 30), (24, 34, 52))
    for i in range(6):
        x0 = cx - 0.48 + i * (0.15 + 0.012)
        for j in range(3):
            y0 = cy - 0.222 + j * (0.14 + 0.012)
            q.boxg((x0, y0, 0.26), (x0 + 0.15, y0 + 0.14, 0.305),
                  (30, 54, 98), (22, 40, 74), (44, 72, 128))
    for by in (cy - 0.152, cy, cy + 0.152):
        q.fp(cx - 0.47, cx + 0.47, by, 0.306, 0.313, (190, 200, 215))
    for sx in (cx - 0.525, cx + 0.525):
        for sy in (cy - 0.10, cy + 0.10):
            q.boxg((sx - 0.03, sy - 0.02, 0.30), (sx + 0.03, sy + 0.02, 0.34),
                  *STEEL_D)
    q.boxg((cx - 0.12, cy + 0.28, 0.16), (cx + 0.12, cy + 0.365, 0.23), *GREY)
    for ex in (cx - 0.06, cx + 0.06):
        q.boxg((ex - 0.015, cy + 0.28, 0.20), (ex + 0.015, cy + 0.30, 0.26),
               *STEEL_D)
    for ex in (cx - 0.25, cx + 0.25):
        q.boxg((ex - 0.015, cy + 0.12, 0.02), (ex + 0.015, cy + 0.16, 0.25),
               *STEEL_D)


def rail_set(q, cx, cy, P):
    """Pair of mounting rails on feet, clamps straddling, bolt dots."""
    for fx in (cx - 0.40, cx + 0.40):
        for fy in (cy - 0.10, cy + 0.10):
            q.box((fx - 0.05, fy - 0.05, -0.02), (fx + 0.05, fy + 0.05, 0.10),
                  *ALU_D)
    for ry in (cy - 0.10, cy + 0.10):
        q.box((cx - 0.55, ry - 0.035, 0.08), (cx + 0.55, ry + 0.035, 0.16), *ALU)
    for ry in (cy - 0.10, cy + 0.10):
        for bx in (cx - 0.30, cx + 0.30):
            q.box((bx - 0.05, ry - 0.05, 0.15), (bx + 0.05, ry + 0.05, 0.24),
                  *STEEL_D)
            q.dot((bx, ry, 0.245), 0.9, (210, 220, 210, 255))


def ballast(q, cx, cy, P):
    """Concrete ballast block with steel rail foot and bolts."""
    q.box((cx - 0.30, cy - 0.20, -0.02), (cx + 0.30, cy + 0.20, 0.30), *CONCRETE)
    q.box((cx - 0.29, cy - 0.19, 0.26), (cx + 0.29, cy + 0.19, 0.295),
          (200, 200, 192), (200, 200, 192), (200, 200, 192))
    for gz in (0.10, 0.20):
        q.line([(cx - 0.29, cy + 0.201, gz), (cx + 0.29, cy + 0.201, gz)],
               (150, 150, 142), 0.8)
    for sx, sz in ((cx - 0.20, 0.12), (cx + 0.20, 0.12), (cx - 0.20, 0.22),
                   (cx + 0.20, 0.22)):
        q.box((sx - 0.025, cy + 0.195, sz), (sx + 0.025, cy + 0.23, sz + 0.05),
              (120, 120, 112), (120, 120, 112), (120, 120, 112))
    q.box((cx - 0.12, cy - 0.06, 0.28), (cx + 0.12, cy + 0.14, 0.33), *STEEL_D)
    q.box((cx - 0.05, cy - 0.02, 0.28), (cx + 0.05, cy + 0.10, 0.52), *STEEL_D)
    for dx in (cx - 0.08, cx + 0.08):
        q.dot((dx, cy + 0.10, 0.335), 0.8, (210, 220, 210, 255))
    for dx in (cx - 0.08, cx + 0.08):
        q.dot((dx, cy + 0.141, 0.30), 0.8, (210, 220, 210, 255))


def optimizer(q, cx, cy, P):
    """Optimizer box slung UNDER the panel (per brief), short thick
    cable conduits box-top to panel underside. One assembly, one hero."""
    for lx in (cx - 0.22, cx + 0.22):
        q.boxg((lx - 0.035, cy - 0.26, -0.02), (lx + 0.035, cy - 0.20, 0.64),
              *ALU_D)
    q.boxg((cx - 0.30, cy - 0.30, 0.62), (cx + 0.30, cy + 0.02, 0.665), *ALU)
    q.boxg((cx - 0.26, cy - 0.26, 0.66), (cx + 0.26, cy - 0.02, 0.72),
          CELL_F, CELL_S, CELL_T)
    q.boxg((cx - 0.20, cy - 0.16, 0.05), (cx + 0.20, cy + 0.02, 0.42),
          (88, 98, 94), (72, 82, 76), (108, 118, 112))
    q.boxg((cx - 0.28, cy - 0.30, 0.52), (cx + 0.28, cy + 0.0, 0.565), *ALU)
    q.boxg((cx - 0.24, cy - 0.26, 0.56), (cx + 0.24, cy - 0.04, 0.62),
          (58, 88, 124), (54, 82, 116), (68, 102, 140))
    for gx in (cx - 0.10, cx + 0.10):
        q.boxg((gx - 0.010, cy - 0.25, 0.615), (gx + 0.010, cy - 0.05, 0.635),
              (200, 218, 238), (200, 218, 238), (200, 218, 238))
    q.boxg((cx - 0.23, cy - 0.16, 0.615), (cx + 0.23, cy - 0.14, 0.635),
          (200, 218, 238), (200, 218, 238), (200, 218, 238))
    # Terminal strip: pale mount plate bridging box-top to panel
    # underside; the dark conduits run ON its face. Dark-on-dark is
    # unreadable at 768px — cables need a light ground (contrast is a
    # physical readability requirement, corpus gate 2026-11-12).
    q.boxg((cx - 0.16, cy - 0.16, 0.36), (cx + 0.16, cy - 0.06, 0.58),
          (170, 178, 172), (150, 158, 152), (188, 196, 188))
    # Cable conduits: short, thick, box-top into the strip face.
    for cbx in (cx - 0.12, cx + 0.12):
        q.boxg((cbx - 0.025, cy - 0.10, 0.40), (cbx + 0.025, cy + 0.0, 0.54),
              (40, 48, 44), (40, 48, 44), (40, 48, 44))
    q.fp(cx - 0.14, cx + 0.02, cy + 0.022, 0.20, 0.28, (62, 76, 70))
    q.fp(cx - 0.14, cx + 0.14, cy + 0.022, 0.31, 0.35, (220, 170, 100))
    q.dot((cx + 0.10, cy + 0.022, 0.33), 0.9, (110, 200, 130, 255))
    q.boxg((cx - 0.02, cy - 0.01, 0.40), (cx + 0.015, cy + 0.03, 0.54),
          (66, 74, 70), (60, 68, 64), (80, 88, 84))
    # (Side conduits removed: they read as posts, and the link cables
    # already carry the electrical connection. Less is more.)


def monitoring_stick(q, cx, cy, P):
    """Monitoring USB stick: plug, body, LED, tall antenna."""
    q.boxg((cx - 0.04, cy - 0.03, -0.02), (cx + 0.04, cy + 0.05, 0.06), *ALU)
    q.boxg((cx - 0.10, cy - 0.07, 0.02), (cx + 0.10, cy + 0.09, 0.22),
          (110, 140, 150), (88, 114, 124), (132, 162, 172))
    q.line([(cx - 0.09, cy + 0.091, 0.06), (cx + 0.09, cy + 0.091, 0.06)],
           (80, 100, 110), 0.8)
    q.line([(cx - 0.09, cy + 0.091, 0.18), (cx + 0.09, cy + 0.091, 0.18)],
           (80, 100, 110), 0.8)
    for px in (cx - 0.02, cx + 0.02):
        q.boxg((px - 0.008, cy - 0.01, -0.015), (px + 0.008, cy + 0.03, 0.025),
              (200, 204, 206), (200, 204, 206), (200, 204, 206))
    q.boxg((cx - 0.03, cy - 0.03, 0.20), (cx + 0.03, cy + 0.03, 0.70), *STEEL_D)
    q.boxg((cx - 0.045, cy - 0.045, 0.18), (cx + 0.045, cy + 0.045, 0.24),
          (80, 88, 84), (80, 88, 84), (80, 88, 84))
    q.boxg((cx - 0.055, cy + 0.085, 0.11), (cx + 0.055, cy + 0.10, 0.17),
          (200, 220, 210), (200, 220, 210), (200, 220, 210))
    q.dot((cx + 0.031, cy, 0.68), 1.1, (90, 100, 92, 255))
    q.dot((cx - 0.03, cy + 0.101, 0.14), 1.1, (110, 200, 130, 255))
    q.line([(cx - 0.05, cy + 0.091, 0.08), (cx + 0.05, cy + 0.091, 0.08)],
           (80, 100, 110), 0.8)
    q.dot((cx, cy + 0.031, 0.705), 0.9, (200, 60, 50, 255))


def earth_rod(q, cx, cy, P):
    """Copper earthing rod, clamp, wire stub down into the ground."""
    _cylinder(q, cx, cy, -0.02, 0.85, 0.035,
              COPPER_L, COPPER_D, COPPER_T, n=12)
    q.box((cx - 0.07, cy - 0.07, 0.55), (cx + 0.07, cy + 0.07, 0.65), *STEEL_D)
    q.dot((cx, cy + 0.071, 0.60), 0.9, (210, 220, 210, 255))
    q.box((cx + 0.0, cy - 0.06, 0.50), (cx + 0.25, cy - 0.01, 0.56),
          *STEEL_D)
    q.box((cx + 0.20, cy - 0.05, -0.02), (cx + 0.25, cy + 0.0, 0.55), *STEEL_D)


def surge_box(q, cx, cy, P):
    """Surge protection box: base, hero, switch, LEDs, glands."""
    q.boxg((cx - 0.24, cy - 0.12, -0.02), (cx + 0.24, cy + 0.16, 0.14), *ALU_D)
    q.boxg((cx - 0.22, cy - 0.10, 0.10), (cx + 0.22, cy + 0.14, 0.72), *GREY)
    q.boxg((cx - 0.10, cy + 0.135, 0.40), (cx + 0.02, cy + 0.185, 0.58),
          *STEEL_D)
    q.dot((cx - 0.04, cy + 0.186, 0.52), 0.9, (230, 150, 80, 255))
    q.dot((cx + 0.12, cy + 0.141, 0.60), 0.9, (110, 200, 130, 255))
    q.dot((cx + 0.12, cy + 0.141, 0.52), 0.9, (230, 150, 80, 255))
    # Amber pilot lamp with bezel: the house accent that marks the
    # important element (corpus gate round 2).
    q.dot((cx + 0.14, cy + 0.141, 0.62), 1.4, (40, 52, 44, 255))
    q.dot((cx + 0.14, cy + 0.141, 0.62), 0.9, (255, 176, 92, 255))
    q.line([(cx - 0.14, cy + 0.141, 0.34), (cx + 0.14, cy + 0.141, 0.34)],
           (120, 130, 122), 0.8)
    for gx in (cx - 0.10, cx + 0.10):
        q.boxg((gx - 0.035, cy + 0.135, 0.10), (gx + 0.035, cy + 0.185, 0.22),
              *STEEL_D)


def solar_coil(q, cx, cy, P):
    """Coiled solar cable: stacked rings, tail, two MC4 plugs."""
    q.ground_ellipse(cx, cy, 0.30, 0.30, (70, 80, 72), z=0.02)
    q.ground_ellipse(cx, cy, 0.30, 0.30, (80, 90, 82), z=0.09)
    q.ground_ellipse(cx, cy, 0.30, 0.30, (70, 80, 72), z=0.16)
    q.ground_ellipse(cx, cy, 0.26, 0.26, (100, 112, 102), z=0.175)
    q.ground_ellipse(cx, cy, 0.22, 0.22, (70, 80, 72), z=0.19)
    q.ground_ellipse(cx, cy, 0.18, 0.18, (100, 112, 102), z=0.205)
    q.ground_ellipse(cx, cy, 0.14, 0.14, (70, 80, 72), z=0.22)
    q.ground_ellipse(cx, cy, 0.09, 0.09, (214, 228, 218, 200), z=0.225)
    q.boxg((cx + 0.05, cy + 0.18, 0.015), (cx + 0.42, cy + 0.26, 0.09),
          (66, 74, 70), (60, 68, 64), (80, 88, 84))
    q.boxg((cx + 0.08, cy + 0.185, 0.085), (cx + 0.24, cy + 0.218, 0.16),
          (70, 80, 74), (60, 68, 64), (86, 96, 90))
    q.boxg((cx + 0.13, cy + 0.18, 0.08), (cx + 0.155, cy + 0.223, 0.165),
          (220, 170, 100), (180, 134, 74), (235, 188, 120))
    q.boxg((cx + 0.24, cy + 0.193, 0.10), (cx + 0.29, cy + 0.21, 0.14),
          (170, 180, 175), (150, 160, 155), (185, 193, 188))
    q.boxg((cx + 0.08, cy + 0.222, 0.085), (cx + 0.24, cy + 0.255, 0.16),
          (70, 80, 74), (60, 68, 64), (86, 96, 90))
    q.boxg((cx + 0.24, cy + 0.23, 0.10), (cx + 0.29, cy + 0.247, 0.14),
          (170, 180, 175), (150, 160, 155), (185, 193, 188))


def roof_hook(q, cx, cy, P):
    """Stainless roof hook: plate, riser, arm, tip, bolts."""
    q.box((cx - 0.16, cy - 0.10, -0.02), (cx + 0.16, cy + 0.12, 0.08), *ALU_D)
    q.box((cx - 0.05, cy - 0.02, 0.06), (cx + 0.05, cy + 0.06, 0.55), *ALU)
    q.box((cx - 0.05, cy - 0.02, 0.48), (cx + 0.30, cy + 0.06, 0.58), *ALU)
    q.box((cx + 0.24, cy - 0.02, 0.36), (cx + 0.30, cy + 0.06, 0.50), *ALU_D)
    for dx in (cx - 0.11, cx + 0.11):
        for dy in (cy - 0.05, cy + 0.07):
            q.dot((dx, dy, 0.085), 0.8, (70, 80, 72, 255))


def snow_guard(q, cx, cy, P):
    """Snow guard rail: base strip, three brackets, top rail."""
    q.box((cx - 0.55, cy - 0.08, -0.02), (cx + 0.55, cy + 0.10, 0.10), *STEEL_D)
    for bx in (cx - 0.40, cx, cx + 0.40):
        q.box((bx - 0.04, cy - 0.04, 0.08), (bx + 0.04, cy + 0.06, 0.30), *ALU_D)
    q.box((cx - 0.55, cy - 0.04, 0.26), (cx + 0.55, cy + 0.06, 0.36), *ALU)
    q.dot((cx - 0.55, cy + 0.01, 0.31), 0.8, (70, 80, 72, 255))


def bird_guard(q, cx, cy, P):
    """Mesh bird guard strip: panel, grid lines, rails, clips."""
    q.box((cx - 0.52, cy - 0.07, -0.02), (cx + 0.52, cy + 0.03, 0.12), *ALU_D)
    q.box((cx - 0.50, cy - 0.06, 0.08), (cx + 0.50, cy + 0.02, 0.50),
          (80, 92, 84), (68, 80, 72), (96, 108, 98))
    q.box((cx - 0.52, cy - 0.07, 0.48), (cx + 0.52, cy + 0.03, 0.55), *ALU)
    fy = cy + 0.022
    for i in range(11):
        xx = cx - 0.50 + i * 0.10
        q.line([(xx, fy, 0.10), (xx, fy, 0.48)], (150, 160, 152), 0.7)
    for zz in (0.16, 0.24, 0.32, 0.40):
        q.line([(cx - 0.50, fy, zz), (cx + 0.50, fy, zz)], (150, 160, 152), 0.7)
    for bx in (cx - 0.30, cx, cx + 0.30):
        q.box((bx - 0.03, cy + 0.015, 0.10), (bx + 0.03, cy + 0.045, 0.20),
              *STEEL_D)


def inverter_string(q, cx, cy, P):
    """String inverter: hero box, display, LEDs, switch, glands."""
    q.boxg((cx - 0.28, cy - 0.14, -0.02), (cx + 0.28, cy + 0.16, 0.12), *ALU_D)
    q.boxg((cx - 0.26, cy - 0.12, 0.08), (cx + 0.26, cy + 0.14, 0.78),
          (200, 208, 198), (170, 180, 170), (216, 224, 214))
    q.fp(cx - 0.14, cx + 0.02, cy + 0.142, 0.52, 0.66, (62, 76, 70))
    q.fp(cx - 0.12, cx + 0.0, cy + 0.144, 0.57, 0.61, (110, 150, 135))
    q.fp(cx - 0.12, cx - 0.04, cy + 0.144, 0.545, 0.56, (110, 150, 135))
    q.dot((cx + 0.12, cy + 0.142, 0.60), 0.9, (110, 200, 130, 255))
    q.dot((cx + 0.12, cy + 0.142, 0.53), 0.9, (230, 150, 80, 255))
    q.boxg((cx + 0.06, cy + 0.10, 0.34), (cx + 0.18, cy + 0.155, 0.46), *STEEL_D)
    for gx, top in ((cx - 0.14, 0.34), (cx - 0.02, 0.34), (cx + 0.10, 0.36)):
        q.boxg((gx - 0.025, cy + 0.09, 0.06), (gx + 0.025, cy + 0.15, top),
              *STEEL_D)
    for i, vz in enumerate((0.30, 0.26, 0.22)):
        q.line([(cx + 0.262, cy - 0.08, vz), (cx + 0.262, cy + 0.10, vz)],
               (150, 160, 152), 0.8)


def combiner_2(q, cx, cy, P):
    """String combiner box: base, hero, lid, fuses, glands, stripe."""
    q.boxg((cx - 0.26, cy - 0.13, -0.02), (cx + 0.26, cy + 0.15, 0.16), *ALU_D)
    q.boxg((cx - 0.24, cy - 0.11, 0.12), (cx + 0.24, cy + 0.13, 0.70), *GREY)
    q.boxg((cx - 0.25, cy + 0.125, 0.14), (cx + 0.25, cy + 0.16, 0.68), *ALU)
    q.fp(cx - 0.18, cx + 0.18, cy + 0.162, 0.20, 0.26, (220, 170, 100))
    for i, fx in enumerate((cx - 0.15, cx - 0.05, cx + 0.05, cx + 0.15)):
        q.boxg((fx - 0.035, cy + 0.155, 0.40), (fx + 0.035, cy + 0.185, 0.52),
              (220, 170, 100), (180, 134, 74), (235, 188, 120))
        q.dot((fx, cy + 0.186, 0.46), 0.7, (90, 80, 60, 255))
    q.line([(cx - 0.18, cy + 0.162, 0.58), (cx + 0.18, cy + 0.162, 0.58)],
           (120, 130, 122), 0.8)
    for gx in (cx - 0.10, cx + 0.10):
        q.boxg((gx - 0.035, cy + 0.145, 0.02), (gx + 0.035, cy + 0.19, 0.18),
              *STEEL_D)


def cleaning_brush(q, cx, cy, P):
    """PV cleaning brush: bristles, head, telescopic handle, grip."""
    q.box((cx - 0.30, cy - 0.08, -0.02), (cx + 0.10, cy + 0.10, 0.08),
          (90, 104, 96), (76, 90, 82), (108, 122, 112))
    q.box((cx - 0.30, cy - 0.08, 0.06), (cx + 0.10, cy + 0.10, 0.20),
          (120, 150, 160), (96, 122, 132), (142, 172, 182))
    q.box((cx + 0.08, cy - 0.015, 0.075), (cx + 0.62, cy + 0.045, 0.15), *ALU)
    q.box((cx + 0.48, cy - 0.025, 0.07), (cx + 0.62, cy + 0.055, 0.16),
          *STEEL_D)
    q.dot((cx + 0.55, cy + 0.056, 0.115), 0.8, (200, 210, 200, 255))


def tile_plain(q, cx, cy, P):
    """Plain roof tile on a wooden batten, front lip, embossed lines."""
    q.box((cx - 0.45, cy - 0.20, -0.02), (cx + 0.45, cy + 0.10, 0.10), *WOOD)
    q.box((cx - 0.40, cy - 0.16, 0.08), (cx + 0.40, cy + 0.14, 0.20), *TERRA)
    q.box((cx - 0.40, cy + 0.10, -0.02), (cx + 0.40, cy + 0.18, 0.12), *TERRA)
    for ly in (cy - 0.08, cy + 0.0, cy + 0.08):
        q.line([(cx - 0.38, ly, 0.202), (cx + 0.38, ly, 0.202)],
               (150, 90, 64), 0.8)


PROPS = {
    "flat-roof-pv-array": {"fn": flat_roof_pv_array,
                           "focus": (0.0, 0.15, 0.16), "k": 420,
                           "plinth": (0.0, 0.15, 0.66, 0.58),
                           "brief": "Cztery pochylone moduły fotowoltaiczne na konstrukcjach balastowych na płaskim dachu"},
    "panel-single": {"fn": panel_single, "focus": (0.0, 0.15, 0.35), "k": 480,
                     "plinth": (0.0, 0.15, 0.72, 0.44),
                     "brief": "single PV module close-up with frame cells and backsheet"},
    "panel-roof": {"fn": panel_roof, "focus": (0.0, 0.15, 0.22), "k": 420,
                   "plinth": (0.0, 0.15, 0.85, 0.50),
                   "brief": "plain rooftop PV module on rails on a flat roof"},
    "rail-set": {"fn": rail_set, "focus": (0.0, 0.15, 0.20), "k": 520,
                "plinth": (0.0, 0.15, 0.70, 0.42),
                "brief": "mounting rail pair with clamps and bolts"},
    "ballast": {"fn": ballast, "focus": (0.0, 0.15, 0.28), "k": 560,
                "plinth": (0.0, 0.15, 0.55, 0.34),
                "brief": "concrete ballast block with rail foot"},
    "optimizer": {"fn": optimizer, "focus": (0.0, 0.15, 0.35), "k": 500,
                  "plinth": (0.0, 0.15, 0.68, 0.42),
                  "brief": "small optimizer box with cables under panel"},
    "monitoring-stick": {"fn": monitoring_stick, "focus": (0.0, 0.15, 0.38), "k": 680,
                         "plinth": (0.0, 0.15, 0.45, 0.28),
                         "brief": "monitoring USB stick with antenna"},
    "earth-rod": {"fn": earth_rod, "focus": (0.0, 0.15, 0.42), "k": 560,
                  "plinth": (0.0, 0.15, 0.50, 0.32),
                  "brief": "earthing rod with clamp and wire"},
    "surge-box": {"fn": surge_box, "focus": (0.0, 0.15, 0.42), "k": 540,
                  "plinth": (0.0, 0.15, 0.52, 0.33),
                  "brief": "surge protection box with switch"},
    "solar-coil": {"fn": solar_coil, "focus": (0.0, 0.15, 0.15), "k": 520,
                   "plinth": (0.0, 0.15, 0.62, 0.38),
                   "brief": "coiled solar cable with MC4 plugs"},
    "roof-hook": {"fn": roof_hook, "focus": (0.0, 0.15, 0.30), "k": 560,
                  "plinth": (0.0, 0.15, 0.55, 0.34),
                  "brief": "stainless roof hook with bolts"},
    "snow-guard": {"fn": snow_guard, "focus": (0.0, 0.15, 0.22), "k": 500,
                   "plinth": (0.0, 0.15, 0.70, 0.42),
                   "brief": "roof snow guard rail section"},
    "bird-guard": {"fn": bird_guard, "focus": (0.0, 0.15, 0.30), "k": 500,
                   "plinth": (0.0, 0.15, 0.68, 0.42),
                   "brief": "mesh bird guard strip"},
    "inverter-string": {"fn": inverter_string, "focus": (0.0, 0.15, 0.42), "k": 520,
                        "plinth": (0.0, 0.15, 0.55, 0.35),
                        "brief": "string inverter with display and glands"},
    "combiner-2": {"fn": combiner_2, "focus": (0.0, 0.15, 0.40), "k": 540,
                   "plinth": (0.0, 0.15, 0.53, 0.34),
                   "brief": "string combiner box with fuses"},
    "cleaning-brush": {"fn": cleaning_brush, "focus": (0.0, 0.15, 0.12), "k": 500,
                       "plinth": (0.0, 0.15, 0.68, 0.42),
                       "brief": "PV cleaning brush with telescopic handle"},
    "tile-plain": {"fn": tile_plain, "focus": (0.0, 0.15, 0.12), "k": 540,
                   "plinth": (0.0, 0.15, 0.62, 0.38),
                   "brief": "plain roof tile with batten"},
}
