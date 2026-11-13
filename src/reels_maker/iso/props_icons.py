"""Batch icons: minimalist iso pictograms (202-216). All coords relative."""
import math

from .world import _cylinder

PROPS = {}


def _reg(name, fn, focus, k, plinth, brief):
    PROPS[name] = {"fn": fn, "focus": focus, "k": k, "plinth": plinth,
                   "brief": brief}


def icon_sun(q, cx, cy, P):
    """Sun pictogram: disc, four arms, four diagonal dots."""
    _cylinder(q, cx, cy, 0.30, 0.38, 0.22,
              (240, 180, 60), (240, 180, 60), (245, 190, 70), n=32)
    q.box((cx - 0.44, cy - 0.05, 0.30), (cx + 0.44, cy + 0.05, 0.38),
          (240, 180, 60), (240, 180, 60), (240, 180, 60))
    q.box((cx - 0.05, cy - 0.44, 0.295), (cx + 0.05, cy + 0.44, 0.375),
          (240, 180, 60), (240, 180, 60), (240, 180, 60))
    for sx in (-0.198, 0.198):
        for sy in (-0.198, 0.198):
            q.box((cx + sx - 0.06, cy + sy - 0.06, 0.295),
                  (cx + sx + 0.06, cy + sy + 0.06, 0.40),
                  (240, 180, 60), (240, 180, 60), (240, 180, 60))


def icon_drop(q, cx, cy, P):
    """Water drop pictogram: base cylinder, stepped cone tip."""
    _cylinder(q, cx, cy, 0.10, 0.35, 0.20,
              (80, 140, 190), (80, 140, 190), (90, 150, 200), n=32)
    _cylinder(q, cx, cy, 0.345, 0.47, 0.15,
              (80, 140, 190), (80, 140, 190), (90, 150, 200), n=24)
    _cylinder(q, cx, cy, 0.465, 0.58, 0.10,
              (80, 140, 190), (80, 140, 190), (90, 150, 200), n=20)
    _cylinder(q, cx, cy, 0.575, 0.68, 0.05,
              (90, 150, 200), (90, 150, 200), (100, 160, 210), n=16)


def icon_flame(q, cx, cy, P):
    """Flame pictogram: three stacked shrinking tiers, yellow core."""
    _cylinder(q, cx, cy, 0.05, 0.30, 0.22,
              (220, 100, 50), (220, 100, 50), (228, 110, 60), n=32)
    _cylinder(q, cx, cy, 0.28, 0.52, 0.15,
              (230, 140, 60), (230, 140, 60), (236, 150, 70), n=24)
    _cylinder(q, cx, cy, 0.50, 0.70, 0.08,
              (240, 190, 80), (240, 190, 80), (245, 200, 90), n=20)


def icon_bolt(q, cx, cy, P):
    """Lightning pictogram: four stepped zigzag segments."""
    q.box((cx - 0.15, cy - 0.10, 0.60), (cx + 0.15, cy + 0.10, 0.75),
          (240, 190, 60), (240, 190, 60), (240, 190, 60))
    q.box((cx - 0.15, cy - 0.10, 0.42), (cx + 0.05, cy + 0.10, 0.62),
          (240, 190, 60), (240, 190, 60), (240, 190, 60))
    q.box((cx - 0.05, cy - 0.10, 0.24), (cx + 0.15, cy + 0.10, 0.44),
          (240, 190, 60), (240, 190, 60), (240, 190, 60))
    q.box((cx - 0.05, cy - 0.10, 0.05), (cx + 0.05, cy + 0.10, 0.26),
          (240, 190, 60), (240, 190, 60), (240, 190, 60))


def icon_snowflake(q, cx, cy, P):
    """Snowflake pictogram: crossed bars, hub, diagonal dots."""
    q.box((cx - 0.40, cy - 0.06, 0.30), (cx + 0.40, cy + 0.06, 0.40),
          (170, 200, 220), (170, 200, 220), (170, 200, 220))
    q.box((cx - 0.06, cy - 0.40, 0.295), (cx + 0.06, cy + 0.40, 0.395),
          (170, 200, 220), (170, 200, 220), (170, 200, 220))
    _cylinder(q, cx, cy, 0.29, 0.41, 0.12,
              (190, 215, 230), (190, 215, 230), (190, 215, 230), n=20)
    for sx in (-0.141, 0.141):
        for sy in (-0.141, 0.141):
            q.box((cx + sx - 0.06, cy + sy - 0.06, 0.30),
                  (cx + sx + 0.06, cy + sy + 0.06, 0.40),
                  (170, 200, 220), (170, 200, 220), (170, 200, 220))


def icon_thermometer(q, cx, cy, P):
    """Thermometer pictogram: tube, bulb, mercury, scale ticks."""
    _cylinder(q, cx, cy, 0.10, 0.26, 0.14,
              (200, 210, 215), (200, 210, 215), (205, 215, 220), n=24)
    q.box((cx - 0.08, cy - 0.08, 0.24), (cx + 0.08, cy + 0.08, 0.75),
          (215, 222, 226), (215, 222, 226), (215, 222, 226))
    q.box((cx - 0.04, cy - 0.04, 0.14), (cx + 0.04, cy + 0.04, 0.60),
          (200, 70, 60), (200, 70, 60), (200, 70, 60))
    for z0 in (0.40, 0.50, 0.60):
        q.box((cx - 0.08, cy + 0.075, z0), (cx + 0.02, cy + 0.11, z0 + 0.04),
              (120, 130, 136), (120, 130, 136), (120, 130, 136))


def icon_gauge(q, cx, cy, P):
    """Pressure gauge pictogram: stem, dial face, rim, needle."""
    q.box((cx - 0.10, cy - 0.10, 0.05), (cx + 0.10, cy + 0.10, 0.30),
          (130, 138, 144), (130, 138, 144), (130, 138, 144))
    _cylinder(q, cx, cy, 0.28, 0.38, 0.28,
              (225, 228, 230), (225, 228, 230), (225, 228, 230), n=40)
    _cylinder(q, cx, cy, 0.275, 0.385, 0.285,
              (110, 118, 124), (110, 118, 124), (110, 118, 124), n=40)
    q.box((cx - 0.02, cy - 0.035, 0.375), (cx + 0.20, cy + 0.035, 0.40),
          (200, 70, 60), (200, 70, 60), (200, 70, 60))
    _cylinder(q, cx, cy, 0.375, 0.41, 0.05,
              (90, 98, 104), (90, 98, 104), (90, 98, 104), n=16)


def icon_battery(q, cx, cy, P):
    """Battery pictogram: body, nub, three charge bars."""
    q.box((cx - 0.30, cy - 0.15, 0.10), (cx + 0.30, cy + 0.15, 0.50),
          (110, 150, 90), (92, 128, 76), (128, 168, 106))
    q.box((cx - 0.08, cy - 0.08, 0.495), (cx + 0.08, cy + 0.08, 0.60),
          (110, 150, 90), (110, 150, 90), (110, 150, 90))
    for z0 in (0.18, 0.28, 0.38):
        q.box((cx - 0.20, cy + 0.145, z0), (cx + 0.20, cy + 0.165, z0 + 0.06),
              (60, 110, 60), (60, 110, 60), (60, 110, 60))


def icon_house(q, cx, cy, P):
    """House pictogram: walls, stepped pyramid roof, door, window."""
    q.box((cx - 0.28, cy - 0.22, 0.05), (cx + 0.28, cy + 0.22, 0.45),
          (214, 206, 192), (188, 180, 168), (228, 222, 210))
    q.box((cx - 0.32, cy - 0.26, 0.44), (cx + 0.32, cy + 0.26, 0.54),
          (150, 90, 70), (126, 74, 58), (170, 108, 86))
    q.box((cx - 0.20, cy - 0.15, 0.535), (cx + 0.20, cy + 0.15, 0.66),
          (150, 90, 70), (126, 74, 58), (170, 108, 86))
    q.box((cx - 0.07, cy + 0.215, 0.10), (cx + 0.07, cy + 0.23, 0.32),
          (110, 90, 70), (110, 90, 70), (110, 90, 70))
    q.box((cx + 0.10, cy + 0.215, 0.22), (cx + 0.22, cy + 0.23, 0.36),
          (176, 202, 214), (176, 202, 214), (176, 202, 214))


def icon_factory(q, cx, cy, P):
    """Factory pictogram: hall, window band, door, two chimneys."""
    q.box((cx - 0.40, cy - 0.25, 0.05), (cx + 0.40, cy + 0.25, 0.40),
          (160, 168, 174), (138, 146, 152), (180, 188, 194))
    q.box((cx - 0.40, cy - 0.25, 0.395), (cx + 0.40, cy + 0.25, 0.46),
          (110, 118, 124), (110, 118, 124), (110, 118, 124))
    q.box((cx - 0.32, cy + 0.245, 0.16), (cx + 0.32, cy + 0.26, 0.30),
          (176, 202, 214), (176, 202, 214), (176, 202, 214))
    q.box((cx - 0.08, cy + 0.245, 0.05), (cx + 0.08, cy + 0.26, 0.22),
          (90, 98, 104), (90, 98, 104), (90, 98, 104))
    for chx in (cx - 0.22, cx + 0.22):
        _cylinder(q, chx, cy - 0.05, 0.455, 0.75, 0.07,
                  (140, 148, 154), (140, 148, 154), (140, 148, 154), n=16)


def icon_panel(q, cx, cy, P):
    """PV panel pictogram: framed panel, grid lines, two legs."""
    for lx in (cx - 0.25, cx + 0.25):
        q.box((lx - 0.04, cy - 0.04, 0.0), (lx + 0.04, cy + 0.04, 0.30),
              (130, 138, 144), (130, 138, 144), (130, 138, 144))
    q.box((cx - 0.36, cy - 0.26, 0.28), (cx + 0.36, cy + 0.26, 0.38),
          (60, 110, 160), (48, 92, 136), (72, 128, 184))
    q.box((cx - 0.38, cy - 0.28, 0.27), (cx + 0.38, cy + 0.28, 0.315),
          (200, 204, 206), (200, 204, 206), (200, 204, 206))
    q.box((cx - 0.015, cy - 0.26, 0.37), (cx + 0.015, cy + 0.26, 0.38),
          (200, 204, 206), (200, 204, 206), (200, 204, 206))
    q.box((cx - 0.36, cy - 0.015, 0.375), (cx + 0.36, cy + 0.015, 0.385),
          (200, 204, 206), (200, 204, 206), (200, 204, 206))


def icon_tank(q, cx, cy, P):
    """Buffer tank pictogram: vessel, cap, bands, gauge dot."""
    _cylinder(q, cx, cy, 0.05, 0.55, 0.25,
              (150, 170, 200), (150, 170, 200), (160, 180, 208), n=32)
    _cylinder(q, cx, cy, 0.545, 0.64, 0.12,
              (130, 138, 144), (130, 138, 144), (130, 138, 144), n=20)
    for z0 in (0.18, 0.36):
        _cylinder(q, cx, cy, z0, z0 + 0.05, 0.255,
                  (110, 118, 124), (110, 118, 124), (110, 118, 124), n=32)
    q.box((cx - 0.05, cy + 0.245, 0.30), (cx + 0.05, cy + 0.265, 0.42),
          (225, 228, 230), (225, 228, 230), (225, 228, 230))


def icon_valve(q, cx, cy, P):
    """Valve pictogram: pipe run, bonnet, handwheel disc."""
    # Pedestal grounding the pipe into the plinth (was floating 0.375
    # over it — corpus gate 2026-11-12).
    q.box((cx - 0.06, cy - 0.06, -0.16), (cx + 0.06, cy + 0.06, 0.27),
          (130, 138, 144), (130, 138, 144), (130, 138, 144))
    q.box((cx - 0.35, cy - 0.08, 0.25), (cx + 0.35, cy + 0.08, 0.41),
          (150, 158, 164), (150, 158, 164), (150, 158, 164))
    _cylinder(q, cx, cy, 0.40, 0.60, 0.09,
              (180, 70, 60), (180, 70, 60), (180, 70, 60), n=20)
    _cylinder(q, cx, cy, 0.595, 0.66, 0.16,
              (180, 70, 60), (180, 70, 60), (180, 70, 60), n=24)


def icon_fan(q, cx, cy, P):
    """Fan pictogram: stand, ring, hub, four blades."""
    q.box((cx - 0.10, cy - 0.08, 0.0), (cx + 0.10, cy + 0.08, 0.28),
          (130, 138, 144), (130, 138, 144), (130, 138, 144))
    _cylinder(q, cx, cy - 0.02, 0.25, 0.33, 0.30,
              (140, 148, 154), (140, 148, 154), (140, 148, 154), n=40)
    q.box((cx - 0.26, cy - 0.09, 0.26), (cx + 0.26, cy + 0.05, 0.32),
          (170, 178, 184), (170, 178, 184), (170, 178, 184))
    q.box((cx - 0.07, cy - 0.28, 0.26), (cx + 0.07, cy + 0.24, 0.32),
          (170, 178, 184), (170, 178, 184), (170, 178, 184))
    _cylinder(q, cx, cy - 0.02, 0.255, 0.325, 0.07,
              (110, 118, 124), (110, 118, 124), (110, 118, 124), n=16)


def _slab(q, cx, cy, hw=0.30, hd=0.20):
    """Display base slab; top at z=0.05, sunk past the plinth crown."""
    q.box((cx - hw, cy - hd, -0.13), (cx + hw, cy + hd, 0.05),
          (150, 164, 152), (120, 136, 124), (170, 182, 170))


def arrow_growth(q, cx, cy, P):
    """Rising chart: slab, three ascending bars, arrow out of the tallest."""
    _slab(q, cx, cy)
    q.box((cx - 0.26, cy - 0.06, 0.0), (cx - 0.12, cy + 0.06, 0.40),
          (150, 190, 160), (110, 150, 120), (170, 205, 175))
    q.box((cx - 0.07, cy - 0.06, 0.0), (cx + 0.07, cy + 0.06, 0.60),
          (120, 175, 140), (90, 135, 108), (145, 195, 160))
    q.box((cx + 0.12, cy - 0.06, 0.0), (cx + 0.26, cy + 0.06, 0.82),
          (240, 170, 95), (190, 130, 70), (252, 192, 120))
    ay = cy + 0.068
    x0, z0, x1, z1, hw = cx + 0.19, 0.50, cx + 0.37, 1.00, 0.042
    dx, dz = x1 - x0, z1 - z0
    ln = math.hypot(dx, dz)
    nx, nz = -dz / ln * hw, dx / ln * hw
    q.poly([(x0 + nx, ay, z0 + nz), (x0 - nx, ay, z0 - nz),
            (x1 - nx, ay, z1 - nz), (x1 + nx, ay, z1 + nz)], (110, 195, 120))
    q.poly([(cx + 0.42, ay, 1.06), (cx + 0.30, ay, 0.94),
            (cx + 0.42, ay, 0.90)], (110, 195, 120))


def coins_big(q, cx, cy, P):
    """Three big gold coin stacks on a slab, two flat coins at the foot."""
    _slab(q, cx, cy, hw=0.34)
    _cylinder(q, cx - 0.24, cy, 0.0, 0.30, 0.14,
              (232, 186, 96), (170, 128, 62), (244, 204, 120), n=28)
    _cylinder(q, cx + 0.03, cy, 0.0, 0.48, 0.16,
              (232, 186, 96), (170, 128, 62), (244, 204, 120), n=32)
    _cylinder(q, cx + 0.27, cy, 0.0, 0.22, 0.12,
              (240, 160, 86), (176, 110, 56), (250, 180, 110), n=28)
    for px in (cx - 0.02, cx - 0.30):
        q.ground_ellipse(px, cy + 0.24, 0.08, 0.08, (170, 128, 62), z=0.052)
        q.ground_ellipse(px, cy + 0.24, 0.08, 0.08, (232, 186, 96), z=0.082)


def shield(q, cx, cy, P):
    """Shield emblem: back plate, three-tier shield, white check lines."""
    _slab(q, cx, cy)
    q.box((cx - 0.26, cy - 0.02, 0.0), (cx + 0.26, cy + 0.10, 0.78),
          (150, 170, 200), (120, 140, 170), (170, 190, 215))
    q.box((cx - 0.20, cy + 0.10, 0.10), (cx + 0.20, cy + 0.16, 0.40),
          (120, 185, 130), (90, 145, 100), (145, 205, 150))
    q.box((cx - 0.15, cy + 0.10, 0.395), (cx + 0.15, cy + 0.16, 0.60),
          (105, 200, 120), (75, 155, 90), (140, 220, 150))
    q.box((cx - 0.08, cy + 0.10, 0.595), (cx + 0.08, cy + 0.16, 0.74),
          (240, 170, 95), (190, 130, 70), (252, 192, 120))
    wy = cy + 0.165
    q.line([(cx - 0.11, wy, 0.44), (cx - 0.03, wy, 0.36)], (248, 250, 244), 2.0)
    q.line([(cx - 0.03, wy, 0.36), (cx + 0.11, wy, 0.52)], (248, 250, 244), 2.0)


def check_badge(q, cx, cy, P):
    """Round mint check badge on a post over a foot block."""
    q.box((cx - 0.20, cy - 0.14, -0.13), (cx + 0.20, cy + 0.14, 0.06),
          (150, 164, 152), (120, 136, 124), (170, 182, 170))
    q.box((cx - 0.06, cy + 0.02, 0.0), (cx + 0.06, cy + 0.10, 0.40),
          (130, 142, 134), (104, 116, 108), (150, 162, 152))
    q.disc_y(cx, cy + 0.085, 0.52, 0.30, (90, 150, 105))
    q.disc_y(cx, cy + 0.10, 0.52, 0.26, (105, 200, 120))
    q.disc_y(cx, cy + 0.101, 0.52, 0.19, (140, 220, 150))
    wy = cy + 0.106
    q.line([(cx - 0.11, wy, 0.53), (cx - 0.03, wy, 0.45)], (248, 250, 244), 2.2)
    q.line([(cx - 0.03, wy, 0.45), (cx + 0.11, wy, 0.61)], (248, 250, 244), 2.2)


def warning_triangle(q, cx, cy, P):
    """Amber warning triangle, dark rim, bar-and-dot mark."""
    _slab(q, cx, cy)
    q.poly([(cx - 0.33, cy + 0.045, 0.03), (cx + 0.33, cy + 0.045, 0.03),
            (cx, cy + 0.045, 0.82)], (110, 118, 124))
    q.poly([(cx - 0.29, cy + 0.05, 0.045), (cx + 0.29, cy + 0.05, 0.045),
            (cx, cy + 0.05, 0.76)], (240, 176, 80))
    q.box((cx - 0.035, cy + 0.05, 0.30), (cx + 0.035, cy + 0.10, 0.56),
          (90, 98, 104), (90, 98, 104), (90, 98, 104))
    q.dot((cx, cy + 0.105, 0.60), 1.2, (90, 98, 104, 255))


def clock(q, cx, cy, P):
    """Round wall clock: foot, post, rim, cream face, hands, ticks."""
    q.box((cx - 0.22, cy - 0.14, -0.13), (cx + 0.22, cy + 0.14, 0.06),
          (150, 164, 152), (120, 136, 124), (170, 182, 170))
    q.box((cx - 0.07, cy + 0.0, 0.0), (cx + 0.07, cy + 0.085, 0.32),
          (130, 142, 134), (104, 116, 108), (150, 162, 152))
    q.disc_y(cx, cy + 0.085, 0.50, 0.30, (80, 110, 115))
    q.disc_y(cx, cy + 0.10, 0.50, 0.26, (244, 240, 228))
    hy = cy + 0.108
    q.line([(cx, hy, 0.50), (cx + 0.10, hy, 0.62)], (70, 84, 78), 1.6)
    q.line([(cx, hy, 0.50), (cx - 0.07, hy, 0.42)], (70, 84, 78), 1.6)
    q.dot((cx, hy, 0.50), 1.2, (200, 70, 60, 255))
    for tx, tz in ((0.0, 0.70), (0.0, 0.30), (0.17, 0.50), (-0.17, 0.50)):
        q.dot((cx + tx, hy, tz), 0.8, (130, 142, 134, 255))


def thermometer(q, cx, cy, P):
    """Thermometer: glass bulb + tube, red fill, cap, scale ticks."""
    _slab(q, cx, cy, hw=0.24)
    _cylinder(q, cx, cy, 0.0, 0.26, 0.15,
              (215, 222, 226), (190, 200, 206), (222, 228, 232), n=28)
    _cylinder(q, cx, cy, 0.04, 0.20, 0.09,
              (200, 70, 60), (200, 70, 60), (210, 84, 72), n=20)
    q.box((cx - 0.09, cy - 0.09, 0.20), (cx + 0.09, cy + 0.09, 0.82),
          (215, 222, 226), (190, 200, 206), (222, 228, 232))
    q.box((cx - 0.04, cy - 0.04, 0.10), (cx + 0.04, cy + 0.04, 0.66),
          (200, 70, 60), (200, 70, 60), (200, 70, 60))
    q.box((cx - 0.10, cy - 0.10, 0.815), (cx + 0.10, cy + 0.10, 0.88),
          (130, 138, 144), (104, 112, 118), (150, 158, 164))
    ty = cy + 0.095
    for z0 in (0.42, 0.52, 0.62):
        q.line([(cx + 0.02, ty, z0), (cx + 0.09, ty, z0)], (120, 130, 136), 1.0)


def droplet(q, cx, cy, P):
    """Water droplet: four shrinking blue tiers + white glint."""
    _slab(q, cx, cy, hw=0.32)
    _cylinder(q, cx, cy, 0.0, 0.32, 0.20,
              (80, 140, 190), (64, 112, 152), (92, 152, 202), n=32)
    _cylinder(q, cx, cy, 0.315, 0.46, 0.15,
              (80, 140, 190), (64, 112, 152), (92, 152, 202), n=24)
    _cylinder(q, cx, cy, 0.455, 0.58, 0.10,
              (90, 150, 200), (72, 120, 160), (102, 162, 212), n=20)
    _cylinder(q, cx, cy, 0.575, 0.68, 0.05,
              (100, 160, 210), (80, 128, 168), (112, 172, 222), n=16)
    q.dot((cx - 0.08, cy + 0.17, 0.22), 1.0, (232, 244, 252, 255))


def leaf(q, cx, cy, P):
    """Eco leaf: stem, pointed leaf plate, embossed veins."""
    _slab(q, cx, cy)
    q.box((cx - 0.035, cy - 0.035, 0.0), (cx + 0.035, cy + 0.035, 0.55),
          (110, 140, 90), (88, 114, 72), (130, 160, 108))
    q.poly([(cx, cy + 0.04, 0.18), (cx - 0.24, cy + 0.04, 0.40),
            (cx - 0.16, cy + 0.04, 0.62), (cx, cy + 0.04, 0.78),
            (cx + 0.16, cy + 0.04, 0.62), (cx + 0.24, cy + 0.04, 0.40)],
           (105, 190, 110))
    vy = cy + 0.045
    q.line([(cx, vy, 0.22), (cx, vy, 0.72)], (70, 130, 75), 1.2)
    q.line([(cx, vy, 0.44), (cx - 0.14, vy, 0.52)], (70, 130, 75), 1.0)
    q.line([(cx, vy, 0.44), (cx + 0.14, vy, 0.52)], (70, 130, 75), 1.0)


def plug(q, cx, cy, P):
    """Power plug: cable stub, blue body, two proud prongs."""
    _slab(q, cx, cy)
    q.box((cx - 0.06, cy - 0.06, 0.0), (cx + 0.06, cy + 0.06, 0.31),
          (90, 98, 104), (72, 80, 86), (108, 116, 122))
    q.box((cx - 0.12, cy - 0.12, 0.30), (cx + 0.12, cy + 0.12, 0.60),
          (72, 104, 160), (58, 84, 130), (86, 120, 182))
    for px in (cx - 0.05, cx + 0.05):
        q.box((px - 0.025, cy - 0.025, 0.595),
              (px + 0.025, cy + 0.025, 0.75),
              (200, 204, 206), (200, 204, 206), (200, 204, 206))
    q.dot((cx - 0.05, cy + 0.121, 0.44), 0.8, (255, 200, 120, 255))
    q.dot((cx + 0.05, cy + 0.121, 0.44), 0.8, (255, 200, 120, 255))


def bolt(q, cx, cy, P):
    """Amber lightning bolt: four stepped zigzag tiers on a slab."""
    _slab(q, cx, cy)
    q.box((cx - 0.15, cy - 0.10, 0.60), (cx + 0.15, cy + 0.10, 0.75),
          (240, 190, 60), (192, 150, 48), (248, 202, 78))
    q.box((cx - 0.15, cy - 0.10, 0.42), (cx + 0.05, cy + 0.10, 0.62),
          (240, 190, 60), (192, 150, 48), (248, 202, 78))
    q.box((cx - 0.05, cy - 0.10, 0.24), (cx + 0.15, cy + 0.10, 0.44),
          (240, 190, 60), (192, 150, 48), (248, 202, 78))
    q.box((cx - 0.05, cy - 0.10, 0.0), (cx + 0.05, cy + 0.10, 0.26),
          (240, 190, 60), (192, 150, 48), (248, 202, 78))


def wifi(q, cx, cy, P):
    """Wifi: emitter block with dot, three arc fans above it."""
    _slab(q, cx, cy)
    q.box((cx - 0.08, cy - 0.07, 0.0), (cx + 0.08, cy + 0.07, 0.20),
          (240, 170, 95), (190, 130, 70), (252, 192, 120))
    q.dot((cx, cy + 0.076, 0.11), 1.4, (248, 250, 244, 255))
    wy = cy + 0.0
    for r, w in ((0.24, 2.2), (0.38, 2.0), (0.52, 1.8)):
        steps = 24
        pts = [(cx + r * math.cos(math.pi * (25 + 130 * i / steps) / 180),
                wy, 0.12 + r * math.sin(math.pi * (25 + 130 * i / steps) / 180))
               for i in range(steps + 1)]
        for a, b in zip(pts, pts[1:]):
            q.line([a, b], (105, 200, 120), w)


def wrench_cross(q, cx, cy, P):
    """Two crossed wrenches on posts: offset bars, jaw blocks at the ends."""
    _slab(q, cx, cy, hw=0.44)
    for lx in (cx - 0.24, cx + 0.24):
        q.box((lx - 0.05, cy - 0.05, 0.0), (lx + 0.05, cy + 0.05, 0.36),
              (130, 138, 144), (104, 112, 118), (150, 158, 164))
    q.box((cx - 0.36, cy - 0.055, 0.34), (cx + 0.36, cy + 0.055, 0.42),
          (150, 158, 164), (120, 128, 134), (170, 178, 184))
    q.box((cx - 0.055, cy - 0.36, 0.345), (cx + 0.055, cy + 0.36, 0.425),
          (170, 178, 184), (136, 144, 150), (190, 198, 204))
    for ex, ey in ((cx + 0.40, cy), (cx - 0.40, cy),
                   (cx, cy + 0.40), (cx, cy - 0.40)):
        q.box((ex - 0.10, ey - 0.07, 0.335), (ex + 0.10, ey + 0.07, 0.43),
              (105, 200, 120), (84, 160, 96), (125, 215, 140))


def star(q, cx, cy, P):
    """Gold star badge: foot, post, teal disc, five-point star."""
    q.box((cx - 0.20, cy - 0.14, -0.13), (cx + 0.20, cy + 0.14, 0.06),
          (150, 164, 152), (120, 136, 124), (170, 182, 170))
    q.box((cx - 0.06, cy + 0.0, 0.0), (cx + 0.06, cy + 0.08, 0.32),
          (130, 142, 134), (104, 116, 108), (150, 162, 152))
    q.disc_y(cx, cy + 0.065, 0.50, 0.30, (80, 110, 115))
    q.disc_y(cx, cy + 0.08, 0.50, 0.26, (105, 165, 170))
    pts = []
    for k in range(10):
        rr = 0.22 if k % 2 == 0 else 0.095
        a = -math.pi / 2 + k * math.pi / 5
        pts.append((cx + rr * math.cos(a), cy + 0.085, 0.50 + rr * math.sin(a)))
    q.poly(pts, (250, 200, 110))


def percent(q, cx, cy, P):
    """Percent tag: cream plate, cap, feet, dot-slash-dot glyph."""
    for fx in (cx - 0.18, cx + 0.18):
        q.box((fx - 0.04, cy - 0.06, -0.13), (fx + 0.04, cy + 0.06, 0.12),
              (130, 138, 144), (104, 112, 118), (150, 158, 164))
    q.box((cx - 0.30, cy - 0.02, 0.08), (cx + 0.30, cy + 0.08, 0.68),
          (238, 243, 234), (204, 214, 200), (248, 250, 244))
    q.box((cx - 0.31, cy - 0.03, 0.675), (cx + 0.31, cy + 0.09, 0.72),
          (150, 164, 152), (120, 136, 124), (170, 182, 170))
    py = cy + 0.085
    q.box((cx - 0.20, py - 0.045, 0.46), (cx - 0.11, py + 0.045, 0.55),
          (90, 150, 105), (90, 150, 105), (90, 150, 105))
    q.box((cx + 0.11, py - 0.045, 0.22), (cx + 0.20, py + 0.045, 0.31),
          (90, 150, 105), (90, 150, 105), (90, 150, 105))
    x0, z0, x1, z1, hw = cx - 0.17, 0.20, cx + 0.17, 0.58, 0.030
    dx, dz = x1 - x0, z1 - z0
    ln = math.hypot(dx, dz)
    nx, nz = -dz / ln * hw, dx / ln * hw
    q.poly([(x0 + nx, py, z0 + nz), (x0 - nx, py, z0 - nz),
            (x1 - nx, py, z1 - nz), (x1 + nx, py, z1 + nz)], (90, 150, 105))


def icon_plug(q, cx, cy, P):
    """Plug pictogram: body, two prongs, cable stub."""
    q.box((cx - 0.06, cy - 0.06, 0.10), (cx + 0.06, cy + 0.06, 0.31),
          (90, 98, 104), (90, 98, 104), (90, 98, 104))
    q.box((cx - 0.12, cy - 0.12, 0.30), (cx + 0.12, cy + 0.12, 0.60),
          (60, 90, 140), (50, 76, 120), (72, 104, 160))
    for px in (cx - 0.05, cx + 0.05):
        q.box((px - 0.025, cy - 0.025, 0.595), (px + 0.025, cy + 0.025, 0.75),
              (200, 204, 206), (200, 204, 206), (200, 204, 206))


_reg("icon-sun", icon_sun, (0.0, 0.15, 0.35), 560,
     (0.0, 0.15, 0.55, 0.34),
     "Minimalist isometric pictogram icon of the sun with rays")
_reg("icon-drop", icon_drop, (0.0, 0.15, 0.38), 560,
     (0.0, 0.15, 0.50, 0.32),
     "Minimalist isometric pictogram icon of a water drop")
_reg("icon-flame", icon_flame, (0.0, 0.15, 0.38), 560,
     (0.0, 0.15, 0.50, 0.32),
     "Minimalist isometric pictogram icon of a flame")
_reg("icon-bolt", icon_bolt, (0.0, 0.15, 0.40), 560,
     (0.0, 0.15, 0.50, 0.32),
     "Minimalist isometric pictogram icon of a lightning bolt")
_reg("icon-snowflake", icon_snowflake, (0.0, 0.15, 0.35), 560,
     (0.0, 0.15, 0.55, 0.34),
     "Minimalist isometric pictogram icon of a snowflake")
_reg("icon-thermometer", icon_thermometer, (0.0, 0.15, 0.42), 560,
     (0.0, 0.15, 0.50, 0.32),
     "Minimalist isometric pictogram icon of a thermometer")
_reg("icon-gauge", icon_gauge, (0.0, 0.15, 0.28), 560,
     (0.0, 0.15, 0.50, 0.32),
     "Minimalist isometric pictogram icon of a pressure gauge")
_reg("icon-battery", icon_battery, (0.0, 0.15, 0.35), 540,
     (0.0, 0.15, 0.55, 0.34),
     "Minimalist isometric pictogram icon of a battery")
_reg("icon-house", icon_house, (0.0, 0.15, 0.35), 560,
     (0.0, 0.15, 0.55, 0.34),
     "Minimalist isometric pictogram icon of a house")
_reg("icon-factory", icon_factory, (0.0, 0.15, 0.40), 540,
     (0.0, 0.15, 0.60, 0.34),
     "Minimalist isometric pictogram icon of a factory")
_reg("icon-panel", icon_panel, (0.0, 0.15, 0.25), 560,
     (0.0, 0.15, 0.55, 0.34),
     "Minimalist isometric pictogram icon of a solar panel")
_reg("icon-tank", icon_tank, (0.0, 0.15, 0.35), 560,
     (0.0, 0.15, 0.50, 0.32),
     "Minimalist isometric pictogram icon of a buffer tank")
_reg("icon-valve", icon_valve, (0.0, 0.15, 0.30), 560,
     (0.0, 0.15, 0.45, 0.28),
     "Minimalist isometric pictogram icon of a valve with handwheel")
_reg("icon-fan", icon_fan, (0.0, 0.13, 0.30), 560,
     (0.0, 0.13, 0.55, 0.34),
     "Minimalist isometric pictogram icon of a fan")
_reg("icon-plug", icon_plug, (0.0, 0.15, 0.42), 560,
     (0.0, 0.15, 0.50, 0.32),
     "Minimalist isometric pictogram icon of an electric plug")
_reg("arrow-growth", arrow_growth, (0.0, 0.15, 0.50), 560,
     (0.0, 0.15, 0.55, 0.34), "rising chart arrow on plate")
_reg("coins-big", coins_big, (0.0, 0.15, 0.30), 580,
     (0.0, 0.15, 0.58, 0.36), "big coin stacks")
_reg("shield", shield, (0.0, 0.15, 0.40), 560,
     (0.0, 0.15, 0.55, 0.34), "shield emblem with check bar")
_reg("check-badge", check_badge, (0.0, 0.15, 0.42), 560,
     (0.0, 0.15, 0.52, 0.32), "round check badge")
_reg("warning-triangle", warning_triangle, (0.0, 0.15, 0.42), 560,
     (0.0, 0.15, 0.55, 0.34), "warning triangle with bar")
_reg("clock", clock, (0.0, 0.15, 0.38), 560,
     (0.0, 0.15, 0.52, 0.32), "round clock with hands")
_reg("thermometer", thermometer, (0.0, 0.15, 0.44), 560,
     (0.0, 0.15, 0.50, 0.32), "thermometer with bulb")
_reg("droplet", droplet, (0.0, 0.15, 0.34), 580,
     (0.0, 0.15, 0.55, 0.34), "water droplet")
_reg("leaf", leaf, (0.0, 0.15, 0.40), 560,
     (0.0, 0.15, 0.52, 0.32), "eco leaf emblem")
_reg("plug", plug, (0.0, 0.15, 0.38), 560,
     (0.0, 0.15, 0.50, 0.32), "power plug with pins")
_reg("bolt", bolt, (0.0, 0.15, 0.38), 560,
     (0.0, 0.15, 0.50, 0.32), "lightning bolt emblem")
_reg("wifi", wifi, (0.0, 0.15, 0.38), 560,
     (0.0, 0.15, 0.55, 0.34), "wifi arcs with dot")
_reg("wrench-cross", wrench_cross, (0.0, 0.15, 0.30), 600,
     (0.0, 0.15, 0.62, 0.36), "crossed wrenches emblem")
_reg("star", star, (0.0, 0.15, 0.38), 560,
     (0.0, 0.15, 0.52, 0.32), "star badge")
_reg("percent", percent, (0.0, 0.15, 0.40), 560,
     (0.0, 0.15, 0.55, 0.34), "percent tag plate")
