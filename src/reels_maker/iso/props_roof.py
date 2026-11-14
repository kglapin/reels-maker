"""Batch roof: roof elements and accessories (187-201). All coords relative."""
from .world import _cylinder


def skylight(q, cx, cy, P):
    """Skylight window: flashing skirt, curb, glass, mullions, sill, handle."""
    # Far/under first: skirt, then curb sunk into it, glass, mullions last.
    q.box((cx - 0.44, cy - 0.32, 0.0), (cx + 0.44, cy + 0.32, 0.10),
          (150, 158, 164), (128, 136, 142), (170, 178, 184))
    q.box((cx - 0.34, cy - 0.24, 0.095), (cx + 0.34, cy + 0.24, 0.34),
          (225, 228, 230), (200, 204, 206), (235, 238, 240))
    q.box((cx - 0.28, cy - 0.18, 0.335), (cx + 0.28, cy + 0.18, 0.375),
          (176, 202, 214), (148, 176, 192), (196, 218, 228))
    # Mullion cross: vertical first, horizontal offset 0.005 in z.
    q.box((cx - 0.025, cy - 0.18, 0.370), (cx + 0.025, cy + 0.18, 0.395),
          (225, 228, 230), (225, 228, 230), (235, 238, 240))
    q.box((cx - 0.28, cy + 0.02, 0.365), (cx + 0.28, cy + 0.06, 0.400),
          (225, 228, 230), (225, 228, 230), (235, 238, 240))
    # Front sill straddles the curb +Y face; handle straddles it too.
    q.box((cx - 0.38, cy + 0.235, 0.095), (cx + 0.38, cy + 0.32, 0.16),
          (200, 204, 206), (180, 184, 186), (214, 218, 220))
    q.box((cx + 0.08, cy + 0.235, 0.18), (cx + 0.18, cy + 0.265, 0.24),
          (120, 128, 134), (120, 128, 134), (140, 148, 154))


def chimney_pot(q, cx, cy, P):
    """Chimney pot: slab, round terracotta pot, band, cap slab, flue."""
    q.box((cx - 0.30, cy - 0.26, 0.0), (cx + 0.30, cy + 0.26, 0.12),
          (168, 172, 176), (144, 148, 152), (188, 192, 196))
    _cylinder(q, cx, cy, 0.115, 0.70, 0.20,
              (170, 112, 94), (120, 70, 58), (186, 130, 110), n=32)
    _cylinder(q, cx, cy, 0.40, 0.46, 0.212,
              (150, 100, 84), (110, 66, 54), (150, 100, 84), n=32)
    # Cap slab surrounds the pot rim; flue mouth sunk into the slab.
    q.box((cx - 0.26, cy - 0.22, 0.745), (cx + 0.26, cy + 0.22, 0.82),
          (178, 182, 186), (154, 158, 162), (198, 202, 206))
    q.box((cx - 0.10, cy - 0.09, 0.815), (cx + 0.10, cy + 0.09, 0.845),
          (62, 66, 70), (62, 66, 70), (62, 66, 70))


def vent_stack(q, cx, cy, P):
    """Vent stack: flashing cone, pipe, collar band, struts, cap disc."""
    _cylinder(q, cx, cy, 0.0, 0.18, 0.26,
              (150, 158, 164), (128, 136, 142), (170, 178, 184), n=32)
    _cylinder(q, cx, cy, 0.17, 0.85, 0.13,
              (178, 186, 190), (140, 148, 152), (192, 200, 204), n=24)
    _cylinder(q, cx, cy, 0.30, 0.36, 0.145,
              (140, 148, 154), (118, 126, 132), (140, 148, 154), n=24)
    # Struts flank the pipe, tops buried in the cap disc.
    q.box((cx + 0.09, cy - 0.03, 0.78), (cx + 0.15, cy + 0.03, 0.905),
          (140, 148, 154), (140, 148, 154), (140, 148, 154))
    q.box((cx - 0.15, cy - 0.03, 0.78), (cx - 0.09, cy + 0.03, 0.905),
          (140, 148, 154), (140, 148, 154), (140, 148, 154))
    q.box((cx - 0.20, cy - 0.17, 0.895), (cx + 0.20, cy + 0.17, 0.96),
          (120, 128, 134), (100, 108, 114), (140, 148, 154))


def gutter_run(q, cx, cy, P):
    """Gutter run: fascia, brackets, channel, water, end caps, outlet."""
    # Far board first, then hangers, channel over them, water/caps last.
    q.box((cx - 0.60, cy - 0.24, 0.30), (cx + 0.60, cy - 0.16, 0.62),
          (168, 158, 144), (146, 138, 126), (186, 176, 162))
    for hx in (cx - 0.40, cx, cx + 0.40):
        q.box((hx - 0.035, cy - 0.16, 0.34), (hx + 0.035, cy + 0.08, 0.40),
              (100, 108, 114), (100, 108, 114), (100, 108, 114))
    q.box((cx - 0.58, cy - 0.10, 0.32), (cx + 0.58, cy + 0.10, 0.50),
          (120, 128, 134), (100, 108, 114), (140, 148, 154))
    q.box((cx - 0.55, cy - 0.07, 0.455), (cx + 0.55, cy + 0.07, 0.485),
          (96, 142, 172), (96, 142, 172), (96, 142, 172))
    for ex in (cx - 0.58, cx + 0.58):
        q.box((ex - 0.035, cy - 0.11, 0.31), (ex + 0.035, cy + 0.11, 0.51),
              (80, 88, 94), (80, 88, 94), (80, 88, 94))
    q.box((cx + 0.30, cy - 0.08, 0.10), (cx + 0.40, cy + 0.02, 0.335),
          (110, 118, 124), (110, 118, 124), (110, 118, 124))


def downpipe(q, cx, cy, P):
    """Downpipe: shoe, barrel, bands, top elbow, inlet stub."""
    # Shoe first (lowest/far), barrel over it, bands and elbow last.
    q.box((cx - 0.07, cy + 0.02, 0.02), (cx + 0.07, cy + 0.24, 0.16),
          (110, 118, 124), (92, 100, 106), (128, 136, 142))
    q.box((cx - 0.07, cy - 0.07, 0.10), (cx + 0.07, cy + 0.07, 1.15),
          (140, 148, 154), (118, 126, 132), (160, 168, 174))
    for z0 in (0.45, 0.80):
        q.box((cx - 0.085, cy - 0.085, z0), (cx + 0.085, cy + 0.085, z0 + 0.05),
              (100, 108, 114), (100, 108, 114), (100, 108, 114))
    q.box((cx - 0.07, cy - 0.20, 1.10), (cx + 0.07, cy + 0.02, 1.24),
          (140, 148, 154), (118, 126, 132), (160, 168, 174))
    q.box((cx - 0.06, cy - 0.32, 1.16), (cx + 0.06, cy - 0.18, 1.28),
          (130, 138, 144), (130, 138, 144), (130, 138, 144))


def antenna(q, cx, cy, P):
    """TV antenna: foot, mast, four element crossarms, tip dot."""
    q.box((cx - 0.14, cy - 0.12, 0.0), (cx + 0.14, cy + 0.12, 0.07),
          (120, 128, 134), (120, 128, 134), (120, 128, 134))
    _cylinder(q, cx, cy, 0.065, 1.55, 0.035,
              (160, 168, 174), (130, 138, 144), (160, 168, 174), n=16)
    # Crossarms mount ON the mast surface (mast r=0.035): two segments
    # per arm from the mast skin outward — never piercing through.
    for w, z0 in ((0.42, 0.90), (0.34, 1.10), (0.26, 1.28), (0.18, 1.42)):
        for sx in (-1, 1):
            xa = cx + sx * 0.033
            xb = cx + sx * w
            lo, hi = min(xa, xb), max(xa, xb)
            q.box((lo, cy - 0.025, z0), (hi, cy + 0.025, z0 + 0.04),
                  (150, 158, 164), (150, 158, 164), (150, 158, 164))
    q.dot((cx, cy, 1.615), 1.0, (180, 70, 60, 255))


def sat_dish(q, cx, cy, P):
    """Satellite dish: foot, pole, collar, stepped bowl, arm, LNB."""
    q.box((cx - 0.16, cy - 0.14, 0.0), (cx + 0.16, cy + 0.14, 0.08),
          (120, 128, 134), (120, 128, 134), (120, 128, 134))
    _cylinder(q, cx, cy, 0.075, 0.70, 0.055,
              (150, 158, 164), (128, 136, 142), (150, 158, 164), n=16)
    _cylinder(q, cx, cy, 0.45, 0.51, 0.07,
              (120, 128, 134), (120, 128, 134), (120, 128, 134), n=16)
    _cylinder(q, cx, cy, 0.70, 0.80, 0.22,
              (225, 228, 230), (205, 208, 210), (235, 238, 240), n=32)
    _cylinder(q, cx, cy, 0.845, 0.90, 0.36,
              (225, 228, 230), (200, 204, 206), (235, 238, 240), n=40)
    q.ground_ellipse(cx, cy, 0.30, 0.30, (168, 172, 176), z=0.955)
    # Feed arm grows out of the bowl, LNB caps the arm end.
    q.box((cx - 0.035, cy + 0.05, 0.88), (cx + 0.035, cy + 0.42, 0.94),
          (140, 148, 154), (140, 148, 154), (140, 148, 154))
    q.box((cx - 0.05, cy + 0.38, 0.86), (cx + 0.05, cy + 0.48, 0.96),
          (90, 98, 104), (90, 98, 104), (90, 98, 104))


def dormer(q, cx, cy, P):
    """Roof dormer: base slab, walls, glass with mullion lines, sill, roof."""
    q.box((cx - 0.50, cy - 0.36, 0.0), (cx + 0.50, cy + 0.36, 0.10),
          (150, 140, 126), (128, 120, 108), (168, 158, 144))
    q.box((cx - 0.30, cy - 0.24, 0.095), (cx + 0.30, cy + 0.24, 0.72),
          (214, 206, 192), (188, 180, 168), (228, 222, 210))
    fy = cy + 0.242
    q.fp(cx - 0.22, cx + 0.22, fy, 0.30, 0.58, (176, 202, 214))
    q.line([(cx, fy + 0.001, 0.29), (cx, fy + 0.001, 0.59)],
           (235, 238, 240), 1.0)
    q.line([(cx - 0.23, fy + 0.001, 0.44), (cx + 0.23, fy + 0.001, 0.44)],
           (235, 238, 240), 1.0)
    # Sill straddles the wall face; roof slab caps the walls.
    q.box((cx - 0.26, cy + 0.235, 0.24), (cx + 0.26, cy + 0.32, 0.30),
          (200, 204, 206), (200, 204, 206), (200, 204, 206))
    q.box((cx - 0.36, cy - 0.28, 0.715), (cx + 0.36, cy + 0.28, 0.80),
          (110, 118, 124), (92, 100, 106), (130, 138, 144))
    q.box((cx - 0.36, cy + 0.275, 0.66), (cx + 0.36, cy + 0.33, 0.74),
          (90, 98, 104), (90, 98, 104), (90, 98, 104))
    q.box((cx - 0.10, cy - 0.28, 0.795), (cx + 0.10, cy + 0.28, 0.85),
          (130, 138, 144), (130, 138, 144), (130, 138, 144))


def ridge_tile(q, cx, cy, P):
    """Ridge tile row: underlay slab, five overlapping tiles, seam caps."""
    q.box((cx - 0.62, cy - 0.14, 0.20), (cx + 0.62, cy + 0.14, 0.30),
          (110, 100, 88), (92, 84, 74), (128, 118, 104))
    shades = [((170, 112, 94), (120, 70, 58), (186, 130, 110)),
              ((160, 104, 88), (112, 66, 54), (178, 122, 102))]
    for i in range(5):
        x0 = cx - 0.55 + i * 0.22
        cl, cd, ct = shades[i % 2]
        q.box((x0, cy - 0.13, 0.295), (x0 + 0.21, cy + 0.13, 0.44),
              cl, cd, ct)
    # Seam caps straddle tile joints, tops above the tile crowns.
    for i in range(4):
        sx = cx - 0.55 + (i + 1) * 0.22 - 0.105
        q.box((sx - 0.018, cy - 0.125, 0.295), (sx + 0.018, cy + 0.135, 0.455),
              (120, 82, 68), (120, 82, 68), (120, 82, 68))


def fascia(q, cx, cy, P):
    """Fascia board: soffit, rafter tails, fascia, drip edge, tile lip."""
    q.box((cx - 0.55, cy - 0.10, 0.42), (cx + 0.55, cy + 0.30, 0.48),
          (214, 210, 202), (192, 188, 180), (226, 222, 214))
    for ix in (cx - 0.375, cx - 0.125, cx + 0.125, cx + 0.375):
        q.box((ix - 0.05, cy - 0.10, 0.475), (ix + 0.05, cy + 0.30, 0.55),
              (168, 158, 144), (146, 138, 126), (186, 176, 162))
    q.box((cx - 0.55, cy + 0.295, 0.30), (cx + 0.55, cy + 0.36, 0.62),
          (150, 140, 126), (128, 120, 108), (168, 158, 144))
    q.box((cx - 0.56, cy + 0.355, 0.56), (cx + 0.56, cy + 0.385, 0.64),
          (100, 108, 114), (100, 108, 114), (100, 108, 114))
    q.box((cx - 0.55, cy - 0.30, 0.615), (cx + 0.55, cy + 0.10, 0.68),
          (170, 112, 94), (170, 112, 94), (170, 112, 94))


def lightning_rod(q, cx, cy, P):
    """Lightning rod: foot, insulator, rod, tip, ground wire with clips."""
    q.box((cx - 0.12, cy - 0.10, 0.0), (cx + 0.12, cy + 0.10, 0.07),
          (120, 128, 134), (120, 128, 134), (120, 128, 134))
    _cylinder(q, cx, cy, 0.065, 0.20, 0.06,
              (226, 222, 210), (200, 196, 184), (236, 232, 222), n=16)
    _cylinder(q, cx, cy, 0.195, 1.45, 0.022,
              (170, 178, 184), (140, 148, 154), (170, 178, 184), n=12)
    q.box((cx - 0.012, cy - 0.012, 1.49), (cx + 0.012, cy + 0.012, 1.62),
          (150, 158, 164), (150, 158, 164), (150, 158, 164))
    q.dot((cx, cy, 1.63), 0.9, (200, 150, 90, 255))
    # Wire runs from the foot along +X with two clip blocks.
    q.box((cx + 0.05, cy - 0.015, 0.015), (cx + 0.45, cy + 0.015, 0.045),
          (130, 138, 144), (130, 138, 144), (130, 138, 144))
    for wx in (cx + 0.20, cx + 0.36):
        q.box((wx - 0.02, cy - 0.025, 0.01), (wx + 0.02, cy + 0.025, 0.05),
              (100, 108, 114), (100, 108, 114), (100, 108, 114))


def pigeon_guard(q, cx, cy, P):
    """Pigeon guard: parapet cap, spike strip, two staggered spike rows."""
    q.box((cx - 0.55, cy - 0.20, 0.0), (cx + 0.55, cy + 0.20, 0.25),
          (178, 182, 186), (154, 158, 162), (198, 202, 206))
    q.box((cx - 0.50, cy - 0.06, 0.245), (cx + 0.50, cy + 0.06, 0.305),
          (110, 118, 124), (110, 118, 124), (110, 118, 124))
    for i in range(14):
        sx = cx - 0.455 + i * 0.07
        top = 0.62 if i % 2 == 0 else 0.55
        q.box((sx - 0.008, cy - 0.043, 0.30), (sx + 0.008, cy - 0.027, top),
              (180, 188, 194), (180, 188, 194), (180, 188, 194))
        q.box((sx - 0.008, cy + 0.027, 0.30), (sx + 0.008, cy + 0.043, top),
              (180, 188, 194), (180, 188, 194), (180, 188, 194))


def roof_blind(q, cx, cy, P):
    """Roof window blind: curb, frame, glass, rails, half-drawn blind."""
    q.box((cx - 0.38, cy - 0.30, 0.0), (cx + 0.38, cy + 0.30, 0.08),
          (150, 158, 164), (128, 136, 142), (170, 178, 184))
    q.box((cx - 0.34, cy - 0.26, 0.06), (cx + 0.34, cy + 0.26, 0.16),
          (225, 228, 230), (200, 204, 206), (235, 238, 240))
    q.box((cx - 0.28, cy - 0.20, 0.155), (cx + 0.28, cy + 0.20, 0.175),
          (176, 202, 214), (176, 202, 214), (176, 202, 214))
    for rx in (cx - 0.30, cx + 0.26):
        q.box((rx, cy - 0.20, 0.155), (rx + 0.04, cy + 0.20, 0.22),
              (200, 204, 206), (200, 204, 206), (200, 204, 206))
    # Blind fabric hangs from the head rail, lower glass left exposed.
    q.box((cx - 0.27, cy - 0.02, 0.170), (cx + 0.27, cy + 0.19, 0.205),
          (140, 170, 200), (140, 170, 200), (140, 170, 200))
    q.box((cx - 0.27, cy - 0.06, 0.20), (cx + 0.27, cy + 0.0, 0.235),
          (110, 130, 160), (110, 130, 160), (110, 130, 160))
    q.line([(cx + 0.20, cy + 0.005, 0.20), (cx + 0.20, cy + 0.005, 0.03)],
           (120, 128, 134), 0.8)


def snow_fence(q, cx, cy, P):
    """Snow fence: bolted feet, capped posts, two rails, ice slats."""
    for px in (cx - 0.40, cx, cx + 0.40):
        q.box((px - 0.08, cy - 0.08, 0.0), (px + 0.08, cy + 0.08, 0.06),
              (120, 128, 134), (120, 128, 134), (120, 128, 134))
        for bx in (px - 0.05, px + 0.05):
            q.dot((bx, cy, 0.065), 0.8, (70, 80, 76, 255))
    for px in (cx - 0.40, cx, cx + 0.40):
        q.box((px - 0.045, cy - 0.045, 0.0), (px + 0.045, cy + 0.045, 0.55),
              (100, 108, 114), (100, 108, 114), (100, 108, 114))
        q.box((px - 0.055, cy - 0.055, 0.545), (px + 0.055, cy + 0.055, 0.60),
              (130, 138, 144), (130, 138, 144), (130, 138, 144))
    for rz in (0.30, 0.45):
        q.box((cx - 0.50, cy - 0.03, rz), (cx + 0.50, cy + 0.03, rz + 0.05),
              (140, 148, 154), (140, 148, 154), (140, 148, 154))
        for px in (cx - 0.40, cx, cx + 0.40):
            q.dot((px, cy + 0.031, rz + 0.025), 0.8, (70, 80, 76, 255))
    sx = cx - 0.34
    j = 0
    while sx <= cx + 0.34:
        tone = (178, 186, 192) if j % 2 == 0 else (168, 176, 182)
        q.box((sx - 0.02, cy - 0.025, 0.345), (sx + 0.02, cy + 0.025, 0.455),
              tone, tone, tone)
        sx += 0.085
        j += 1


def soffit(q, cx, cy, P):
    """Soffit panel: board, joists, front trim, vent grilles, seams."""
    q.box((cx - 0.50, cy - 0.30, 0.40), (cx + 0.50, cy + 0.30, 0.46),
          (222, 224, 218), (200, 202, 196), (232, 234, 228))
    for ix in (cx - 0.375, cx - 0.125, cx + 0.125, cx + 0.375):
        q.box((ix - 0.05, cy - 0.30, 0.455), (ix + 0.05, cy + 0.30, 0.54),
              (168, 158, 144), (146, 138, 126), (186, 176, 162))
    q.box((cx - 0.50, cy + 0.295, 0.34), (cx + 0.50, cy + 0.36, 0.52),
          (150, 140, 126), (128, 120, 108), (168, 158, 144))
    for vx in (cx - 0.30, cx, cx + 0.30):
        q.box((vx - 0.09, cy + 0.355, 0.38), (vx + 0.09, cy + 0.375, 0.46),
              (74, 88, 78), (74, 88, 78), (74, 88, 78))
    for lx in (cx - 0.25, cx, cx + 0.25):
        q.line([(lx, cy - 0.28, 0.462), (lx, cy + 0.28, 0.462)],
               (190, 192, 186), 0.8)


PROPS = {
    "skylight": {"fn": skylight, "focus": (0.0, 0.15, 0.22), "k": 560,
                 "plinth": (0.0, 0.15, 0.60, 0.38),
                 "brief": "roof skylight window with flashing"},
    "chimney-pot": {"fn": chimney_pot, "focus": (0.0, 0.15, 0.46), "k": 490,
                    "plinth": (0.0, 0.15, 0.50, 0.32),
                    "brief": "chimney pot cap"},
    "vent-stack": {"fn": vent_stack, "focus": (0.0, 0.15, 0.50), "k": 480,
                   "plinth": (0.0, 0.15, 0.48, 0.30),
                   "brief": "roof vent stack pipe with cap"},
    "gutter-run": {"fn": gutter_run, "focus": (0.0, 0.10, 0.38), "k": 420,
                   "plinth": (0.0, 0.10, 0.72, 0.34),
                   "brief": "gutter run section with brackets"},
    "downpipe": {"fn": downpipe, "focus": (0.0, 0.05, 0.65), "k": 360,
                 "plinth": (0.0, 0.05, 0.35, 0.26),
                 "brief": "downpipe with elbow and shoe"},
    "antenna": {"fn": antenna, "focus": (0.0, 0.15, 0.84), "k": 320,
                "plinth": (0.0, 0.15, 0.42, 0.28),
                "brief": "TV antenna mast with elements"},
    "sat-dish": {"fn": sat_dish, "focus": (0.0, 0.20, 0.50), "k": 420,
                 "plinth": (0.0, 0.20, 0.55, 0.34),
                 "brief": "satellite dish with arm and mount"},
    "dormer": {"fn": dormer, "focus": (0.0, 0.15, 0.48), "k": 420,
               "plinth": (0.0, 0.15, 0.62, 0.38),
               "brief": "roof dormer with window"},
    "ridge-tile": {"fn": ridge_tile, "focus": (0.0, 0.15, 0.32), "k": 520,
                   "plinth": (0.0, 0.15, 0.72, 0.34),
                   "brief": "ridge tile row section"},
    "fascia": {"fn": fascia, "focus": (0.0, 0.15, 0.48), "k": 470,
               "plinth": (0.0, 0.15, 0.68, 0.36),
               "brief": "fascia board section"},
    "lightning-rod": {"fn": lightning_rod, "focus": (0.0, 0.15, 0.84),
                      "k": 320, "plinth": (0.0, 0.15, 0.40, 0.28),
                      "brief": "lightning rod with wire"},
    "pigeon-guard": {"fn": pigeon_guard, "focus": (0.0, 0.15, 0.32), "k": 520,
                     "plinth": (0.0, 0.15, 0.66, 0.34),
                     "brief": "pigeon guard spike strip"},
    "roof-blind": {"fn": roof_blind, "focus": (0.0, 0.15, 0.15), "k": 560,
                   "plinth": (0.0, 0.15, 0.56, 0.36),
                   "brief": "roof window blind"},
    "snow-fence": {"fn": snow_fence, "focus": (0.0, 0.10, 0.28), "k": 520,
                   "plinth": (0.0, 0.10, 0.62, 0.32),
                   "brief": "roof snow fence section"},
    "soffit": {"fn": soffit, "focus": (0.0, 0.15, 0.44), "k": 520,
               "plinth": (0.0, 0.15, 0.62, 0.38),
               "brief": "soffit panel section with vents"},
}
