"""Batch extra: 5 props topping the gallery up to 50+ new objects."""
import math

from .world import _cylinder

PROPS = {}


def _reg(name, fn, focus, k, plinth, brief):
    PROPS[name] = {"fn": fn, "focus": focus, "k": k, "plinth": plinth,
                   "brief": brief}


def collector(q, cx, cy, P):
    """Solar thermal collector: tilted glass quad in a frame on A-legs,
    copper stubs under the low edge."""
    # Legs: front pair short, back pair tall (overlap panel edge).
    for fx in (cx - 0.30, cx + 0.30):
        q.box((fx - 0.025, cy + 0.19, 0.0), (fx + 0.025, cy + 0.27, 0.30),
              (70, 84, 74), (70, 84, 74), (70, 84, 74))
        q.box((fx - 0.025, cy - 0.27, 0.0), (fx + 0.025, cy - 0.19, 0.60),
              (70, 84, 74), (70, 84, 74), (70, 84, 74))
    # Glass quad + frame rails + 2 slope bars.
    q.poly([(cx - 0.35, cy + 0.25, 0.28), (cx + 0.35, cy + 0.25, 0.28),
            (cx + 0.35, cy - 0.25, 0.58), (cx - 0.35, cy - 0.25, 0.58)],
           (44, 78, 104))
    for ex in (-0.35, 0.35):
        q.line([(cx + ex, cy + 0.25, 0.28), (cx + ex, cy - 0.25, 0.58)],
               (150, 164, 150), 1.6)
    q.line([(cx - 0.35, cy + 0.25, 0.28), (cx + 0.35, cy + 0.25, 0.28)],
           (150, 164, 150), 1.6)
    q.line([(cx - 0.35, cy - 0.25, 0.58), (cx + 0.35, cy - 0.25, 0.58)],
           (150, 164, 150), 1.6)
    for bx in (-0.12, 0.12):
        q.line([(cx + bx, cy + 0.25, 0.285), (cx + bx, cy - 0.25, 0.585)],
               (90, 130, 160), 0.9)
    # Copper stubs under the low edge.
    for sx in (cx - 0.20, cx + 0.20):
        _cylinder(q, sx, cy + 0.25, 0.02, 0.29, 0.030,
                  (198, 112, 72), (148, 78, 48), (218, 140, 95), n=10)


def weather(q, cx, cy, P):
    """Weather station: pole on a plate, crossarm, 3-cup anemometer,
    sensor box and a mini solar panel."""
    q.box((cx - 0.09, cy - 0.09, 0.0), (cx + 0.09, cy + 0.09, 0.03),
          (90, 100, 90), (90, 100, 90), (90, 100, 90))
    _cylinder(q, cx, cy, 0.03, 0.90, 0.028,
              (150, 160, 150), (110, 124, 114), (170, 180, 170), n=10)
    q.box((cx - 0.16, cy - 0.02, 0.80), (cx + 0.16, cy + 0.02, 0.84),
          (110, 124, 114), (110, 124, 114), (110, 124, 114))
    for k in range(3):
        ang = k * 2.094
        ex, ey = cx + 0.14 * math.cos(ang), cy + 0.14 * math.sin(ang)
        q.line([(cx, cy, 0.88), (ex, ey, 0.88)], (110, 124, 114), 1.2)
        # World-sized cups, not px dots: open bowl with a dark hollow
        # just under the mouth (corpus gate 2026-11-12).
        _cylinder(q, ex, ey, 0.862, 0.892, 0.018,
                  (70, 84, 74), (52, 64, 56), (88, 102, 92), n=8,
                  rim=False, top_ring=False)
        q.ground_ellipse(ex, ey, 0.012, 0.012, (30, 38, 32), z=0.888)
    q.dot((cx, cy, 0.885), 1.6, (150, 160, 150, 255))
    # Sensor box embedded 0.01 into the pole (was exact-tangent) plus
    # a visible bracket arm: no floating box (corpus gate 2026-11-12).
    q.box((cx - 0.07, cy + 0.018, 0.45), (cx + 0.07, cy + 0.10, 0.60),
          (230, 236, 226), (200, 208, 196), (240, 244, 236))
    q.box((cx - 0.02, cy + 0.005, 0.50), (cx + 0.02, cy + 0.045, 0.54),
          (110, 124, 114), (110, 124, 114), (110, 124, 114))
    q.dot((cx, cy + 0.103, 0.55), 0.9, (110, 190, 170, 255))
    # Panel bracket pole->panel plus a frame edge: no floating panel.
    q.box((cx - 0.015, cy - 0.035, 0.70), (cx + 0.015, cy - 0.005, 0.73),
          (110, 124, 114), (110, 124, 114), (110, 124, 114))
    q.poly([(cx - 0.09, cy - 0.02, 0.66), (cx + 0.09, cy - 0.02, 0.66),
            (cx + 0.09, cy - 0.02, 0.76), (cx - 0.09, cy - 0.02, 0.76)],
           (44, 78, 104))
    q.line([(cx - 0.09, cy - 0.02, 0.66), (cx + 0.09, cy - 0.02, 0.66),
            (cx + 0.09, cy - 0.02, 0.76), (cx - 0.09, cy - 0.02, 0.76),
            (cx - 0.09, cy - 0.02, 0.66)], (28, 52, 72), 1.0)


def ups(q, cx, cy, P):
    """UPS box on feet: front LEDs, vent slots, switch and two sockets."""
    for fx in (cx - 0.15, cx + 0.15):
        q.box((fx - 0.04, cy - 0.10, 0.0), (fx + 0.04, cy + 0.10, 0.05),
              (40, 48, 42), (40, 48, 42), (40, 48, 42))
    q.box((cx - 0.20, cy - 0.13, 0.04), (cx + 0.20, cy + 0.13, 0.30),
          (108, 120, 108), (86, 98, 86), (132, 144, 132))
    q.box((cx - 0.155, cy + 0.128, 0.225), (cx + 0.015, cy + 0.138, 0.255),
          (150, 162, 150), (150, 162, 150), (150, 162, 150))
    for j, col in enumerate(((110, 190, 170), (220, 150, 60), (110, 190, 170))):
        q.dot((cx - 0.12 + j * 0.05, cy + 0.139, 0.24), 1.4,
              col + (255,))
    for j in range(3):
        q.line([(cx - 0.16, cy + 0.132, 0.10 + j * 0.03),
                (cx - 0.02, cy + 0.132, 0.10 + j * 0.03)], (48, 58, 50), 0.9)
    q.line([(cx - 0.19, cy - 0.12, 0.302), (cx + 0.19, cy - 0.12, 0.302),
            (cx + 0.19, cy + 0.12, 0.302), (cx - 0.19, cy + 0.12, 0.302),
            (cx - 0.19, cy - 0.12, 0.302)], (70, 82, 70), 0.8)
    for sx in (cx - 0.17, cx + 0.17):
        for sy in (cy - 0.09, cy + 0.09):
            q.dot((sx, sy, 0.303), 0.8, (70, 82, 70, 255))
    q.box((cx + 0.06, cy + 0.128, 0.20), (cx + 0.10, cy + 0.136, 0.26),
          (30, 38, 32), (30, 38, 32), (30, 38, 32))
    for sx in (0.13, 0.175):
        q.box((cx + sx - 0.012, cy + 0.128, 0.08), (cx + sx + 0.012, cy + 0.136,
              0.14), (22, 30, 26), (22, 30, 26), (22, 30, 26))


def towel_rad(q, cx, cy, P):
    """Bathroom ladder radiator on a slim wall chip: chrome uprights,
    five rungs, side valve with knob."""
    q.box((cx - 0.30, cy - 0.03, 0.0), (cx + 0.30, cy + 0.03, 0.95),
          (226, 232, 218), (200, 210, 194), (238, 242, 232))
    for fx in (cx - 0.22, cx + 0.22):
        _cylinder(q, fx, cy + 0.10, 0.10, 0.80, 0.035,
                  (170, 185, 180), (130, 145, 140), (190, 204, 198), n=12)
    for j in range(5):
        z = 0.20 + j * 0.125
        q.box((cx - 0.22, cy + 0.075, z - 0.028), (cx + 0.22, cy + 0.125,
              z + 0.028), (160, 175, 170), (160, 175, 170), (160, 175, 170))
    for bx in (cx - 0.22, cx + 0.22):
        for bz in (0.30, 0.70):
            q.box((bx - 0.02, cy + 0.03, bz - 0.02), (bx + 0.02, cy + 0.10,
                  bz + 0.02), (130, 145, 140), (130, 145, 140),
                  (130, 145, 140))
    _cylinder(q, cx + 0.22, cy + 0.10, 0.02, 0.10, 0.045,
              (96, 110, 100), (70, 84, 74), (120, 134, 122), n=10)
    q.dot((cx + 0.22, cy + 0.10, 0.075), 1.2, (200, 62, 52, 255))


def water_meter(q, cx, cy, P):
    """Inline brass water meter: horizontal run with union nuts, central
    body, top dial with glass, needle and embossed ticks, feet on a pad."""
    q.box((cx - 0.10, cy - 0.08, 0.0), (cx + 0.10, cy + 0.08, 0.03),
          (90, 100, 90), (90, 100, 90), (90, 100, 90))
    for sx in (cx - 0.21, cx + 0.21):
        q.box((sx - 0.07, cy - 0.035, 0.13), (sx + 0.07, cy + 0.035, 0.20),
              (188, 132, 82), (142, 96, 58), (188, 132, 82))
    for sx in (cx - 0.12, cx + 0.12):
        q.box((sx - 0.035, cy - 0.05, 0.115), (sx + 0.035, cy + 0.05, 0.215),
              (142, 96, 58), (108, 72, 44), (164, 116, 74))
    q.box((cx - 0.09, cy - 0.06, 0.025), (cx + 0.09, cy + 0.06, 0.22),
          (188, 132, 82), (142, 96, 58), (188, 132, 82))
    q.ground_ellipse(cx, cy, 0.070, 0.070, (150, 172, 150), z=0.218)
    q.ground_ellipse(cx, cy, 0.056, 0.056, (238, 244, 238), z=0.223)
    for k in range(8):
        ang = k * 0.785
        q.line([(cx + 0.045 * math.cos(ang), cy + 0.045 * math.sin(ang), 0.224),
                (cx + 0.053 * math.cos(ang), cy + 0.053 * math.sin(ang), 0.224)],
               (90, 110, 92), 0.7)
    q.line([(cx, cy, 0.225), (cx + 0.038, cy + 0.016, 0.225)], (200, 62, 52),
           1.0)
    q.dot((cx, cy, 0.226), 0.8, (90, 110, 92, 255))


_reg("collector", collector, (0.0, 0.15, 0.35), 550, (0.0, 0.15, 0.60, 0.40),
     "Solar thermal collector: tilted glass panel in frame on A-legs with copper stubs below the low edge")
_reg("weather", weather, (0.0, 0.15, 0.45), 500, (0.0, 0.15, 0.45, 0.32),
     "Weather station: pole with crossarm anemometer cups, sensor box and mini solar panel")
_reg("ups", ups, (0.0, 0.15, 0.16), 600, (0.0, 0.15, 0.45, 0.30),
     "UPS box on feet with status LEDs, vent slots, switch and sockets")
_reg("towel-rad", towel_rad, (0.0, 0.15, 0.47), 500, (0.0, 0.15, 0.50, 0.32),
     "Bathroom ladder radiator in chrome on a wall chip with side valve")
_reg("water-meter", water_meter, (0.0, 0.15, 0.14), 650, (0.0, 0.15, 0.40, 0.28),
     "Brass water meter with pipe stubs, union nuts and top dial with needle")
