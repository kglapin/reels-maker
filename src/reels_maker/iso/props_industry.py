"""Iso gallery props batch: industry (forklift, pallets, machines, dock).

Builders take ``(q, cx, cy, P)`` with all coordinates relative to the
placement center. Rules: overlap mating parts >= 0.005 (never
exact-touch), NO contact_shadow anywhere, mid-tone palette (nothing below
RGB 60 except tiny dots), hero element biggest, stubs start AT parent
surfaces, proud details painted AFTER parents, details only on +X/+Y
faces, no text decals (embossed lines only).
"""
from __future__ import annotations

import math

from .world import _cylinder


def forklift(q, cx, cy, P):
    """Forklift: yellow body hero, rear counterweight, mast, forks, cabin, wheels."""
    # Rear counterweight first (far, -X), then far wheels, then hero body.
    q.boxg((cx - 0.50, cy - 0.15, 0.12), (cx - 0.375, cy + 0.15, 0.50),
          (200, 150, 70), (160, 118, 56), (218, 170, 88))
    for wx in (cx - 0.24, cx + 0.10):
        q.disc_y(wx, cy - 0.175, 0.13, 0.13, (62, 70, 64))
        q.disc_y(wx, cy - 0.177, 0.13, 0.06, (150, 158, 148))
    # Hero body (overlaps counterweight in X, covers far-wheel tops).
    q.boxg((cx - 0.38, cy - 0.17, 0.15), (cx + 0.20, cy + 0.17, 0.55),
          (235, 185, 95), (190, 145, 70), (248, 205, 120))
    # Seat + steering column on the body top (after body, mostly above it).
    q.boxg((cx - 0.22, cy - 0.09, 0.545), (cx - 0.02, cy + 0.09, 0.66),
          (90, 100, 92), (70, 80, 72), (110, 120, 112))
    q.boxg((cx + 0.06, cy - 0.025, 0.545), (cx + 0.10, cy + 0.025, 0.78),
          (80, 90, 82), (64, 72, 66), (98, 108, 100))
    q.disc_y(cx + 0.08, cy + 0.027, 0.78, 0.05, (64, 72, 66))
    # Cabin posts + roof over the rear half.
    for py in (cy - 0.14, cy + 0.14):
        q.boxg((cx - 0.32, py - 0.03, 0.545), (cx - 0.28, py + 0.03, 1.00),
              (90, 100, 92), (70, 80, 72), (110, 120, 112))
    q.boxg((cx - 0.36, cy - 0.17, 0.99), (cx + 0.04, cy + 0.17, 1.06),
          (150, 160, 150), (120, 132, 122), (172, 182, 172))
    # Mast rails (near, +X) + crossbars, then carriage + forks last.
    for ry in (cy - 0.14, cy + 0.14):
        q.boxg((cx + 0.28, ry - 0.03, 0.0), (cx + 0.34, ry + 0.03, 1.05),
              (96, 106, 98), (76, 86, 78), (116, 126, 118))
    for cz in (0.30, 0.85):
        q.boxg((cx + 0.275, cy - 0.17, cz), (cx + 0.345, cy + 0.17, cz + 0.07),
              (110, 120, 112), (88, 98, 90), (130, 140, 132))
    q.boxg((cx + 0.335, cy - 0.16, 0.05), (cx + 0.40, cy + 0.16, 0.28),
          (130, 140, 132), (104, 114, 106), (150, 160, 152))
    for fy in (cy - 0.085, cy + 0.085):
        q.boxg((cx + 0.34, fy - 0.035, 0.02), (cx + 0.70, fy + 0.035, 0.08),
              (150, 160, 150), (120, 132, 122), (172, 182, 172))
    # Near wheels after the body; stripe + lights on the +Y flank.
    for wx in (cx - 0.24, cx + 0.10):
        q.disc_y(wx, cy + 0.175, 0.13, 0.13, (62, 70, 64))
        q.disc_y(wx, cy + 0.177, 0.13, 0.06, (150, 158, 148))
    q.dot((cx - 0.24, cy + 0.179, 0.13), 0.9, (90, 96, 90, 255))
    q.dot((cx + 0.10, cy + 0.179, 0.13), 0.9, (90, 96, 90, 255))
    q.fp(cx - 0.30, cx + 0.12, cy + 0.171, 0.30, 0.38, (70, 84, 72))
    q.dot((cx + 0.201, cy + 0.08, 0.45), 1.0, (255, 240, 180, 255))
    # Headlights on the visible +Y flank, above the stripe: dark
    # housings with a bright lens each (a bare dot reads as dust).
    for hx in (cx - 0.05, cx + 0.15):
        q.boxg((hx - 0.028, cy + 0.168, 0.415), (hx + 0.028, cy + 0.185, 0.485),
              (70, 80, 72), (56, 66, 58), (88, 98, 90))
        q.dot((hx, cy + 0.187, 0.45), 1.5, (255, 252, 235, 255))


def pallet(q, cx, cy, P):
    """Wooden euro pallet: bottom boards, block grid, top slat deck."""
    wood_l, wood_d, wood_t = (208, 162, 108), (160, 120, 76), (222, 180, 126)
    # Bottom boards (far -> near).
    for by in (cy - 0.28, cy, cy + 0.28):
        q.box((cx - 0.45, by - 0.06, 0.0), (cx + 0.45, by + 0.06, 0.025),
              wood_l, wood_d, wood_t)
    # Block grid 3x3 (far rows first).
    for by in (cy - 0.28, cy, cy + 0.28):
        for bx in (cx - 0.36, cx, cx + 0.36):
            q.box((bx - 0.06, by - 0.06, 0.015), (bx + 0.06, by + 0.06, 0.12),
                  wood_l, wood_d, wood_t)
    # Top slats (far -> near), bottoms sunk into the blocks.
    for i, sy in enumerate((cy - 0.28, cy - 0.14, cy, cy + 0.14, cy + 0.28)):
        q.box((cx - 0.45, sy - 0.05, 0.11), (cx + 0.45, sy + 0.05, 0.16),
              wood_l, wood_d, wood_t)
    # Embossed grain lines on the top faces (no text).
    for sy in (cy - 0.28, cy, cy + 0.28):
        q.line([(cx - 0.40, sy, 0.162), (cx + 0.40, sy, 0.162)],
               (150, 112, 70), 0.8)


def pallet_jack(q, cx, cy, P):
    """Hand pallet jack: two forks, rear pivot housing, handle, wheels."""
    red_l, red_d, red_t = (205, 100, 85), (160, 74, 62), (220, 125, 105)
    steel_l, steel_d = (140, 150, 142), (108, 118, 110)
    # Far fork wheels first, then far fork over them.
    for wx in (cx + 0.30, cx + 0.42):
        q.disc_y(wx, cy - 0.185, 0.035, 0.035, (70, 78, 72))
    q.box((cx - 0.42, cy - 0.17, 0.03), (cx + 0.48, cy - 0.05, 0.10),
          red_l, red_d, red_t)
    # Rear pivot housing + connecting bar (far, -X).
    q.box((cx - 0.52, cy - 0.10, 0.02), (cx - 0.40, cy + 0.10, 0.22),
          red_l, red_d, red_t)
    q.box((cx - 0.50, cy - 0.05, 0.20), (cx - 0.44, cy + 0.05, 0.55),
          steel_l, steel_d, steel_l)
    # Handle: two side bars rising out of the housing + grip.
    for hy in (cy - 0.055, cy + 0.055):
        q.box((cx - 0.56, hy - 0.025, 0.15), (cx - 0.50, hy + 0.025, 0.86),
              red_l, red_d, red_t)
    q.box((cx - 0.575, cy - 0.08, 0.855), (cx - 0.485, cy + 0.08, 0.92),
          (90, 100, 92), (70, 80, 72), (110, 120, 112))
    # Steering wheels at the rear + near fork + near wheels last.
    q.disc_y(cx - 0.46, cy - 0.10, 0.07, 0.07, (70, 78, 72))
    q.disc_y(cx - 0.46, cy + 0.10, 0.07, 0.07, (70, 78, 72))
    q.box((cx - 0.42, cy + 0.05, 0.03), (cx + 0.48, cy + 0.17, 0.10),
          red_l, red_d, red_t)
    for wx in (cx + 0.30, cx + 0.42):
        q.disc_y(wx, cy + 0.185, 0.035, 0.035, (70, 78, 72))
    q.dot((cx - 0.46, cy + 0.102, 0.07), 0.8, (150, 158, 148, 255))


def crates(q, cx, cy, P):
    """Stack of crates and boxes: big wood hero, mid crate, cardboard top."""
    # Hero bottom crate + corner battens on the +Y face.
    q.box((cx - 0.35, cy - 0.28, 0.0), (cx + 0.35, cy + 0.28, 0.45),
          (205, 160, 105), (160, 122, 76), (220, 178, 122))
    for bx in (cx - 0.31, cx + 0.27):
        q.box((bx, cy + 0.275, 0.005), (bx + 0.04, cy + 0.295, 0.445),
              (160, 122, 76), (140, 106, 66), (176, 138, 90))
    q.line([(cx - 0.30, cy + 0.296, 0.15), (cx + 0.30, cy + 0.296, 0.15)],
           (150, 112, 70), 0.9)
    q.line([(cx - 0.30, cy + 0.296, 0.30), (cx + 0.30, cy + 0.296, 0.30)],
           (150, 112, 70), 0.9)
    # Mid crate (bottom sunk into the hero) + slat lines.
    q.box((cx - 0.28, cy - 0.22, 0.44), (cx + 0.28, cy + 0.22, 0.80),
          (195, 150, 98), (152, 115, 72), (210, 168, 115))
    q.line([(cx - 0.24, cy + 0.221, 0.62), (cx + 0.24, cy + 0.221, 0.62)],
           (142, 106, 66), 0.9)
    # Cardboard top box + tape band (embossed, no text).
    q.box((cx - 0.20, cy - 0.16, 0.79), (cx + 0.20, cy + 0.16, 1.05),
          (228, 202, 160), (186, 160, 122), (240, 216, 178))
    q.box((cx - 0.035, cy - 0.165, 0.79), (cx + 0.035, cy + 0.165, 1.055),
          (200, 172, 132), (200, 172, 132), (200, 172, 132))


def conveyor(q, cx, cy, P):
    """Conveyor belt on legs: frame hero, dark belt, end rollers, motor."""
    steel_l, steel_d, steel_t = (150, 162, 152), (118, 130, 120), (172, 184, 174)
    # Frame hero first (legs hang below its bottom edge, drawn after).
    q.boxg((cx - 0.55, cy - 0.14, 0.45), (cx + 0.55, cy + 0.14, 0.58),
          steel_l, steel_d, steel_t)
    # Dark belt proud of the frame top.
    q.boxg((cx - 0.55, cy - 0.12, 0.575), (cx + 0.55, cy + 0.12, 0.63),
          (74, 84, 78), (66, 76, 70), (92, 102, 96))
    # End roller housings + disc caps on the +/-X faces.
    q.boxg((cx - 0.61, cy - 0.13, 0.44), (cx - 0.545, cy + 0.13, 0.59),
          steel_l, steel_d, steel_t)
    q.boxg((cx + 0.545, cy - 0.13, 0.44), (cx + 0.61, cy + 0.13, 0.59),
          steel_l, steel_d, steel_t)
    q.disc_x(cx - 0.611, cy, 0.515, 0.075, (90, 100, 92))
    q.disc_x(cx + 0.611, cy, 0.515, 0.075, (90, 100, 92))
    # Drive motor slung under the frame (before the legs).
    q.boxg((cx + 0.08, cy - 0.12, 0.20), (cx + 0.30, cy + 0.05, 0.40),
          (110, 125, 115), (88, 102, 92), (130, 145, 135))
    q.boxg((cx + 0.17, cy - 0.125, 0.395), (cx + 0.21, cy + 0.055, 0.46),
          (88, 102, 92), (88, 102, 92), (88, 102, 92))
    # Legs far -> near, feet sunk; crossbars between the pairs.
    for lx, ly in ((cx - 0.40, cy - 0.10), (cx - 0.40, cy + 0.10),
                   (cx + 0.40, cy - 0.10), (cx + 0.40, cy + 0.10)):
        q.boxg((lx - 0.035, ly - 0.035, -0.02), (lx + 0.035, ly + 0.035, 0.46),
              steel_l, steel_d, steel_t)
    for lx in (cx - 0.40, cx + 0.40):
        q.boxg((lx - 0.03, cy - 0.10, 0.12), (lx + 0.03, cy + 0.10, 0.18),
              steel_d, steel_d, steel_d)
    # Side guide rail on the +Y edge (trim, painted last).
    q.boxg((cx - 0.55, cy + 0.135, 0.625), (cx + 0.55, cy + 0.165, 0.70),
          steel_l, steel_d, steel_t)


def press(q, cx, cy, P):
    """Machine press: spine + beam frame hero, ram cylinder, bolster plate."""
    frame_l, frame_d, frame_t = (140, 155, 165), (108, 122, 132), (165, 178, 186)
    # Back spine (far) then base bolster bed.
    q.boxg((cx - 0.40, cy - 0.15, 0.15), (cx - 0.28, cy + 0.15, 1.05),
          frame_l, frame_d, frame_t)
    q.boxg((cx - 0.38, cy - 0.25, 0.0), (cx + 0.34, cy + 0.25, 0.18),
          (150, 160, 152), (118, 128, 120), (172, 182, 174))
    # Press plate sunk into the bed top + hazard stripe on the +Y face.
    q.boxg((cx - 0.04, cy - 0.14, 0.175), (cx + 0.28, cy + 0.14, 0.24),
          (120, 132, 124), (96, 108, 100), (142, 154, 146))
    q.fp(cx - 0.30, cx + 0.26, cy + 0.251, 0.05, 0.11, (200, 150, 70))
    # Top beam (high above the bed: no screen overlap, order is free).
    q.boxg((cx - 0.40, cy - 0.15, 0.90), (cx + 0.30, cy + 0.15, 1.06),
          frame_l, frame_d, frame_t)
    # Ram cylinder under the beam, bottom proud of the beam face.
    _cylinder(q, cx + 0.12, cy, 0.55, 0.905, 0.09,
              (170, 182, 174), (120, 132, 124), (190, 200, 192), n=20)
    _cylinder(q, cx + 0.12, cy, 0.42, 0.56, 0.115,
              (120, 132, 124), (92, 102, 94), (142, 154, 146), n=20)
    # Plunger rod down out of the collar + press foot meeting the bolster
    # plate (foot bottom sunk into the plate: contact, never a gap).
    _cylinder(q, cx + 0.12, cy, 0.28, 0.44, 0.06,
              (170, 182, 174), (120, 132, 124), (190, 200, 192), n=16)
    q.boxg((cx + 0.01, cy - 0.11, 0.235), (cx + 0.23, cy + 0.11, 0.31),
          (120, 132, 124), (96, 108, 100), (142, 154, 146))
    # Control box on the beam +Y face + buttons (proud, painted last).
    q.boxg((cx - 0.30, cy + 0.145, 0.92), (cx - 0.10, cy + 0.20, 1.04),
          (90, 102, 110), (72, 84, 92), (110, 122, 130))
    q.dot((cx - 0.25, cy + 0.202, 0.99), 1.0, (255, 176, 92, 255))
    q.dot((cx - 0.15, cy + 0.202, 0.99), 1.0, (110, 190, 170, 255))
    q.line([(cx - 0.28, cy + 0.202, 0.945), (cx - 0.12, cy + 0.202, 0.945)],
           (150, 164, 172), 0.8)


def workbench(q, cx, cy, P):
    """Workbench: slab hero, legs, shelf, pegboard, vice and hand tools."""
    wood_l, wood_d, wood_t = (215, 180, 135), (168, 138, 98), (228, 196, 152)
    steel_l, steel_d = (140, 150, 142), (108, 118, 110)
    # Pegboard panel (far, -Y) first.
    q.box((cx - 0.45, cy - 0.25, 0.69), (cx + 0.45, cy - 0.21, 1.10),
          (170, 160, 140), (140, 132, 114), (188, 178, 158))
    # Legs far -> near, then lower shelf threaded through them.
    for lx, ly in ((cx - 0.42, cy - 0.18), (cx + 0.42, cy - 0.18),
                   (cx - 0.42, cy + 0.18), (cx + 0.42, cy + 0.18)):
        q.box((lx - 0.04, ly - 0.04, -0.02), (lx + 0.04, ly + 0.04, 0.63),
              steel_l, steel_d, steel_l)
    q.box((cx - 0.42, cy - 0.18, 0.14), (cx + 0.42, cy + 0.18, 0.19),
          (120, 130, 122), (96, 106, 98), (140, 150, 142))
    # Hero slab over the leg tops.
    q.box((cx - 0.50, cy - 0.25, 0.62), (cx + 0.50, cy + 0.25, 0.70),
          wood_l, wood_d, wood_t)
    # Vice at the +X end: base, fixed jaw, screw stub, handle bar.
    q.box((cx + 0.28, cy - 0.08, 0.69), (cx + 0.46, cy + 0.08, 0.76),
          steel_l, steel_d, steel_l)
    q.box((cx + 0.42, cy - 0.08, 0.75), (cx + 0.47, cy + 0.08, 0.88),
          (110, 122, 114), (88, 100, 92), (130, 142, 134))
    q.box((cx + 0.24, cy - 0.02, 0.79), (cx + 0.425, cy + 0.02, 0.83),
          (88, 100, 92), (88, 100, 92), (88, 100, 92))
    # Hand tools on the slab: hammer, small parts box, oil can.
    q.box((cx - 0.30, cy - 0.03, 0.69), (cx - 0.02, cy + 0.03, 0.725),
          (150, 115, 75), (150, 115, 75), (150, 115, 75))
    q.box((cx - 0.02, cy - 0.05, 0.69), (cx + 0.06, cy + 0.05, 0.78),
          (120, 130, 122), (120, 130, 122), (120, 130, 122))
    q.box((cx - 0.42, cy + 0.08, 0.69), (cx - 0.24, cy + 0.20, 0.78),
          (110, 140, 120), (88, 114, 98), (130, 160, 140))
    _cylinder(q, cx - 0.12, cy - 0.12, 0.69, 0.82, 0.045,
              (200, 150, 70), (150, 110, 52), (215, 168, 90), n=14)
    # Hanging tools proud of the pegboard +Y face (painted last).
    q.box((cx - 0.30, cy - 0.215, 0.78), (cx - 0.26, cy - 0.19, 1.02),
          steel_l, steel_d, steel_l)
    q.box((cx - 0.05, cy - 0.215, 0.82), (cx + 0.09, cy - 0.19, 0.90),
          (150, 115, 75), (150, 115, 75), (150, 115, 75))
    q.dot((cx + 0.20, cy - 0.208, 0.95), 0.9, (90, 100, 92, 255))


def tool_cabinet(q, cx, cy, P):
    """Drawer tool cabinet: red body hero, drawer fronts, top tray, casters."""
    red_l, red_d, red_t = (198, 96, 82), (152, 70, 60), (216, 122, 104)
    # Casters + base plinth first.
    for wx, wy in ((cx - 0.22, cy - 0.13), (cx + 0.22, cy - 0.13),
                   (cx - 0.22, cy + 0.13), (cx + 0.22, cy + 0.13)):
        q.box((wx - 0.045, wy - 0.045, -0.02), (wx + 0.045, wy + 0.045, 0.03),
              (80, 90, 82), (64, 72, 66), (100, 110, 102))
    q.box((cx - 0.31, cy - 0.21, 0.02), (cx + 0.31, cy + 0.21, 0.105),
          (90, 100, 92), (70, 80, 72), (110, 120, 112))
    # Hero body + top tray rim.
    q.box((cx - 0.30, cy - 0.20, 0.10), (cx + 0.30, cy + 0.20, 0.95),
          red_l, red_d, red_t)
    q.box((cx - 0.31, cy - 0.21, 0.945), (cx + 0.31, cy + 0.21, 1.00),
          (90, 100, 92), (70, 80, 72), (110, 120, 112))
    # Five drawer fronts proud of the +Y face + handles (painted last).
    for i in range(5):
        z0 = 0.16 + i * 0.15
        q.fp(cx - 0.25, cx + 0.25, cy + 0.201, z0, z0 + 0.12, (216, 122, 104))
        q.box((cx - 0.16, cy + 0.201, z0 + 0.045), (cx + 0.16, cy + 0.215, z0 + 0.075),
              (150, 160, 152), (120, 130, 122), (170, 180, 172))
    # Side push handle on the +X flank.
    q.box((cx + 0.295, cy - 0.12, 0.72), (cx + 0.335, cy - 0.08, 0.90),
          (150, 160, 152), (150, 160, 152), (150, 160, 152))
    q.box((cx + 0.295, cy + 0.08, 0.72), (cx + 0.335, cy + 0.12, 0.90),
          (150, 160, 152), (150, 160, 152), (150, 160, 152))
    q.box((cx + 0.295, cy - 0.12, 0.875), (cx + 0.335, cy + 0.12, 0.915),
          (150, 160, 152), (150, 160, 152), (150, 160, 152))


def workshop_compressor(q, cx, cy, P):
    """Workshop air compressor: red tank hero, motor, wheels, fittings."""
    # Feet + wheels + axle first (far -> near).
    for fx, fy in ((cx - 0.14, cy - 0.14), (cx + 0.14, cy - 0.14),
                   (cx - 0.14, cy + 0.14), (cx + 0.14, cy + 0.14)):
        q.box((fx - 0.05, fy - 0.05, -0.02), (fx + 0.05, fy + 0.05, 0.125),
              (90, 100, 92), (70, 80, 72), (110, 120, 112))
    q.disc_y(cx - 0.10, cy - 0.27, 0.09, 0.09, (70, 78, 72))
    q.box((cx - 0.16, cy - 0.27, 0.06), (cx + 0.16, cy - 0.21, 0.12),
          (90, 100, 92), (90, 100, 92), (90, 100, 92))
    # Hero tank (covers the far feet tops).
    _cylinder(q, cx, cy, 0.12, 0.78, 0.26,
              (215, 120, 95), (150, 70, 60), (225, 140, 115), n=28)
    # Motor block rooted in the tank +Y flank (near, after tank).
    q.box((cx - 0.15, cy + 0.18, 0.30), (cx + 0.15, cy + 0.36, 0.52),
          (110, 125, 115), (88, 102, 92), (130, 145, 135))
    q.box((cx - 0.10, cy + 0.30, 0.515), (cx + 0.10, cy + 0.38, 0.60),
          (90, 100, 92), (72, 82, 74), (110, 120, 112))
    # Top outlet + gauge + pull handle (all after the tank cap).
    _cylinder(q, cx - 0.08, cy - 0.05, 0.78, 0.90, 0.045,
              (150, 160, 152), (110, 120, 112), (170, 180, 172), n=14)
    q.dot((cx + 0.10, cy + 0.362, 0.45), 1.1, (245, 240, 220, 255))
    q.box((cx - 0.16, cy - 0.16, 0.80), (cx - 0.12, cy - 0.12, 1.00),
          (90, 100, 92), (90, 100, 92), (90, 100, 92))
    q.box((cx + 0.12, cy - 0.16, 0.80), (cx + 0.16, cy - 0.12, 1.00),
          (90, 100, 92), (90, 100, 92), (90, 100, 92))
    q.box((cx - 0.16, cy - 0.16, 0.96), (cx + 0.16, cy - 0.12, 1.02),
          (90, 100, 92), (90, 100, 92), (90, 100, 92))
    # Near wheels + hub dots last.
    q.disc_y(cx - 0.10, cy + 0.27, 0.09, 0.09, (70, 78, 72))
    q.disc_y(cx + 0.10, cy + 0.27, 0.09, 0.09, (70, 78, 72))
    q.dot((cx - 0.10, cy + 0.272, 0.09), 0.9, (150, 158, 148, 255))
    q.dot((cx + 0.10, cy + 0.272, 0.09), 0.9, (150, 158, 148, 255))


def generator(q, cx, cy, P):
    """Power generator: skid, teal canopy hero, panel, exhaust stack."""
    # Skid frame first, then hero canopy over it.
    q.boxg((cx - 0.42, cy - 0.24, 0.0), (cx + 0.42, cy + 0.24, 0.125),
          (90, 100, 92), (70, 80, 72), (110, 120, 112))
    q.boxg((cx - 0.40, cy - 0.22, 0.12), (cx + 0.40, cy + 0.22, 0.72),
          (110, 165, 150), (86, 132, 120), (135, 185, 170))
    # Top service panel proud of the canopy roof.
    q.boxg((cx - 0.30, cy - 0.15, 0.715), (cx + 0.30, cy + 0.15, 0.78),
          (90, 100, 92), (72, 82, 74), (110, 120, 112))
    q.line([(cx - 0.26, cy + 0.0, 0.782), (cx + 0.26, cy + 0.0, 0.782)],
           (150, 164, 156), 0.8)
    # Exhaust stack rooted in the roof + rain cap.
    _cylinder(q, cx - 0.22, cy - 0.05, 0.72, 1.00, 0.05,
              (110, 120, 112), (80, 90, 82), (130, 140, 132), n=14)
    _cylinder(q, cx - 0.22, cy - 0.05, 0.995, 1.03, 0.065,
              (80, 90, 82), (64, 72, 66), (100, 110, 102), n=14)
    q.dot((cx + 0.10, cy + 0.0, 0.785), 1.0, (200, 210, 200, 255))
    # Control face on +Y: dark panel, display, buttons, vents.
    q.fp(cx - 0.18, cx + 0.18, cy + 0.221, 0.30, 0.58, (62, 76, 70))
    q.fp(cx - 0.14, cx + 0.02, cy + 0.223, 0.47, 0.54, (110, 150, 135))
    q.dot((cx + 0.10, cy + 0.224, 0.50), 1.0, (255, 176, 92, 255))
    q.dot((cx + 0.10, cy + 0.224, 0.40), 1.0, (110, 190, 170, 255))
    for vz in (0.32, 0.36):
        q.line([(cx - 0.14, cy + 0.223, vz), (cx + 0.14, cy + 0.223, vz)],
               (120, 134, 126), 0.8)
    # Intake vents on the +X flank (embossed lines, painted last).
    for vz in (0.30, 0.38, 0.46, 0.54):
        q.line([(cx + 0.401, cy - 0.14, vz), (cx + 0.401, cy + 0.14, vz)],
               (70, 108, 96), 0.9)



def transformer_big(q, cx, cy, P):
    """Pole transformer: post, tank hero with fins, bushings, crossarm."""
    grey_l, grey_d, grey_t = (150, 165, 155), (116, 130, 120), (172, 186, 176)
    # Post (far) + crossarm, both sunk at the foot.
    q.box((cx - 0.09, cy - 0.09, -0.02), (cx + 0.09, cy + 0.09, 1.50),
          (150, 120, 90), (120, 96, 72), (168, 138, 106))
    q.box((cx - 0.42, cy - 0.06, 1.30), (cx + 0.42, cy + 0.06, 1.38),
          (130, 104, 78), (130, 104, 78), (130, 104, 78))
    for ix in (cx - 0.30, cx + 0.30):
        _cylinder(q, ix, cy, 1.37, 1.47, 0.035,
                  (170, 180, 172), (120, 130, 122), (190, 198, 190), n=12)
    # Hero tank hung on the +Y face of the post (near, after post).
    _cylinder(q, cx, cy + 0.28, 0.75, 1.25, 0.20,
              grey_l, grey_d, grey_t, n=24)
    # Cooling fins rooted in the tank +X flank.
    for fy in (cy + 0.16, cy + 0.28, cy + 0.40):
        q.box((cx + 0.10, fy - 0.025, 0.82), (cx + 0.30, fy + 0.025, 1.18),
              grey_l, grey_d, grey_t)
    # Lid band + bushings on the tank cap (painted last).
    _cylinder(q, cx, cy + 0.28, 1.24, 1.30, 0.215,
              grey_d, grey_d, grey_d, n=24)
    for bx in (cx - 0.09, cx + 0.09):
        _cylinder(q, bx, cy + 0.28, 1.295, 1.44, 0.035,
                  (170, 180, 172), (120, 130, 122), (190, 198, 190), n=12)
        q.dot((bx, cy + 0.28, 1.495), 0.8, (90, 100, 92, 255))
    q.line([(cx - 0.14, cy + 0.482, 1.00), (cx + 0.14, cy + 0.482, 1.00)],
           (90, 102, 94), 0.8)


def cable_tray(q, cx, cy, P):
    """Cable tray section: tray hero, rungs, cables, support legs."""
    steel_l, steel_d, steel_t = (150, 162, 152), (118, 130, 120), (172, 184, 174)
    # Support legs + crossbars first (far -> near).
    for lx, ly in ((cx - 0.40, cy - 0.07), (cx - 0.40, cy + 0.07),
                   (cx + 0.40, cy - 0.07), (cx + 0.40, cy + 0.07)):
        q.box((lx - 0.035, ly - 0.035, -0.02), (lx + 0.035, ly + 0.035, 0.505),
              steel_l, steel_d, steel_t)
    for lx in (cx - 0.40, cx + 0.40):
        q.box((lx - 0.03, cy - 0.07, 0.30), (lx + 0.03, cy + 0.07, 0.36),
              steel_d, steel_d, steel_d)
    # Tray base hero + rungs across it.
    q.box((cx - 0.55, cy - 0.12, 0.50), (cx + 0.55, cy + 0.12, 0.55),
          steel_l, steel_d, steel_t)
    for rx in [cx - 0.44 + i * 0.11 for i in range(9)]:
        q.box((rx - 0.025, cy - 0.085, 0.545), (rx + 0.025, cy + 0.085, 0.575),
              steel_d, steel_d, steel_d)
    # Far side rail, then cables bedded over the rungs, then near rail.
    q.box((cx - 0.55, cy - 0.12, 0.545), (cx + 0.55, cy - 0.085, 0.66),
          steel_l, steel_d, steel_t)
    for dy, col in ((-0.055, (200, 110, 90)), (0.0, (220, 180, 100)),
                     (0.055, (110, 150, 190))):
        q.box((cx - 0.53, cy + dy - 0.022, 0.57), (cx + 0.53, cy + dy + 0.022, 0.615),
              col, col, col)
    q.box((cx - 0.55, cy + 0.085, 0.545), (cx + 0.55, cy + 0.12, 0.66),
          steel_l, steel_d, steel_t)


def factory_chimney(q, cx, cy, P):
    """Tall factory chimney: concrete base, three tapered brick rings, bands."""
    brick_l, brick_d, brick_t = (188, 112, 86), (142, 82, 62), (205, 132, 104)
    # Base plinth first, then rings bottom-up (rims read as joint bands).
    q.box((cx - 0.30, cy - 0.30, -0.02), (cx + 0.30, cy + 0.30, 0.25),
          (170, 175, 165), (138, 144, 134), (190, 194, 186))
    _cylinder(q, cx, cy, 0.20, 0.80, 0.24, brick_l, brick_d, brick_t, n=28)
    _cylinder(q, cx, cy, 0.75, 0.81, 0.255, (110, 120, 112),
              (84, 92, 86), (130, 140, 132), n=28)
    _cylinder(q, cx, cy, 0.76, 1.25, 0.20, brick_l, brick_d, brick_t, n=28)
    _cylinder(q, cx, cy, 1.20, 1.26, 0.215, (110, 120, 112),
              (84, 92, 86), (130, 140, 132), n=28)
    _cylinder(q, cx, cy, 1.21, 1.65, 0.165, brick_l, brick_d, brick_t, n=28)
    # Dark flue opening on the cap + door on the base +Y face.
    q.ground_ellipse(cx, cy, 0.10, 0.10, (60, 66, 62), z=1.701, n=20)
    q.fp(cx - 0.10, cx + 0.10, cy + 0.301, 0.03, 0.20, (90, 98, 92))
    q.line([(cx - 0.10, cy + 0.302, 0.115), (cx + 0.10, cy + 0.302, 0.115)],
           (150, 158, 150), 0.8)


def loading_dock(q, cx, cy, P):
    """Loading dock: platform hero, back wall with door, bumpers, bollards."""
    conc_l, conc_d, conc_t = (175, 180, 170), (140, 146, 136), (195, 200, 192)
    # Back wall (far) first, then the platform over its foot.
    q.box((cx - 0.55, cy - 0.30, 0.40), (cx + 0.55, cy - 0.20, 1.15),
          (200, 190, 170), (164, 156, 140), (216, 208, 190))
    q.box((cx - 0.55, cy - 0.30, 1.145), (cx + 0.55, cy - 0.195, 1.20),
          (164, 156, 140), (164, 156, 140), (164, 156, 140))
    q.box((cx - 0.55, cy - 0.20, 0.0), (cx + 0.55, cy + 0.30, 0.45),
          conc_l, conc_d, conc_t)
    # Door panel proud of the wall +Y face + embossed slats + dock plate.
    q.fp(cx - 0.15, cx + 0.25, cy - 0.199, 0.45, 0.95, (140, 150, 160))
    for dz in (0.55, 0.65, 0.75, 0.85):
        q.line([(cx - 0.15, cy - 0.198, dz), (cx + 0.25, cy - 0.198, dz)],
               (100, 110, 120), 0.8)
    q.box((cx - 0.08, cy - 0.198, 0.40), (cx + 0.18, cy - 0.16, 0.46),
          (120, 130, 122), (120, 130, 122), (120, 130, 122))
    # Edge warning stripe + bumpers on the platform +Y face.
    q.fp(cx - 0.55, cx + 0.55, cy + 0.301, 0.36, 0.43, (205, 160, 80))
    for bx in (cx - 0.30, cx + 0.30):
        q.box((bx - 0.10, cy + 0.295, 0.10), (bx + 0.10, cy + 0.355, 0.25),
              (70, 78, 72), (60, 68, 62), (90, 98, 92))
    # Bollards standing on the plinth in front (nearest, last).
    for bx in (cx - 0.38, cx + 0.38):
        _cylinder(q, bx, cy + 0.42, -0.02, 0.42, 0.045,
                  (210, 170, 80), (160, 128, 60), (225, 188, 100), n=14)
        q.dot((bx, cy + 0.42, 0.475), 0.9, (90, 96, 90, 255))


def welding_set(q, cx, cy, P):
    """Welding machine: skid, green steel body hero, panel, cables, mask."""
    # Skid first, then hero body over it (wheels proud of the skid sides).
    q.boxg((cx - 0.30, cy - 0.22, 0.02), (cx + 0.30, cy + 0.22, 0.155),
          (90, 100, 92), (70, 80, 72), (110, 120, 112))
    q.disc_y(cx - 0.16, cy - 0.27, 0.08, 0.08, (70, 78, 72))
    q.disc_y(cx - 0.16, cy - 0.272, 0.08, 0.05, (170, 178, 168))
    q.boxg((cx - 0.19, cy - 0.28, 0.05), (cx - 0.13, cy - 0.19, 0.11),
          (90, 100, 92), (90, 100, 92), (90, 100, 92))
    q.boxg((cx - 0.28, cy - 0.20, 0.15), (cx + 0.28, cy + 0.20, 0.62),
          (88, 128, 108), (66, 100, 84), (110, 150, 128))
    # Electrode holder lying on the roof: insulated handle, twin jaws.
    q.boxg((cx - 0.10, cy - 0.05, 0.615), (cx + 0.05, cy + 0.03, 0.655),
          (60, 68, 64), (60, 68, 64), (60, 68, 64))
    q.boxg((cx + 0.05, cy - 0.025, 0.615), (cx + 0.17, cy - 0.005, 0.65),
          (140, 130, 110), (140, 130, 110), (140, 130, 110))
    q.boxg((cx + 0.05, cy + 0.015, 0.615), (cx + 0.17, cy + 0.035, 0.65),
          (140, 130, 110), (140, 130, 110), (140, 130, 110))
    # Front panel on +Y: dark face, amber display, knobs, vents (painted after).
    q.fp(cx - 0.20, cx + 0.20, cy + 0.201, 0.24, 0.55, (62, 76, 70))
    q.fp(cx - 0.16, cx - 0.06, cy + 0.203, 0.45, 0.52, (215, 165, 95))
    q.line([(cx - 0.11, cy + 0.204, 0.46), (cx - 0.085, cy + 0.204, 0.505)],
           (210, 210, 190), 0.9)
    q.dot((cx + 0.15, cy + 0.204, 0.50), 1.0, (110, 200, 130, 255))
    for vz in (0.30, 0.34):
        q.line([(cx - 0.16, cy + 0.203, vz), (cx + 0.16, cy + 0.203, vz)],
               (120, 134, 126), 0.8)
    # Dinse sockets: dark round rims with center pins; plugs + thin leads.
    for sox in (cx - 0.135, cx - 0.015):
        q.disc_y(sox, cy + 0.203, 0.30, 0.028, (40, 48, 44))
        q.dot((sox, cy + 0.206, 0.30), 0.9, (200, 210, 200, 255))
        q.boxg((sox - 0.020, cy + 0.19, 0.28), (sox + 0.020, cy + 0.25, 0.35),
              (170, 70, 55), (130, 52, 42), (190, 96, 76))
    for cbx in (cx - 0.135, cx - 0.015):
        q.boxg((cbx - 0.011, cy + 0.20, 0.10), (cbx + 0.011, cy + 0.24, 0.20),
              (40, 48, 44), (40, 48, 44), (40, 48, 44))
        q.boxg((cbx - 0.003, cy + 0.205, 0.02), (cbx + 0.019, cy + 0.245, 0.105),
              (40, 48, 44), (40, 48, 44), (40, 48, 44))
    # One big current dial + vent louvers (vertical slats, not a grille).
    q.boxg((cx + 0.035, cy + 0.20, 0.375), (cx + 0.095, cy + 0.23, 0.435),
          (50, 58, 54), (50, 58, 54), (50, 58, 54))
    q.line([(cx + 0.065, cy + 0.231, 0.425), (cx + 0.077, cy + 0.231, 0.414)],
           (220, 220, 200), 1.0)
    for kx in (cx + 0.14, cx + 0.20):
        q.boxg((kx - 0.022, cy + 0.20, 0.40), (kx + 0.022, cy + 0.235, 0.46),
              (140, 150, 142), (110, 122, 114), (162, 172, 164))
    for vx in (cx - 0.02, cx + 0.02, cx + 0.06, cx + 0.10):
        q.line([(vx, cy + 0.203, 0.28), (vx, cy + 0.203, 0.38)],
               (120, 134, 126), 0.9)
    # Cable coil on the +X flank: concentric wound rings + holder arm.
    q.boxg((cx + 0.27, cy - 0.10, 0.22), (cx + 0.30, cy + 0.06, 0.48),
          (60, 68, 64), (60, 68, 64), (60, 68, 64))
    for j, cc in enumerate(((40, 48, 44), (110, 118, 112), (40, 48, 44),
                            (110, 118, 112), (40, 48, 44))):
        q.disc_x(cx + 0.305 + j * 0.008, cy - 0.02, 0.35, 0.13, cc)
    q.disc_x(cx + 0.345, cy - 0.02, 0.35, 0.055, (28, 34, 30))
    # Near wheels (proud, with hubs, axle stubs into the skid) + small
    # welding mask leaning on the unit +X face (last).
    q.disc_y(cx - 0.16, cy + 0.27, 0.08, 0.08, (70, 78, 72))
    q.disc_y(cx - 0.16, cy + 0.272, 0.08, 0.035, (150, 158, 148))
    q.boxg((cx - 0.19, cy + 0.19, 0.05), (cx - 0.13, cy + 0.28, 0.11),
          (90, 100, 92), (90, 100, 92), (90, 100, 92))
    q.disc_y(cx + 0.16, cy + 0.27, 0.08, 0.08, (70, 78, 72))
    q.disc_y(cx + 0.16, cy + 0.272, 0.08, 0.05, (170, 178, 168))
    q.boxg((cx + 0.13, cy + 0.19, 0.05), (cx + 0.19, cy + 0.28, 0.11),
          (90, 100, 92), (90, 100, 92), (90, 100, 92))
    q.dot((cx - 0.16, cy + 0.274, 0.08), 0.8, (90, 96, 90, 255))
    q.dot((cx + 0.16, cy + 0.274, 0.08), 0.8, (90, 96, 90, 255))
    # Welding mask: tapered shield (narrow crown, wide skirt), big visor
    # filling the upper half, pivot knobs on both flanks, top handle.
    q.boxg((cx + 0.29, cy + 0.19, 0.0), (cx + 0.41, cy + 0.33, 0.14),
          (150, 160, 165), (120, 132, 138), (172, 182, 187))
    q.boxg((cx + 0.27, cy + 0.18, 0.13), (cx + 0.43, cy + 0.36, 0.30),
          (150, 160, 165), (120, 132, 138), (172, 182, 187))
    q.boxg((cx + 0.42, cy + 0.21, 0.15), (cx + 0.448, cy + 0.31, 0.26),
              (40, 52, 58), (30, 40, 44), (52, 66, 72))
    q.boxg((cx + 0.315, cy + 0.19, 0.295), (cx + 0.385, cy + 0.35, 0.325),
          (130, 140, 145), (130, 140, 145), (130, 140, 145))
    for njx in (cx + 0.265, cx + 0.435):
        q.boxg((njx - 0.015, cy + 0.23, 0.17), (njx + 0.015, cy + 0.29, 0.23),
              (90, 100, 92), (90, 100, 92), (90, 100, 92))


PROPS = {
    "forklift": {"fn": forklift, "focus": (0.0, 0.15, 0.537), "k": 400,
                 "plinth": (0.0, 0.15, 0.80, 0.46),
                 "brief": "forklift with mast forks cabin wheels"},
    "pallet": {"fn": pallet, "focus": (0.0, 0.15, 0.128), "k": 620,
               "plinth": (0.0, 0.15, 0.68, 0.44),
               "brief": "wooden euro pallet"},
    "pallet-jack": {"fn": pallet_jack, "focus": (0.0, 0.15, 0.385), "k": 360,
                    "plinth": (0.0, 0.15, 0.75, 0.44),
                    "brief": "hand pallet jack with forks and handle"},
    "crates": {"fn": crates, "focus": (0.0, 0.15, 0.476), "k": 440,
               "plinth": (0.0, 0.15, 0.66, 0.42),
               "brief": "stack of crates and boxes"},
    "conveyor": {"fn": conveyor, "focus": (0.0, 0.15, 0.466), "k": 480,
                 "plinth": (0.0, 0.15, 0.82, 0.44),
                 "brief": "conveyor belt on legs with rollers"},
    "press": {"fn": press, "focus": (0.0, 0.15, 0.597), "k": 400,
              "plinth": (0.0, 0.15, 0.70, 0.44),
              "brief": "machine press with frame and ram"},
    "workbench": {"fn": workbench, "focus": (0.0, 0.15, 0.644), "k": 360,
                  "plinth": (0.0, 0.15, 0.78, 0.46),
                  "brief": "workbench with vice and tools"},
    "tool-cabinet": {"fn": tool_cabinet, "focus": (0.0, 0.15, 0.568), "k": 440,
                     "plinth": (0.0, 0.15, 0.62, 0.40),
                     "brief": "drawer tool cabinet with handles"},
    "workshop-compressor": {"fn": workshop_compressor, "focus": (0.0, 0.15, 0.502),
                            "k": 460,
                            "plinth": (0.0, 0.15, 0.62, 0.42),
                            "brief": "workshop air compressor tank with motor and wheels"},
    "generator": {"fn": generator, "focus": (0.0, 0.15, 0.441), "k": 380,
                  "plinth": (0.0, 0.15, 0.70, 0.44),
                  "brief": "power generator box with panel and exhaust"},
    "transformer-big": {"fn": transformer_big, "focus": (0.0, 0.15, 0.951), "k": 340,
                        "plinth": (0.0, 0.15, 0.66, 0.46),
                        "brief": "pole transformer with fins and bushings"},
    "cable-tray": {"fn": cable_tray, "focus": (0.0, 0.15, 0.489), "k": 500,
                   "plinth": (0.0, 0.15, 0.80, 0.42),
                   "brief": "cable tray section with cables"},
    "factory-chimney": {"fn": factory_chimney, "focus": (0.0, 0.15, 0.721), "k": 290,
                        "plinth": (0.0, 0.15, 0.60, 0.40),
                        "brief": "tall factory chimney with bands"},
    "loading-dock": {"fn": loading_dock, "focus": (0.0, 0.15, 0.655), "k": 300,
                     "plinth": (0.0, 0.15, 0.84, 0.50),
                     "brief": "loading dock platform with bumpers and door"},
    "welding-set": {"fn": welding_set, "focus": (0.0, 0.15, 0.325), "k": 540,
                    "plinth": (0.0, 0.15, 0.80, 0.44),
                    "brief": "welding machine with cables and mask"},
}
