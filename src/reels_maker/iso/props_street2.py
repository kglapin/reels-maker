"""Batch street2: street furniture props (172-186). All coords relative."""
import math

from .world import _cylinder

PROPS = {}


def _reg(name, fn, focus, k, plinth, brief):
    PROPS[name] = {"fn": fn, "focus": focus, "k": k, "plinth": plinth,
                   "brief": brief}


def bus_stop(q, cx, cy, P):
    """Bus shelter: rear glass wall, roof slab, bench, sign pole."""
    q.box((cx - 0.55, cy - 0.30, 0.0), (cx + 0.55, cy - 0.26, 1.50),
          (168, 196, 208), (140, 170, 186), (188, 212, 222))
    for px in (cx - 0.52, cx + 0.52):
        q.box((px - 0.03, cy - 0.30, 0.0), (px + 0.03, cy - 0.26, 1.50),
              (90, 104, 94), (90, 104, 94), (90, 104, 94))
    q.box((cx - 0.60, cy - 0.34, 1.495), (cx + 0.60, cy + 0.10, 1.58),
          (110, 126, 114), (110, 126, 114), (110, 126, 114))
    q.box((cx - 0.40, cy - 0.10, 0.415), (cx + 0.40, cy + 0.02, 0.47),
          (150, 120, 88), (120, 96, 70), (170, 140, 104))
    for lx in (cx - 0.35, cx + 0.35):
        q.box((lx - 0.025, cy - 0.08, 0.0), (lx + 0.025, cy + 0.0, 0.42),
              (70, 84, 74), (70, 84, 74), (70, 84, 74))
    _cylinder(q, cx + 0.72, cy + 0.05, 0.0, 1.90, 0.025,
              (110, 124, 114), (110, 124, 114), (110, 124, 114), n=8)
    q.box((cx + 0.62, cy + 0.0, 1.55), (cx + 0.82, cy + 0.10, 1.85),
          (44, 90, 168), (44, 90, 168), (70, 120, 190))
    q.box((cx + 0.66, cy + 0.045, 1.62), (cx + 0.78, cy + 0.055, 1.78),
          (240, 244, 238), (240, 244, 238), (240, 244, 238))


def bench(q, cx, cy, P):
    """Park bench: side frames, seat slats, back slats."""
    for sx in (cx - 0.45, cx + 0.45):
        q.box((sx - 0.04, cy - 0.06, 0.0), (sx + 0.04, cy + 0.06, 0.42),
              (60, 72, 62), (60, 72, 62), (60, 72, 62))
        q.box((sx - 0.04, cy + 0.10, 0.42), (sx + 0.04, cy + 0.20, 0.85),
              (60, 72, 62), (60, 72, 62), (60, 72, 62))
    for j in range(3):
        q.box((cx - 0.50, cy - 0.10 + j * 0.09, 0.415),
              (cx + 0.50, cy - 0.03 + j * 0.09, 0.445),
              (150, 120, 88), (150, 120, 88), (170, 140, 104))
        q.box((cx - 0.50, cy + 0.13, 0.50 + j * 0.14),
              (cx + 0.50, cy + 0.19, 0.53 + j * 0.14),
              (150, 120, 88), (150, 120, 88), (170, 140, 104))


def trash_bin(q, cx, cy, P):
    """Street bin: tapered body, rim, lid, dark opening."""
    q.box((cx - 0.16, cy - 0.16, 0.0), (cx + 0.16, cy + 0.16, 0.06),
          (60, 72, 62), (60, 72, 62), (60, 72, 62))
    q.box((cx - 0.14, cy - 0.14, 0.055), (cx + 0.14, cy + 0.14, 0.55),
          (88, 102, 88), (66, 80, 66), (108, 122, 108))
    q.box((cx - 0.155, cy - 0.155, 0.545), (cx + 0.155, cy + 0.155, 0.60),
          (70, 84, 74), (70, 84, 74), (70, 84, 74))
    q.box((cx - 0.13, cy - 0.13, 0.595), (cx + 0.13, cy + 0.13, 0.68),
          (60, 72, 62), (60, 72, 62), (60, 72, 62))
    q.fp(cx - 0.09, cx + 0.09, cy + 0.143, 0.38, 0.48, (20, 26, 22))


def bike_rack(q, cx, cy, P):
    """Bike rack: ground rail with three inverted-U hoops."""
    q.box((cx - 0.45, cy - 0.04, 0.0), (cx + 0.45, cy + 0.04, 0.05),
          (100, 114, 102), (100, 114, 102), (100, 114, 102))
    for hx in (cx - 0.40, cx, cx + 0.40):
        q.box((hx - 0.025, cy - 0.025, 0.045), (hx + 0.025, cy + 0.025, 0.55),
              (140, 154, 142), (140, 154, 142), (140, 154, 142))
        q.box((hx + 0.30 - 0.025, cy - 0.025, 0.045),
              (hx + 0.30 + 0.025, cy + 0.025, 0.55),
              (140, 154, 142), (140, 154, 142), (140, 154, 142))
        q.box((hx - 0.025, cy - 0.025, 0.525), (hx + 0.325, cy + 0.025, 0.575),
              (140, 154, 142), (140, 154, 142), (140, 154, 142))


def fast_charger(q, cx, cy, P):
    """DC fast charger: pillar, screen, cable holsters, base."""
    q.box((cx - 0.16, cy - 0.12, 0.0), (cx + 0.16, cy + 0.12, 0.08),
          (70, 84, 74), (70, 84, 74), (70, 84, 74))
    q.box((cx - 0.13, cy - 0.09, 0.075), (cx + 0.13, cy + 0.09, 1.05),
          (52, 66, 56), (38, 50, 42), (72, 86, 76))
    q.fp(cx - 0.08, cx + 0.08, cy + 0.093, 0.70, 0.92, (22, 34, 30))
    q.fp(cx - 0.06, cx + 0.0, cy + 0.095, 0.74, 0.80, (110, 190, 170))
    q.fp(cx + 0.02, cx + 0.06, cy + 0.095, 0.74, 0.88, (220, 150, 60))
    for sx in (cx - 0.155, cx + 0.115):
        q.box((sx - 0.02, cy + 0.06, 0.30), (sx + 0.02, cy + 0.10, 0.60),
              (40, 52, 44), (40, 52, 44), (40, 52, 44))
    q.dot((cx - 0.155, cy + 0.103, 0.62), 1.0, (110, 190, 170, 255))
    # Charging cable: thick U-loop hanging off the +Y face, rooted INSIDE
    # the right holster and plugged back into the pillar (painted last).
    # No dip below plug level (was z=0.13, read as ending mid-air).
    q.line([(cx + 0.115, cy + 0.08, 0.52), (cx + 0.23, cy + 0.105, 0.32)],
           (28, 34, 30), 2.5)
    q.line([(cx + 0.23, cy + 0.105, 0.32), (cx + 0.20, cy + 0.105, 0.20)],
           (28, 34, 30), 2.5)
    q.line([(cx + 0.20, cy + 0.105, 0.20), (cx + 0.08, cy + 0.105, 0.17)],
           (28, 34, 30), 2.5)
    # Plug handle docked low on the pillar face where the loop returns.
    q.box((cx + 0.02, cy + 0.085, 0.16), (cx + 0.10, cy + 0.115, 0.30),
          (52, 64, 56), (40, 50, 44), (70, 84, 72))
    q.box((cx + 0.035, cy + 0.10, 0.26), (cx + 0.085, cy + 0.118, 0.30),
          (110, 190, 170), (110, 190, 170), (110, 190, 170))


def parking_sign(q, cx, cy, P):
    """Parking sign: pole, blue square, white bar."""
    _cylinder(q, cx, cy, 0.0, 1.70, 0.028,
              (120, 134, 122), (120, 134, 122), (120, 134, 122), n=10)
    q.box((cx - 0.03, cy - 0.03, 0.0), (cx + 0.03, cy + 0.03, 0.06),
          (90, 104, 92), (90, 104, 92), (90, 104, 92))
    q.box((cx - 0.22, cy - 0.02, 1.10), (cx + 0.22, cy + 0.06, 1.54),
          (44, 90, 168), (36, 74, 140), (60, 110, 185))
    q.box((cx - 0.14, cy + 0.062, 1.24), (cx + 0.14, cy + 0.075, 1.40),
          (240, 244, 238), (240, 244, 238), (240, 244, 238))


def street_sign(q, cx, cy, P):
    """Street name sign: pole with horizontal plate and bars."""
    _cylinder(q, cx, cy, 0.0, 1.80, 0.028,
              (120, 134, 122), (120, 134, 122), (120, 134, 122), n=10)
    q.box((cx - 0.03, cy - 0.03, 0.0), (cx + 0.03, cy + 0.03, 0.06),
          (90, 104, 92), (90, 104, 92), (90, 104, 92))
    q.box((cx - 0.40, cy - 0.02, 1.45), (cx + 0.40, cy + 0.04, 1.65),
          (238, 242, 236), (200, 210, 200), (248, 250, 246))
    q.box((cx - 0.34, cy + 0.045, 1.51), (cx + 0.10, cy + 0.055, 1.59),
          (90, 130, 110), (90, 130, 110), (90, 130, 110))


def hydrant(q, cx, cy, P):
    """Fire hydrant, dressed: bolted flange, waist band, 3 capped
    nozzles with chains, stepped ribbed dome, top nut (visual-plan)."""
    # Muted brick red (was neon signal red; both corpus judges
    # flagged the palette violation — corpus gate 2026-11-12).
    RED_L = (150, 44, 38)
    RED_D = (114, 32, 28)
    RED_T = (170, 54, 44)
    DARK = (92, 30, 26)
    STEEL = (170, 176, 182)
    CHAIN = (150, 156, 162)
    # Mouth seals FIRST (call-order painter): flat discs sealing every
    # open tube mouth before any staves paint over them. Safe ONLY
    # because a later solid covers each disc's center (upper step,
    # barrel, nut) — a free disc center would blob over the wall.
    # Without these, stacked open tubes show see-through slits.
    for _rz, _rr in ((0.12, 0.15), (0.24, 0.105), (0.55, 0.10),
                     (0.60, 0.13), (0.63, 0.105), (0.66, 0.095),
                     (0.69, 0.075)):
        q.ground_ellipse(cx, cy, _rr, _rr, RED_T, z=_rz)
    q.box((cx - 0.13, cy - 0.13, 0.0), (cx + 0.13, cy + 0.13, 0.06),
          RED_D, RED_D, RED_D)
    _cylinder(q, cx, cy, 0.05, 0.12, 0.15,
              RED_L, RED_D, RED_T, rim=False, top_ring=False, n=24)
    for deg in (30, 90, 150, 210, 270, 330):
        a = math.radians(deg)
        bx, by = cx + 0.125 * math.cos(a), cy + 0.125 * math.sin(a)
        q.box((bx - 0.012, by - 0.012, 0.115), (bx + 0.012, by + 0.012, 0.15),
              STEEL, STEEL, STEEL)
    _cylinder(q, cx, cy, 0.10, 0.55, 0.10,
              RED_L, RED_D, RED_T, rim=False, top_ring=False, n=24)
    _cylinder(q, cx, cy, 0.115, 0.24, 0.105,
              DARK, DARK, DARK, rim=False, top_ring=False, n=24)
    # Waist bolts REMOVED (were white floaters on the bare barrel;
    # detail law: bolts ONLY on flanges — corpus gate 2026-11-12).
    for sx in (cx - 0.105, cx + 0.105):
        q.box((sx - 0.035, cy - 0.035, 0.26), (sx + 0.035, cy + 0.035, 0.36),
              RED_T, RED_T, RED_T)
        q.box((sx - 0.058, cy - 0.058, 0.30), (sx + 0.058, cy + 0.058, 0.335),
              RED_T, RED_T, RED_T)
        for sz in (0.285, 0.305):
            q.line([(sx + 0.036, cy - 0.035, sz),
                    (sx + 0.036, cy + 0.035, sz)], DARK, 1.0)
            q.line([(sx - 0.035, cy + 0.036, sz),
                    (sx + 0.035, cy + 0.036, sz)], DARK, 1.0)
    q.box((cx - 0.055, cy + 0.06, 0.20), (cx + 0.055, cy + 0.21, 0.33),
          RED_T, RED_T, RED_T)
    q.box((cx - 0.075, cy + 0.08, 0.26), (cx + 0.075, cy + 0.225, 0.30),
          RED_T, RED_T, RED_T)
    for sz in (0.265, 0.285):
        q.line([(cx - 0.055, cy + 0.226, sz), (cx + 0.055, cy + 0.226, sz)],
               DARK, 1.0)
        q.line([(cx + 0.076, cy + 0.08, sz), (cx + 0.076, cy + 0.21, sz)],
               DARK, 1.0)
    q.box((cx - 0.02, cy + 0.208, 0.255), (cx + 0.02, cy + 0.228, 0.28),
          STEEL, STEEL, STEEL)
    _cylinder(q, cx, cy, 0.545, 0.60, 0.13,
              RED_L, RED_D, RED_T, rim=False, top_ring=False, n=24)
    _cylinder(q, cx, cy, 0.59, 0.63, 0.105,
              RED_L, RED_D, RED_T, rim=False, top_ring=False, n=24)
    _cylinder(q, cx, cy, 0.62, 0.66, 0.095,
              RED_L, RED_D, RED_T, rim=False, top_ring=False, n=24)
    _cylinder(q, cx, cy, 0.65, 0.69, 0.075,
              RED_L, RED_D, RED_T, rim=False, top_ring=False, n=24)
    q.box((cx - 0.02, cy - 0.02, 0.685), (cx + 0.02, cy + 0.02, 0.75),
          STEEL, STEEL, STEEL)


def bollard(q, cx, cy, P):
    """Protective bollard: post with reflective band and cap."""
    q.box((cx - 0.07, cy - 0.07, 0.0), (cx + 0.07, cy + 0.07, 0.04),
          (80, 94, 82), (80, 94, 82), (80, 94, 82))
    q.box((cx - 0.055, cy - 0.055, 0.035), (cx + 0.055, cy + 0.055, 0.62),
          (90, 104, 92), (70, 84, 72), (110, 124, 112))
    q.box((cx - 0.058, cy - 0.058, 0.40), (cx + 0.058, cy + 0.058, 0.50),
          (220, 225, 215), (220, 225, 215), (220, 225, 215))
    q.box((cx - 0.06, cy - 0.06, 0.615), (cx + 0.06, cy + 0.06, 0.66),
          (70, 84, 72), (70, 84, 72), (70, 84, 72))


def barrier(q, cx, cy, P):
    """Boom barrier: post, striped boom, base."""
    q.box((cx - 0.12, cy - 0.12, 0.0), (cx + 0.12, cy + 0.12, 0.08),
          (80, 94, 82), (80, 94, 82), (80, 94, 82))
    q.box((cx - 0.09, cy - 0.09, 0.075), (cx + 0.09, cy + 0.09, 0.85),
          (200, 206, 198), (170, 180, 172), (215, 220, 212))
    for j in range(5):
        col = (200, 62, 52) if j % 2 == 0 else (240, 244, 238)
        q.box((cx + 0.09 + j * 0.16, cy - 0.035, 0.68),
              (cx + 0.09 + (j + 1) * 0.16, cy + 0.035, 0.78), col, col, col)
    q.dot((cx, cy + 0.093, 0.72), 1.0, (220, 150, 60, 255))


def traffic_cone(q, cx, cy, P):
    """Traffic cone: stacked tapering boxes, band, base."""
    q.box((cx - 0.16, cy - 0.16, 0.0), (cx + 0.16, cy + 0.16, 0.05),
          (200, 100, 60), (170, 84, 52), (215, 120, 75))
    q.box((cx - 0.11, cy - 0.11, 0.045), (cx + 0.11, cy + 0.11, 0.30),
          (200, 100, 60), (170, 84, 52), (215, 120, 75))
    q.box((cx - 0.115, cy - 0.115, 0.24), (cx + 0.115, cy + 0.115, 0.33),
          (240, 244, 238), (240, 244, 238), (240, 244, 238))
    q.box((cx - 0.07, cy - 0.07, 0.295), (cx + 0.07, cy + 0.07, 0.52),
          (200, 100, 60), (170, 84, 52), (215, 120, 75))


def road_sign(q, cx, cy, P):
    """Triangular road sign: pole, plate from offset triangles, bar."""
    _cylinder(q, cx, cy, 0.0, 1.50, 0.028,
              (120, 134, 122), (120, 134, 122), (120, 134, 122), n=10)
    q.box((cx - 0.03, cy - 0.03, 0.0), (cx + 0.03, cy + 0.03, 0.06),
          (90, 104, 92), (90, 104, 92), (90, 104, 92))
    ux, uy, uz = cx, cy + 0.03, 1.05
    q.poly([(ux - 0.26, uy, uz), (ux + 0.26, uy, uz), (ux, uy, uz + 0.44)],
           (200, 62, 52))
    q.poly([(ux - 0.18, uy + 0.002, uz + 0.05), (ux + 0.18, uy + 0.002, uz + 0.05),
            (ux, uy + 0.002, uz + 0.33)], (240, 244, 238))
    q.box((ux - 0.03, uy - 0.02, uz - 0.35), (ux + 0.03, uy + 0.06, uz + 0.02),
          (120, 134, 122), (120, 134, 122), (120, 134, 122))


def fountain(q, cx, cy, P):
    """Square fountain: basin, rim, column, bowl, jet."""
    q.box((cx - 0.42, cy - 0.42, 0.0), (cx + 0.42, cy + 0.42, 0.30),
          (168, 182, 170), (140, 156, 144), (150, 164, 152))
    q.box((cx - 0.46, cy - 0.46, 0.295), (cx + 0.46, cy + 0.46, 0.36),
          (150, 164, 152), (150, 164, 152), (150, 164, 152))
    q.box((cx - 0.36, cy - 0.36, 0.295), (cx + 0.36, cy + 0.36, 0.33),
          (90, 150, 175), (90, 150, 175), (90, 150, 175))
    _cylinder(q, cx, cy, 0.30, 0.75, 0.07,
              (150, 164, 152), (150, 164, 152), (150, 164, 152), n=12)
    q.ground_ellipse(cx, cy, 0.16, 0.16, (150, 164, 152), z=0.75)
    q.ground_ellipse(cx, cy, 0.10, 0.10, (170, 182, 174), z=0.78)
    _cylinder(q, cx, cy, 0.78, 1.05, 0.018,
              (170, 215, 230), (170, 215, 230), (200, 230, 240), n=8)
    q.dot((cx, cy, 1.06), 1.2, (220, 240, 246, 255))


def kiosk(q, cx, cy, P):
    """Kiosk booth, dressed: front sign band on brackets, framed counter
    with shelf, side door, corner trims, kick plate, awning arms."""
    TRIM = (160, 134, 98)
    DARK = (56, 66, 58)
    q.box((cx - 0.35, cy - 0.30, 0.0), (cx + 0.35, cy + 0.30, 0.06),
          (120, 134, 122), (120, 134, 122), (120, 134, 122))
    q.box((cx - 0.32, cy - 0.27, 0.055), (cx + 0.32, cy + 0.27, 1.15),
          (206, 178, 132), (178, 152, 112), (222, 196, 152))
    for tx in (cx - 0.32, cx + 0.32):
        for ty in (cy - 0.27, cy + 0.27):
            q.box((tx - 0.02, ty - 0.02, 0.055), (tx + 0.02, ty + 0.02, 1.15),
                  TRIM, TRIM, TRIM)
    q.box((cx - 0.32, cy + 0.265, 0.055), (cx + 0.32, cy + 0.28, 0.18),
          DARK, DARK, DARK)
    q.box((cx + 0.315, cy - 0.10, 0.055), (cx + 0.325, cy + 0.10, 0.90),
          DARK, DARK, DARK)
    q.box((cx + 0.322, cy + 0.02, 0.45), (cx + 0.335, cy + 0.06, 0.55),
          (150, 158, 164), (150, 158, 164), (150, 158, 164))
    q.box((cx - 0.38, cy - 0.10, 1.145), (cx + 0.38, cy + 0.42, 1.22),
          (150, 60, 52), (150, 60, 52), (170, 80, 68))
    for ax in (cx - 0.30, cx + 0.30):
        q.box((ax - 0.025, cy + 0.265, 1.10), (ax + 0.025, cy + 0.42, 1.15),
              TRIM, TRIM, TRIM)
    q.box((cx - 0.28, cy + 0.265, 0.55), (cx + 0.28, cy + 0.275, 0.95),
          (40, 52, 44), (40, 52, 44), (40, 52, 44))
    q.box((cx - 0.28, cy + 0.263, 0.72), (cx + 0.28, cy + 0.277, 0.75),
          (62, 74, 66), (62, 74, 66), (62, 74, 66))
    q.box((cx - 0.30, cy + 0.24, 0.52), (cx + 0.30, cy + 0.29, 0.555),
          (150, 178, 160), (150, 178, 160), (150, 178, 160))
    for sx in (cx - 0.26, cx + 0.26):
        q.box((sx - 0.03, cy + 0.265, 0.93), (sx + 0.03, cy + 0.33, 0.985),
              TRIM, TRIM, TRIM)
    q.box((cx - 0.30, cy + 0.265, 0.98), (cx + 0.30, cy + 0.335, 1.08),
          (240, 244, 238), (240, 244, 238), (240, 244, 238))


def lamp_post_2(q, cx, cy, P):
    """Park lamp post: base, pole, arm, lantern with warm glass."""
    q.box((cx - 0.08, cy - 0.08, 0.0), (cx + 0.08, cy + 0.08, 0.10),
          (70, 84, 74), (70, 84, 74), (70, 84, 74))
    _cylinder(q, cx, cy, 0.095, 1.90, 0.032,
              (70, 84, 74), (70, 84, 74), (70, 84, 74), n=10)
    q.box((cx - 0.03, cy + 0.0, 1.82), (cx + 0.03, cy + 0.30, 1.88),
          (70, 84, 74), (70, 84, 74), (70, 84, 74))
    q.box((cx - 0.09, cy + 0.24, 1.70), (cx + 0.09, cy + 0.36, 1.76),
          (50, 60, 52), (50, 60, 52), (50, 60, 52))
    q.box((cx - 0.06, cy + 0.27, 1.60), (cx + 0.06, cy + 0.33, 1.705),
          (250, 200, 130), (250, 200, 130), (250, 200, 130))
    q.dot((cx, cy + 0.303, 1.65), 1.0, (255, 220, 150, 255))


_reg("bus-stop", bus_stop, (0.0, 0.15, 0.75), 250, (0.0, 0.15, 0.95, 0.55),
     "Bus stop shelter with glass rear wall, roof, bench and sign pole")
_reg("bench", bench, (0.0, 0.15, 0.42), 480, (0.0, 0.15, 0.62, 0.36),
     "Park bench with slatted seat and backrest on side frames")
_reg("trash-bin", trash_bin, (0.0, 0.15, 0.34), 550, (0.0, 0.15, 0.40, 0.30),
     "Street trash bin with rim, lid and dark opening")
_reg("bike-rack", bike_rack, (0.0, 0.15, 0.28), 400, (0.0, 0.15, 0.60, 0.32),
     "Bike rack: three inverted-U hoops on a ground rail")
_reg("fast-charger", fast_charger, (0.0, 0.15, 0.52), 480, (0.0, 0.15, 0.45, 0.32),
     "DC fast charger pillar with screen, cable holsters and base")
_reg("parking-sign", parking_sign, (0.0, 0.15, 0.82), 330, (0.0, 0.15, 0.30, 0.22),
     "Parking sign: pole with blue square and white bar")
_reg("street-sign", street_sign, (0.0, 0.15, 0.90), 330, (0.0, 0.15, 0.30, 0.22),
     "Street name sign on pole with plate and bars")
_reg("hydrant", hydrant, (0.0, 0.15, 0.35), 550, (0.0, 0.15, 0.40, 0.30),
     "Fire hydrant with barrel, dome, top nut and side nozzles")
_reg("bollard", bollard, (0.0, 0.15, 0.33), 550, (0.0, 0.15, 0.35, 0.28),
     "Protective bollard with reflective band and cap")
_reg("barrier", barrier, (0.3, 0.15, 0.42), 420, (0.35, 0.15, 0.75, 0.34),
     "Boom barrier with striped arm and base")
_reg("traffic-cone", traffic_cone, (0.0, 0.15, 0.26), 550, (0.0, 0.15, 0.35, 0.28),
     "Traffic cone with reflective band on base")
_reg("road-sign", road_sign, (0.0, 0.15, 0.66), 330, (0.0, 0.15, 0.30, 0.22),
     "Triangular road sign on pole with mounting bracket")
_reg("fountain", fountain, (0.0, 0.15, 0.50), 380, (0.0, 0.15, 0.62, 0.42),
     "Square fountain with basin, column, bowl and water jet")
_reg("kiosk", kiosk, (0.0, 0.15, 0.60), 380, (0.0, 0.15, 0.60, 0.40),
     "Kiosk booth with awning, counter opening and sign band")
_reg("lamp-post-2", lamp_post_2, (0.0, 0.15, 0.99), 330, (0.0, 0.15, 0.30, 0.22),
     "Park lamp post with arm and warm lantern glass")
