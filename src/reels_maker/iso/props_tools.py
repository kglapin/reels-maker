"""Tool gallery batch (157-171): hand tools, test gear and service kit."""
from __future__ import annotations

import math

from reels_maker.iso.world import _cylinder


def drill(q, cx, cy, P):
    """Cordless drill: battery pack, pistol grip with trigger, chuck + bit."""
    # Battery pack foot first (wide pack, release + charge dots on +Y).
    q.box((cx - 0.26, cy - 0.11, 0.0), (cx + 0.14, cy + 0.11, 0.10),
          (70, 80, 76), (60, 68, 64), (86, 96, 92))
    q.box((cx - 0.12, cy - 0.06, 0.06), (cx + 0.04, cy + 0.06, 0.20),
          (78, 88, 82), (64, 74, 68), (94, 104, 98))
    q.box((cx - 0.20, cy + 0.105, 0.03), (cx - 0.10, cy + 0.125, 0.07),
          (60, 72, 66), (60, 72, 66), (60, 72, 66))
    q.dot((cx - 0.15, cy + 0.126, 0.05), 0.8, (110, 200, 130, 255))
    for i in range(3):
        q.dot((cx - 0.02 + i * 0.05, cy + 0.112, 0.05), 0.7,
              (110, 200, 120, 255))
    # Pistol grip rises out of the pack into the body (overlap both ends).
    q.box((cx - 0.16, cy - 0.07, 0.09), (cx + 0.0, cy + 0.07, 0.38),
          (66, 88, 80), (60, 76, 70), (80, 104, 94))
    # Red trigger proud of the grip's +X face + rows of grip ribs on +Y.
    q.box((cx - 0.03, cy - 0.025, 0.19), (cx + 0.035, cy + 0.025, 0.31),
          (170, 70, 55), (140, 58, 46), (190, 86, 68))
    for gz in (0.13, 0.17, 0.21, 0.25, 0.29, 0.33):
        q.line([(cx - 0.14, cy + 0.072, gz), (cx - 0.02, cy + 0.072, gz)],
               (60, 76, 70), 0.8)
    # Hero body in dark green (overlaps grip top), lighter lid course.
    q.box((cx - 0.30, cy - 0.10, 0.30), (cx + 0.18, cy + 0.10, 0.55),
          (64, 112, 98), (60, 92, 82), (80, 132, 116))
    q.box((cx - 0.30, cy - 0.10, 0.545), (cx + 0.18, cy + 0.10, 0.585),
          (80, 132, 116), (60, 92, 82), (96, 150, 132))
    # Chuck: three shrinking steel steps from inside the body, tip, long bit.
    q.box((cx + 0.10, cy - 0.075, 0.345), (cx + 0.28, cy + 0.075, 0.505),
          (150, 160, 155), (120, 132, 126), (170, 180, 175))
    q.box((cx + 0.26, cy - 0.058, 0.36), (cx + 0.38, cy + 0.058, 0.49),
          (140, 150, 145), (112, 124, 118), (162, 172, 167))
    q.box((cx + 0.36, cy - 0.042, 0.375), (cx + 0.45, cy + 0.042, 0.475),
          (130, 142, 136), (104, 116, 110), (152, 164, 158))
    q.disc_x(cx + 0.452, cy, 0.425, 0.042, (200, 208, 200))
    q.box((cx + 0.44, cy - 0.012, 0.415), (cx + 0.62, cy + 0.012, 0.435),
          (120, 130, 124), (100, 110, 104), (140, 150, 144))
    q.dot((cx + 0.622, cy, 0.425), 0.7, (80, 90, 84, 255))
    # Dark brand plate + vent slots proud of the +Y flank.
    q.fp(cx - 0.24, cx + 0.02, cy + 0.101, 0.375, 0.50, (52, 68, 62))
    q.line([(cx - 0.22, cy + 0.102, 0.41), (cx - 0.02, cy + 0.102, 0.41)],
           (200, 200, 190), 0.9)
    for vx in (cx - 0.20, cx - 0.14, cx - 0.08):
        q.line([(vx, cy + 0.102, 0.33), (vx, cy + 0.102, 0.40)],
               (60, 80, 74), 0.8)


def grinder(q, cx, cy, P):
    """Angle grinder: cabled rear grip, orange body, head, disc + steel guard."""
    # Power cable: one plug mass + a 0.08 column into the rear grip.
    # Was a light end-cube + 0.06 cable that read as floating bits
    # (corpus gate 2026-11-12; detail law: fewer, bigger).
    q.box((cx - 0.41, cy - 0.035, 0.10), (cx - 0.33, cy + 0.015, 0.42),
          (60, 66, 62), (60, 66, 62), (60, 66, 62))
    q.box((cx - 0.54, cy - 0.045, 0.02), (cx - 0.36, cy + 0.025, 0.12),
          (64, 70, 66), (58, 64, 60), (80, 86, 82))
    q.box((cx - 0.46, cy - 0.055, 0.40), (cx - 0.26, cy + 0.055, 0.54),
          (138, 86, 56), (112, 70, 44), (156, 100, 66))
    q.box((cx - 0.28, cy - 0.085, 0.36), (cx + 0.10, cy + 0.085, 0.58),
          (182, 110, 66), (146, 84, 50), (200, 130, 84))
    # Trailing power cord: grip rear down into the plinth (a cord
    # must END somewhere — corpus gate 2026-11-12).
    q.line([(cx - 0.46, cy, 0.47), (cx - 0.60, cy - 0.02, 0.22),
            (cx - 0.66, cy - 0.02, -0.10)],
           (40, 48, 44), 2.0)
    # Gear head sits low over the disc (was hovering 0.18 above it).
    q.box((cx + 0.08, cy - 0.075, 0.20), (cx + 0.24, cy + 0.075, 0.42),
          (120, 130, 125), (98, 108, 103), (140, 150, 145))
    # Spindle + flange collar connect head to disc (flange under the head).
    q.box((cx + 0.12, cy - 0.04, 0.10), (cx + 0.20, cy + 0.04, 0.34),
          (110, 120, 115), (92, 102, 97), (128, 138, 132))
    _cylinder(q, cx + 0.16, cy, 0.10, 0.32, 0.075,
              (100, 110, 104), (82, 92, 86), (118, 128, 122), n=16)
    # Thin steel disc + hub + nut dot.
    q.ground_ellipse(cx + 0.16, cy, 0.30, 0.30, (120, 130, 125), z=0.095)
    q.ground_ellipse(cx + 0.16, cy, 0.30, 0.30, (210, 215, 210), z=0.115)
    q.ground_ellipse(cx + 0.16, cy, 0.10, 0.10, (130, 140, 135), z=0.117)
    q.dot((cx + 0.16, cy, 0.125), 0.9, (90, 98, 92, 255))
    # Guard shroud: rises out of the disc and INTO the gear head (connected).
    q.box((cx - 0.10, cy - 0.30, 0.10), (cx + 0.30, cy + 0.02, 0.34),
          (95, 100, 96), (78, 84, 79), (112, 118, 113))
    q.box((cx - 0.10, cy - 0.30, 0.335), (cx + 0.30, cy + 0.02, 0.365),
          (112, 118, 113), (78, 84, 79), (128, 134, 129))
    # Side handle sunk deep into the +Y flank + paddle dot, painted last.
    q.box((cx - 0.10, cy + 0.05, 0.40), (cx - 0.03, cy + 0.30, 0.47),
          (90, 100, 94), (74, 84, 78), (106, 116, 110))
    q.dot((cx - 0.065, cy + 0.302, 0.435), 0.9, (70, 80, 74, 255))
    q.fp(cx - 0.22, cx + 0.04, cy + 0.086, 0.42, 0.52, (150, 66, 54))
    q.dot((cx - 0.02, cy + 0.087, 0.47), 0.8, (90, 60, 50, 255))


def multimeter(q, cx, cy, P):
    """Multimeter: amber boot, blue-grey body, screen and dial on +Y."""
    q.box((cx - 0.22, cy - 0.10, 0.0), (cx + 0.22, cy + 0.12, 0.16),
          (215, 150, 75), (175, 120, 58), (228, 168, 92))
    q.box((cx - 0.20, cy - 0.08, 0.10), (cx + 0.20, cy + 0.10, 0.72),
          (84, 112, 140), (66, 90, 114), (104, 132, 160))
    q.box((cx - 0.20, cy - 0.08, 0.715), (cx + 0.20, cy + 0.10, 0.75),
          (96, 124, 152), (76, 100, 124), (114, 142, 170))
    fy = cy + 0.102
    # Screen bezel + glass + digit strokes (embossed lines only).
    q.fp(cx - 0.14, cx + 0.14, fy, 0.52, 0.68, (60, 74, 84))
    q.fp(cx - 0.12, cx + 0.12, fy + 0.001, 0.545, 0.655, (205, 225, 218))
    q.line([(cx - 0.08, fy + 0.002, 0.60), (cx + 0.08, fy + 0.002, 0.60)],
           (90, 120, 110), 1.0)
    q.line([(cx - 0.08, fy + 0.002, 0.575), (cx + 0.02, fy + 0.002, 0.575)],
           (90, 120, 110), 1.0)
    # Dial: rim disc, face disc, tick dots, pointer line, hub dot.
    q.disc_y(cx, fy + 0.001, 0.32, 0.10, (60, 72, 78))
    q.disc_y(cx, fy + 0.002, 0.32, 0.078, (225, 230, 225))
    for k in range(7):
        a = -0.9 + k * 0.3
        q.dot((cx + 0.062 * math.cos(a), fy + 0.003,
               0.32 + 0.062 * math.sin(a)), 0.55,
              (90, 100, 96, 255))
    q.line([(cx - 0.03, fy + 0.004, 0.29), (cx + 0.035, fy + 0.004, 0.35)],
           (180, 90, 60), 1.2)
    q.dot((cx, fy + 0.004, 0.32), 0.9, (70, 80, 86, 255))
    for bx in (cx - 0.09, cx + 0.09):
        q.dot((bx, fy + 0.001, 0.44), 0.8, (215, 150, 75, 255))


def pipe_wrench(q, cx, cy, P):
    """Pipe wrench gripping a pipe stub: handle, hook jaw, pipe, moving jaw."""
    q.box((cx - 0.38, cy - 0.055, 0.10), (cx + 0.15, cy + 0.055, 0.22),
          (175, 92, 66), (140, 72, 52), (195, 112, 84))
    q.box((cx - 0.30, cy - 0.055, 0.215), (cx - 0.10, cy + 0.055, 0.25),
          (140, 72, 52), (140, 72, 52), (140, 72, 52))
    # Hook jaw rises at the +X end (overlaps handle end).
    q.box((cx + 0.12, cy - 0.055, 0.10), (cx + 0.24, cy + 0.055, 0.46),
          (150, 78, 58), (122, 62, 46), (170, 94, 70))
    q.box((cx + 0.12, cy - 0.055, 0.44), (cx + 0.22, cy + 0.055, 0.54),
          (160, 168, 162), (130, 140, 132), (180, 188, 182))
    # Pipe stub standing in the jaw gap (overlaps both jaw faces).
    q.box((cx + 0.215, cy - 0.055, 0.0), (cx + 0.295, cy + 0.055, 0.52),
          (200, 205, 198), (164, 172, 164), (218, 222, 214))
    q.box((cx + 0.215, cy - 0.055, 0.455), (cx + 0.295, cy + 0.055, 0.50),
          (164, 172, 164), (164, 172, 164), (164, 172, 164))
    # Moving jaw + knurl nut close the grip (painted after the pipe).
    q.box((cx + 0.29, cy - 0.055, 0.30), (cx + 0.38, cy + 0.055, 0.56),
          (150, 78, 58), (122, 62, 46), (170, 94, 70))
    q.box((cx + 0.24, cy - 0.06, 0.28), (cx + 0.30, cy + 0.06, 0.38),
          (110, 72, 52), (92, 60, 44), (128, 86, 62))
    # Teeth dots on the +Y jaw faces + heel dot.
    for tz in (0.46, 0.49, 0.52):
        q.dot((cx + 0.17, cy + 0.057, tz), 0.6, (80, 60, 48, 255))
    for tz in (0.44, 0.47, 0.50):
        q.dot((cx + 0.335, cy + 0.057, tz), 0.6, (80, 60, 48, 255))
    q.dot((cx - 0.34, cy + 0.057, 0.16), 0.8, (110, 60, 44, 255))


def level(q, cx, cy, P):
    """Spirit level: aluminium bar on the plinth, caps, two vials on +Y."""
    q.box((cx - 0.42, cy - 0.07, 0.02), (cx + 0.42, cy + 0.07, 0.30),
          (205, 212, 200), (168, 180, 164), (222, 228, 216))
    q.box((cx - 0.44, cy - 0.072, 0.04), (cx - 0.38, cy + 0.072, 0.28),
          (90, 98, 92), (74, 82, 76), (108, 116, 110))
    q.box((cx + 0.38, cy - 0.072, 0.04), (cx + 0.44, cy + 0.072, 0.28),
          (90, 98, 92), (74, 82, 76), (108, 116, 110))
    q.dot((cx - 0.41, cy + 0.074, 0.16), 0.9, (60, 68, 62, 255))
    q.dot((cx + 0.41, cy + 0.074, 0.16), 0.9, (60, 68, 62, 255))
    # Milled slot along the top + two vial windows proud of the +Y face.
    q.fp(cx - 0.34, cx + 0.34, cy + 0.071, 0.10, 0.14, (168, 180, 164))
    for vx in (cx - 0.20, cx + 0.20):
        q.box((vx - 0.10, cy + 0.065, 0.10), (vx + 0.10, cy + 0.105, 0.22),
              (150, 160, 150), (150, 160, 150), (150, 160, 150))
        q.fp(vx - 0.08, vx + 0.08, cy + 0.106, 0.12, 0.20, (190, 225, 195))
        q.line([(vx - 0.08, cy + 0.107, 0.16), (vx + 0.08, cy + 0.107, 0.16)],
               (130, 170, 130), 1.0)
        q.dot((vx + 0.01, cy + 0.108, 0.16), 0.9, (240, 180, 90, 255))


def hammer(q, cx, cy, P):
    """Claw hammer: wood handle, grip, steel head, stepped claw, face cap."""
    q.box((cx - 0.05, cy - 0.05, 0.02), (cx + 0.05, cy + 0.05, 0.62),
          (192, 142, 92), (152, 110, 70), (208, 160, 108))
    q.box((cx - 0.056, cy - 0.056, 0.02), (cx + 0.056, cy + 0.056, 0.30),
          (110, 70, 50), (90, 58, 42), (128, 84, 60))
    q.dot((cx, cy + 0.058, 0.10), 0.8, (70, 50, 38, 255))
    # Collar under the head (top sinks into the head bottom).
    q.box((cx - 0.062, cy - 0.062, 0.50), (cx + 0.062, cy + 0.062, 0.63),
          (100, 110, 105), (82, 92, 87), (118, 128, 122))
    # Head + striking face toward +X (nearer, painted after the collar).
    q.box((cx - 0.10, cy - 0.075, 0.58), (cx + 0.28, cy + 0.075, 0.78),
          (150, 160, 155), (122, 134, 128), (170, 180, 175))
    q.box((cx + 0.26, cy - 0.065, 0.60), (cx + 0.34, cy + 0.065, 0.76),
          (170, 180, 175), (140, 152, 146), (190, 200, 195))
    q.disc_x(cx + 0.342, cy, 0.68, 0.068, (200, 208, 200))
    q.dot((cx + 0.344, cy, 0.68), 0.8, (90, 100, 94, 255))
    # Claw: two steps down toward -X, each overlapping the previous.
    q.box((cx - 0.24, cy - 0.06, 0.58), (cx - 0.08, cy + 0.06, 0.72),
          (140, 150, 145), (114, 126, 120), (160, 170, 165))
    q.box((cx - 0.33, cy - 0.05, 0.50), (cx - 0.22, cy + 0.05, 0.62),
          (130, 142, 136), (106, 118, 112), (150, 162, 156))
    q.line([(cx - 0.04, cy + 0.052, 0.66), (cx + 0.25, cy + 0.052, 0.66)],
           (110, 122, 116), 0.8)


def screwdrivers(q, cx, cy, P):
    """Screwdriver set: open holder, three drivers, tips up, front wall last."""
    # Back wall + base first (far), drivers, then the near front wall.
    q.box((cx - 0.26, cy - 0.14, 0.02), (cx + 0.26, cy - 0.03, 0.55),
          (70, 110, 130), (56, 90, 106), (88, 130, 150))
    q.box((cx - 0.26, cy - 0.14, 0.02), (cx + 0.26, cy + 0.14, 0.12),
          (60, 96, 116), (48, 80, 96), (76, 114, 134))
    q.line([(cx - 0.22, cy - 0.028, 0.48), (cx + 0.22, cy - 0.028, 0.48)],
           (150, 180, 195), 0.8)
    handle_cols = [(185, 80, 60), (70, 130, 180), (220, 170, 80)]
    for dx, col in zip((cx - 0.15, cx, cx + 0.15), handle_cols):
        dark = tuple(max(60, int(v * 0.72)) for v in col)
        light = tuple(min(255, int(v * 1.12)) for v in col)
        q.box((dx - 0.048, cy - 0.06, 0.28), (dx + 0.048, cy + 0.02, 0.56),
              col, dark, light)
        q.box((dx - 0.016, cy - 0.03, 0.50), (dx + 0.016, cy + 0.0, 0.80),
              (170, 178, 172), (140, 150, 142), (190, 198, 192))
        q.box((dx - 0.020, cy - 0.032, 0.78), (dx + 0.020, cy + 0.002, 0.87),
              (110, 118, 112), (92, 100, 94), (128, 136, 130))
        q.dot((dx, cy - 0.005, 0.52), 0.7, (60, 66, 62, 255))
    # Near front wall swallows the driver bottoms (reads as "in the holder").
    q.box((cx - 0.26, cy + 0.05, 0.02), (cx + 0.26, cy + 0.14, 0.32),
          (78, 120, 140), (62, 98, 114), (96, 138, 158))
    q.line([(cx - 0.22, cy + 0.142, 0.26), (cx + 0.22, cy + 0.142, 0.26)],
           (150, 180, 195), 0.8)


def tape_measure(q, cx, cy, P):
    """Tape measure: amber body, blade out +X with hook, clip on +Y."""
    q.box((cx - 0.20, cy - 0.11, 0.02), (cx + 0.20, cy + 0.11, 0.48),
          (230, 170, 70), (186, 136, 56), (242, 188, 92))
    q.box((cx - 0.20, cy - 0.11, 0.475), (cx + 0.20, cy + 0.11, 0.51),
          (238, 184, 86), (186, 136, 56), (248, 200, 108))
    # Blade starts inside the body, hook drops over its end.
    q.box((cx + 0.15, cy - 0.035, 0.30), (cx + 0.55, cy + 0.035, 0.345),
          (235, 238, 230), (200, 205, 196), (246, 248, 242))
    q.box((cx + 0.535, cy - 0.038, 0.235), (cx + 0.575, cy + 0.038, 0.35),
          (120, 130, 125), (100, 110, 105), (140, 150, 145))
    for i in range(6):
        tx = cx + 0.24 + i * 0.05
        q.line([(tx, cy - 0.034, 0.346), (tx, cy + 0.034, 0.346)],
               (150, 158, 150), 0.8)
    # Belt clip + lock + label lines proud of the +Y flank.
    q.box((cx - 0.10, cy + 0.105, 0.12), (cx + 0.10, cy + 0.135, 0.44),
          (100, 110, 105), (84, 94, 89), (118, 128, 122))
    q.dot((cx - 0.06, cy + 0.137, 0.38), 0.7, (70, 78, 73, 255))
    q.dot((cx + 0.06, cy + 0.137, 0.18), 0.7, (70, 78, 73, 255))
    q.box((cx - 0.06, cy + 0.105, 0.475), (cx + 0.06, cy + 0.135, 0.53),
          (150, 60, 52), (150, 60, 52), (150, 60, 52))
    q.fp(cx - 0.14, cx + 0.02, cy + 0.111, 0.16, 0.30, (240, 200, 110))
    q.line([(cx - 0.12, cy + 0.112, 0.20), (cx + 0.0, cy + 0.112, 0.20)],
           (170, 120, 60), 0.8)
    q.line([(cx - 0.12, cy + 0.112, 0.26), (cx + 0.0, cy + 0.112, 0.26)],
           (170, 120, 60), 0.8)


def vacuum_pump(q, cx, cy, P):
    """Vacuum pump: skid base, blue body, carry handle, gauge and sight."""
    for sy in (cy - 0.10, cy + 0.10):
        q.box((cx - 0.32, sy - 0.045, 0.0), (cx + 0.32, sy + 0.045, 0.12),
              (70, 82, 92), (58, 68, 78), (86, 98, 108))
    q.box((cx - 0.30, cy - 0.13, 0.10), (cx + 0.30, cy + 0.13, 0.52),
          (92, 132, 162), (72, 106, 132), (114, 154, 184))
    q.box((cx - 0.30, cy - 0.13, 0.515), (cx + 0.30, cy + 0.13, 0.55),
          (104, 144, 174), (72, 106, 132), (124, 164, 194))
    # Motor cap on the +X end + cooling fins.
    q.box((cx + 0.28, cy - 0.10, 0.16), (cx + 0.39, cy + 0.10, 0.46),
          (70, 90, 110), (58, 76, 94), (86, 106, 128))
    for fz in (0.22, 0.28, 0.34, 0.40):
        q.line([(cx + 0.392, cy - 0.09, fz), (cx + 0.392, cy + 0.09, fz)],
               (120, 140, 158), 0.8)
    # Carry handle: far post, near post, grip bar last.
    q.box((cx - 0.20, cy - 0.04, 0.50), (cx - 0.14, cy + 0.04, 0.72),
          (60, 75, 95), (60, 75, 95), (60, 75, 95))
    q.box((cx + 0.14, cy - 0.04, 0.50), (cx + 0.20, cy + 0.04, 0.72),
          (60, 75, 95), (60, 75, 95), (60, 75, 95))
    q.box((cx - 0.24, cy - 0.045, 0.70), (cx + 0.24, cy + 0.045, 0.80),
          (66, 82, 102), (66, 82, 102), (66, 82, 102))
    # Intake port + cap on top, gauge + sight glass on the +Y face.
    _cylinder(q, cx + 0.12, cy - 0.04, 0.52, 0.64, 0.045,
              (130, 140, 135), (100, 112, 106), (150, 160, 155), n=12)
    q.box((cx + 0.06, cy - 0.10, 0.62), (cx + 0.18, cy + 0.02, 0.70),
          (150, 110, 70), (122, 90, 56), (170, 130, 88))
    fy = cy + 0.132
    q.disc_y(cx - 0.12, fy, 0.36, 0.095, (70, 80, 90))
    q.disc_y(cx - 0.12, fy + 0.002, 0.36, 0.075, (235, 240, 235))
    q.line([(cx - 0.16, fy + 0.004, 0.33), (cx - 0.09, fy + 0.004, 0.39)],
           (180, 90, 60), 1.2)
    q.dot((cx - 0.12, fy + 0.004, 0.36), 0.9, (70, 80, 90, 255))
    q.fp(cx + 0.02, cx + 0.12, fy, 0.18, 0.30, (190, 220, 200))
    q.line([(cx + 0.02, fy + 0.001, 0.24), (cx + 0.12, fy + 0.001, 0.24)],
           (120, 150, 130), 1.0)


def manifold_gauge(q, cx, cy, P):
    """Service manifold: brass bar, two gauges, knobs, twin hoses to floor."""
    # Hoses first (they hang behind/in front, tops buried in the bar).
    q.poly([(cx - 0.30, cy - 0.10, 0.50), (cx - 0.24, cy - 0.10, 0.50),
            (cx - 0.26, cy - 0.10, 0.0), (cx - 0.32, cy - 0.10, 0.0)],
           (165, 82, 62))
    q.poly([(cx + 0.24, cy + 0.02, 0.50), (cx + 0.30, cy + 0.02, 0.50),
            (cx + 0.32, cy + 0.02, 0.0), (cx + 0.26, cy + 0.02, 0.0)],
           (82, 112, 152))
    # Brass bar hero over the hose tops.
    q.box((cx - 0.28, cy - 0.07, 0.42), (cx + 0.28, cy + 0.07, 0.56),
          (200, 160, 95), (162, 128, 74), (218, 180, 114))
    # Stems rise out of the bar into the gauge backs.
    for sx in (cx - 0.17, cx + 0.17):
        q.box((sx - 0.035, cy - 0.035, 0.54), (sx + 0.035, cy + 0.035, 0.68),
              (150, 118, 70), (122, 96, 56), (170, 138, 86))
    # Gauge rims face +Y (near), bodies painted after the stems.
    for gx in (cx - 0.17, cx + 0.17):
        q.disc_y(gx, cy + 0.035, 0.74, 0.155, (80, 90, 96))
    for gx in (cx - 0.17, cx + 0.17):
        q.disc_y(gx, cy + 0.037, 0.74, 0.125, (238, 242, 238))
        for k in range(8):
            a = math.pi * (0.15 + 0.7 * k / 7)
            q.dot((gx + 0.10 * math.cos(a), cy + 0.039,
                   0.74 + 0.10 * math.sin(a)), 0.55, (90, 100, 106, 255))
        q.line([(gx - 0.05, cy + 0.040, 0.70), (gx + 0.04, cy + 0.040, 0.78)],
               (180, 90, 60), 1.2)
        q.dot((gx, cy + 0.040, 0.74), 0.9, (70, 80, 88, 255))
    # Knob handles under the bar + center hook dot.
    for kx in (cx - 0.10, cx + 0.10):
        q.box((kx - 0.03, cy - 0.03, 0.28), (kx + 0.03, cy + 0.03, 0.43),
              (110, 72, 52), (92, 60, 44), (128, 86, 62))
        q.box((kx - 0.055, cy - 0.02, 0.30), (kx + 0.055, cy + 0.02, 0.35),
              (130, 88, 62), (130, 88, 62), (130, 88, 62))
    # Coupler fittings terminate both hoses at the floor (visible endpoints).
    q.box((cx - 0.345, cy - 0.135, 0.0), (cx - 0.225, cy - 0.065, 0.14),
          (190, 150, 90), (154, 120, 72), (208, 170, 108))
    q.box((cx - 0.33, cy - 0.13, 0.08), (cx - 0.24, cy - 0.07, 0.22),
          (150, 118, 70), (150, 118, 70), (150, 118, 70))
    q.box((cx + 0.225, cy - 0.015, 0.0), (cx + 0.345, cy + 0.055, 0.14),
          (190, 150, 90), (154, 120, 72), (208, 170, 108))
    q.box((cx + 0.24, cy - 0.01, 0.08), (cx + 0.33, cy + 0.05, 0.22),
          (150, 118, 70), (150, 118, 70), (150, 118, 70))


def refrigerant_bottle(q, cx, cy, P):
    """Refrigerant bottle: grey-green cylinder, base ring, collar, valve."""
    _cylinder(q, cx, cy, 0.02, 0.10, 0.275,
              (82, 96, 90), (68, 80, 76), (100, 114, 108), n=24)
    # Hero body over the base ring + embossed band rings after the body.
    _cylinder(q, cx, cy, 0.06, 0.60, 0.26,
              (165, 185, 175), (132, 152, 142), (185, 205, 195), n=32)
    _cylinder(q, cx, cy, 0.30, 0.325, 0.266,
              (110, 130, 150), (90, 108, 126), (110, 130, 150), n=24)
    _cylinder(q, cx, cy, 0.375, 0.40, 0.266,
              (110, 130, 150), (90, 108, 126), (110, 130, 150), n=24)
    # Shoulder step narrows to the collar, collar rises into the valve.
    _cylinder(q, cx, cy, 0.56, 0.68, 0.20,
              (140, 162, 152), (112, 132, 122), (160, 182, 172), n=24)
    _cylinder(q, cx, cy, 0.62, 0.74, 0.10,
              (130, 142, 136), (104, 116, 110), (150, 162, 156), n=16)
    # Red valve bonnet (accent) + dark T-handle + brass stem nut.
    q.box((cx - 0.06, cy - 0.06, 0.72), (cx + 0.06, cy + 0.06, 0.84),
          (160, 70, 55), (130, 58, 46), (180, 86, 68))
    _cylinder(q, cx, cy, 0.82, 0.90, 0.028,
              (190, 150, 90), (154, 120, 72), (208, 170, 108), n=10)
    q.box((cx - 0.14, cy - 0.035, 0.88), (cx + 0.14, cy + 0.035, 0.94),
          (80, 88, 92), (66, 74, 78), (96, 104, 108))
    q.dot((cx + 0.10, cy + 0.037, 0.91), 0.7, (200, 120, 70, 255))
    # Capped service port on the +Y flank: port + amber cap + dot.
    q.box((cx + 0.08, cy + 0.20, 0.30), (cx + 0.16, cy + 0.30, 0.38),
          (168, 134, 76), (168, 134, 76), (168, 134, 76))
    q.box((cx + 0.075, cy + 0.195, 0.36), (cx + 0.165, cy + 0.305, 0.44),
          (210, 150, 80), (172, 122, 64), (226, 168, 96))
    q.dot((cx + 0.12, cy + 0.307, 0.40), 0.8, (120, 70, 60, 255))


def torque_wrench(q, cx, cy, P):
    """Torque wrench lying grounded: long visible shaft between a compact
    grip and a slim head (reviewer verdict: shaft must span ~50% of the
    tool or it reads as disjoint boxes)."""
    # Steel bar hero resting directly on the plinth (like the level).
    q.boxg((cx - 0.42, cy - 0.055, 0.02), (cx + 0.16, cy + 0.055, 0.16),
          (155, 163, 158), (126, 136, 130), (176, 184, 179))
    # One elongated rubber grip (no center seam) + butt ring only.
    q.boxg((cx - 0.42, cy - 0.07, 0.02), (cx - 0.26, cy + 0.07, 0.19),
          (75, 85, 90), (62, 70, 76), (90, 100, 106))
    q.boxg((cx - 0.50, cy - 0.065, 0.02), (cx - 0.41, cy + 0.065, 0.19),
          (110, 118, 112), (92, 100, 94), (128, 136, 130))
    q.dot((cx - 0.502, cy, 0.105), 0.9, (70, 76, 72, 255))
    for gx in (cx - 0.39, cx - 0.35, cx - 0.31):
        q.line([(gx, cy + 0.072, 0.05), (gx, cy + 0.072, 0.12)],
               (140, 152, 156), 0.8)
    # Scale window + six ticks + red pointer, centered on the shaft.
    q.fp(cx - 0.10, cx + 0.02, cy + 0.056, 0.05, 0.14, (200, 208, 202))
    for i in range(6):
        tx = cx - 0.08 + i * 0.016
        q.line([(tx, cy + 0.057, 0.06), (tx, cy + 0.057, 0.12)],
               (110, 120, 114), 0.8)
    q.line([(cx - 0.10, cy + 0.058, 0.095), (cx + 0.02, cy + 0.058, 0.095)],
           (170, 70, 55), 1.5)
    # Slim head (~17% of length, barely taller than the shaft).
    q.boxg((cx + 0.14, cy - 0.08, 0.02), (cx + 0.28, cy + 0.08, 0.22),
          (155, 163, 158), (126, 136, 130), (176, 184, 179))
    q.boxg((cx + 0.175, cy + 0.078, 0.10), (cx + 0.225, cy + 0.098, 0.16),
          (170, 70, 55), (170, 70, 55), (170, 70, 55))
    # Round ratchet cap centered on the head top + small square drive.
    _cylinder(q, cx + 0.21, cy, 0.215, 0.27, 0.062,
              (140, 148, 142), (112, 120, 114), (160, 168, 162), n=16)
    q.boxg((cx + 0.19, cy - 0.025, 0.265), (cx + 0.23, cy + 0.025, 0.34),
          (110, 118, 112), (92, 100, 94), (128, 136, 130))


def hole_saw(q, cx, cy, P):
    """Hole saw: red cup, tooth dots on the near rim, arbor and shank."""
    # No cap, no sealing disc here: the band mouth ring is 0.006 wide
    # (subpixel slit, invisible) while ANY flat disc at this spot paints
    # over the cup front as a phantom blob (call-order painter).
    _cylinder(q, cx, cy, 0.02, 0.42, 0.24,
              (188, 92, 70), (150, 72, 54), (206, 110, 86), n=32)
    _cylinder(q, cx, cy, 0.115, 0.145, 0.246,
              (140, 65, 50), (140, 65, 50), (140, 65, 50), rim=False,
              top_ring=False, n=24)
    # Arbor rises out of the cup top + hex shank + pilot bit.
    _cylinder(q, cx, cy, 0.40, 0.68, 0.045,
              (130, 138, 132), (104, 112, 106), (150, 158, 152), n=12)
    q.box((cx - 0.05, cy - 0.05, 0.66), (cx + 0.05, cy + 0.05, 0.82),
          (110, 118, 112), (92, 100, 94), (128, 136, 130))
    _cylinder(q, cx, cy, 0.80, 0.92, 0.02,
              (150, 158, 152), (120, 130, 124), (170, 178, 172), n=8)
    # Tooth dots along the near rim arc (small, painted after the cup).
    for k in range(7):
        a = math.pi * (0.15 + 0.7 * k / 6)
        q.dot((cx + 0.24 * math.cos(a), cy + 0.24 * math.sin(a) * 0.35 + 0.06,
               0.44), 0.6, (240, 200, 130, 255))
    q.line([(cx - 0.20, cy + 0.20, 0.22), (cx + 0.20, cy + 0.20, 0.22)],
           (140, 65, 50), 0.8)


def inspection_cam(q, cx, cy, P):
    """Inspection camera: body, screen on +Y, buttons, probe neck and head."""
    q.box((cx - 0.16, cy - 0.09, 0.10), (cx + 0.16, cy + 0.09, 0.55),
          (70, 115, 125), (56, 94, 102), (88, 135, 145))
    q.box((cx - 0.16, cy - 0.09, 0.545), (cx + 0.16, cy + 0.09, 0.58),
          (82, 127, 137), (56, 94, 102), (98, 145, 155))
    # Screen frame + glass + scan lines proud of the +Y face.
    q.box((cx - 0.12, cy + 0.085, 0.30), (cx + 0.12, cy + 0.115, 0.50),
          (60, 75, 80), (60, 75, 80), (60, 75, 80))
    q.fp(cx - 0.10, cx + 0.10, cy + 0.116, 0.325, 0.475, (200, 225, 220))
    for sz in (0.36, 0.40, 0.44):
        q.line([(cx - 0.08, cy + 0.117, sz), (cx + 0.08, cy + 0.117, sz)],
               (120, 160, 150), 0.8)
    q.dot((cx + 0.05, cy + 0.118, 0.40), 0.8, (240, 170, 90, 255))
    for bx in (cx - 0.09, cx - 0.03, cx + 0.03):
        q.dot((bx, cy + 0.092, 0.20), 0.8, (200, 120, 70, 255))
    # Probe neck rises out of the top + head + lens, all overlapping.
    _cylinder(q, cx - 0.06, cy, 0.54, 0.70, 0.04,
              (110, 120, 114), (88, 98, 92), (130, 140, 134), n=12)
    q.box((cx - 0.12, cy - 0.05, 0.68), (cx + 0.0, cy + 0.05, 0.84),
          (90, 100, 105), (74, 84, 88), (108, 118, 122))
    q.disc_y(cx - 0.06, cy + 0.052, 0.76, 0.035, (60, 70, 76))
    q.dot((cx - 0.06, cy + 0.054, 0.76), 1.0, (25, 35, 40, 255))
    q.dot((cx - 0.10, cy + 0.054, 0.70), 0.6, (240, 220, 150, 255))


def tool_bag(q, cx, cy, P):
    """Tool bag: base trim, fabric body, open mouth, handles, pockets."""
    q.box((cx - 0.35, cy - 0.16, 0.02), (cx + 0.35, cy + 0.16, 0.16),
          (120, 66, 52), (98, 54, 42), (140, 80, 62))
    q.box((cx - 0.34, cy - 0.15, 0.10), (cx + 0.34, cy + 0.15, 0.52),
          (172, 88, 70), (140, 70, 56), (192, 106, 86))
    # Dark open mouth between back and front walls (walls rise above it).
    q.box((cx - 0.30, cy - 0.06, 0.48), (cx + 0.30, cy + 0.06, 0.585),
          (66, 70, 68), (66, 70, 68), (66, 70, 68))
    q.box((cx - 0.30, cy - 0.15, 0.48), (cx + 0.30, cy - 0.055, 0.62),
          (162, 80, 63), (132, 64, 50), (182, 98, 78))
    # Tools peeking out of the mouth (bottoms buried, walls cover them).
    q.box((cx - 0.16, cy - 0.03, 0.55), (cx - 0.10, cy + 0.03, 0.76),
          (200, 150, 80), (200, 150, 80), (200, 150, 80))
    q.box((cx + 0.02, cy - 0.03, 0.55), (cx + 0.08, cy + 0.03, 0.72),
          (90, 140, 160), (90, 140, 160), (90, 140, 160))
    q.box((cx - 0.30, cy + 0.055, 0.48), (cx + 0.30, cy + 0.15, 0.62),
          (182, 98, 78), (148, 78, 62), (202, 116, 94))
    q.line([(cx - 0.26, cy + 0.152, 0.57), (cx + 0.26, cy + 0.152, 0.57)],
           (230, 180, 90), 1.0)
    # Carry handles: far post, near post, grip bar last.
    q.box((cx - 0.22, cy - 0.05, 0.58), (cx - 0.16, cy + 0.03, 0.80),
          (120, 62, 50), (120, 62, 50), (120, 62, 50))
    q.box((cx + 0.16, cy - 0.03, 0.58), (cx + 0.22, cy + 0.05, 0.80),
          (120, 62, 50), (120, 62, 50), (120, 62, 50))
    q.box((cx - 0.26, cy - 0.04, 0.78), (cx + 0.26, cy + 0.04, 0.88),
          (130, 70, 56), (130, 70, 56), (130, 70, 56))
    # Front pocket + flap line + side pocket on +X, all proud, painted last.
    q.box((cx - 0.20, cy + 0.145, 0.14), (cx + 0.20, cy + 0.185, 0.40),
          (162, 80, 63), (162, 80, 63), (162, 80, 63))
    q.line([(cx - 0.18, cy + 0.187, 0.35), (cx + 0.18, cy + 0.187, 0.35)],
           (230, 180, 90), 1.0)
    q.box((cx + 0.335, cy - 0.08, 0.12), (cx + 0.385, cy + 0.08, 0.34),
          (150, 74, 58), (150, 74, 58), (150, 74, 58))
    q.dot((cx + 0.387, cy, 0.28), 0.7, (230, 180, 90, 255))


PROPS = {
    "drill": {"fn": drill, "focus": (0.0, 0.15, 0.30), "k": 600,
              "plinth": (0.0, 0.15, 0.72, 0.38),
              "brief": "cordless drill with chuck and battery"},
    "grinder": {"fn": grinder, "focus": (0.0, 0.15, 0.32), "k": 580,
                "plinth": (0.0, 0.15, 0.75, 0.38),
                "brief": "angle grinder with disc and guard"},
    "multimeter": {"fn": multimeter, "focus": (0.0, 0.15, 0.37), "k": 580,
                   "plinth": (0.0, 0.15, 0.52, 0.32),
                   "brief": "multimeter with screen and dial"},
    "pipe-wrench": {"fn": pipe_wrench, "focus": (0.0, 0.15, 0.28), "k": 600,
                    "plinth": (0.0, 0.15, 0.60, 0.36),
                    "brief": "pipe wrench with jaws"},
    "level": {"fn": level, "focus": (0.0, 0.15, 0.16), "k": 560,
              "plinth": (0.0, 0.15, 0.62, 0.36),
              "brief": "spirit level bar with vials"},
    "hammer": {"fn": hammer, "focus": (0.0, 0.15, 0.40), "k": 600,
               "plinth": (0.0, 0.15, 0.58, 0.34),
               "brief": "claw hammer"},
    "screwdrivers": {"fn": screwdrivers, "focus": (0.0, 0.15, 0.43), "k": 540,
                     "plinth": (0.0, 0.15, 0.55, 0.34),
                     "brief": "screwdriver set in holder"},
    "tape-measure": {"fn": tape_measure, "focus": (0.0, 0.15, 0.27), "k": 600,
                     "plinth": (0.0, 0.15, 0.62, 0.36),
                     "brief": "tape measure box with belt clip"},
    "vacuum-pump": {"fn": vacuum_pump, "focus": (0.0, 0.15, 0.38), "k": 550,
                    "plinth": (0.0, 0.15, 0.62, 0.38),
                    "brief": "vacuum pump box with handle and gauge"},
    "manifold-gauge": {"fn": manifold_gauge, "focus": (0.0, 0.15, 0.42),
                       "k": 540,
                       "plinth": (0.0, 0.15, 0.58, 0.36),
                       "brief": "service manifold with two gauges and hoses"},
    "refrigerant-bottle": {"fn": refrigerant_bottle,
                            "focus": (0.0, 0.15, 0.46), "k": 520,
                            "plinth": (0.0, 0.15, 0.52, 0.32),
                            "brief": "refrigerant bottle with valve and cap"},
    "torque-wrench": {"fn": torque_wrench, "focus": (0.0, 0.15, 0.23),
                      "k": 600,
                      "plinth": (0.0, 0.15, 0.60, 0.36),
                      "brief": "torque wrench with handle"},
    "hole-saw": {"fn": hole_saw, "focus": (0.0, 0.15, 0.45), "k": 560,
                 "plinth": (0.0, 0.15, 0.52, 0.32),
                 "brief": "hole saw cup with arbor"},
    "inspection-cam": {"fn": inspection_cam, "focus": (0.0, 0.15, 0.45),
                       "k": 540,
                       "plinth": (0.0, 0.15, 0.52, 0.32),
                       "brief": "inspection camera with screen and probe"},
    "tool-bag": {"fn": tool_bag, "focus": (0.0, 0.15, 0.44), "k": 528,
                 "plinth": (0.0, 0.15, 0.62, 0.38),
                 "brief": "tool bag with handles and pockets"},
}
