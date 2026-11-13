"""Iso gallery props batch: electro (EV + grid + lighting).

Builders take ``(q, cx, cy, P)`` with all coordinates relative to the
placement center. Rules: overlap mating parts >= 0.005 (never
exact-touch), NO contact_shadow anywhere, mid-tone palette (nothing below
RGB 60 except tiny dots), hero element biggest, stubs start AT parent
surfaces, proud details painted AFTER parents, no text decals (embossed
lines only).
"""
from __future__ import annotations

import math

from reels_maker.iso.world import _cylinder


def wallbox(q, cx, cy, P):
    """EV wall charger on a pedestal post: hero box, screen, LED, cable
    loop down into a plug head."""
    # Pedestal post + cap (post top overlaps the charger box back).
    q.boxg((cx - 0.09, cy - 0.07, 0.0), (cx + 0.09, cy + 0.07, 0.78),
          (150, 160, 150), (120, 132, 122), (170, 180, 170))
    q.boxg((cx - 0.11, cy - 0.09, 0.0), (cx + 0.11, cy + 0.09, 0.06),
          (120, 132, 122), (100, 112, 102), (140, 152, 142))
    q.boxg((cx - 0.11, cy - 0.09, 0.76), (cx + 0.11, cy + 0.09, 0.82),
          (120, 132, 122), (100, 112, 102), (140, 152, 142))
    # Hero charger box (back overlaps the post face by 0.005+).
    q.boxg((cx - 0.24, cy + 0.065, 0.42), (cx + 0.24, cy + 0.245, 1.02),
          (70, 140, 115), (64, 116, 94), (90, 165, 138))
    # Screen + embossed bars (no text) on the +Y face, painted after box.
    q.fp(cx - 0.13, cx + 0.02, cy + 0.247, 0.80, 0.94, (62, 76, 70))
    q.fp(cx - 0.11, cx - 0.03, cy + 0.249, 0.86, 0.895, (110, 150, 135))
    q.fp(cx - 0.11, cx - 0.06, cy + 0.249, 0.82, 0.845, (110, 150, 135))
    # Status LED (tiny dot, may glow) + socket ring below screen.
    q.dot((cx + 0.14, cy + 0.248, 0.90), 1.5, (255, 176, 92, 255))
    q.dot((cx + 0.14, cy + 0.248, 0.78), 1.0, (200, 210, 200, 255))
    # Holster notch on the +X flank.
    q.boxg((cx + 0.235, cy + 0.02, 0.55), (cx + 0.285, cy + 0.14, 0.75),
          (64, 116, 94), (56, 100, 82), (70, 140, 115))
    # Cable: holster-rooted loop hanging PROUD of the front face
    # (charger language - corpus gate round 2: an in-face run read
    # as an arm, not a cable). Face plane is y=cy+0.245.
    q.line([(cx + 0.115, cy + 0.08, 0.52), (cx + 0.20, cy + 0.20, 0.32),
            (cx + 0.06, cy + 0.28, 0.235), (cx - 0.10, cy + 0.28, 0.235),
            (cx - 0.17, cy + 0.28, 0.45), (cx - 0.17, cy + 0.26, 0.60)],
           (40, 48, 44), 2.5)
    # Plug head swallowing the riser top + two prongs, proud of face.
    q.boxg((cx - 0.225, cy + 0.22, 0.56), (cx - 0.115, cy + 0.30, 0.72),
           (88, 100, 92), (70, 82, 74), (108, 120, 110))
    q.boxg((cx - 0.210, cy + 0.235, 0.715), (cx - 0.180, cy + 0.26, 0.78),
           (170, 178, 170), (170, 178, 170), (170, 178, 170))
    q.boxg((cx - 0.165, cy + 0.235, 0.715), (cx - 0.135, cy + 0.26, 0.78),
           (170, 178, 170), (170, 178, 170), (170, 178, 170))


def ev_car(q, cx, cy, P):
    """Compact isometric EV: hero body, glasshouse with dark band,
    four wheels, headlights, charge port."""
    # Far-side wheels FIRST (depth buffer): the body overdraws their tops,
    # leaving only the grounded crescents visible below the skirt.
    for wx in (cx - 0.38, cx + 0.38):
        q.disc_y(wx, cy - 0.268, 0.07, 0.205, (64, 84, 72))
        q.disc_y(wx, cy - 0.27, 0.07, 0.17, (62, 68, 64))
        q.disc_y(wx, cy - 0.272, 0.07, 0.085, (150, 160, 155))
    # Skirt grounded into the plinth + hero body (muted green steel).
    q.box((cx - 0.57, cy - 0.26, -0.05), (cx + 0.57, cy + 0.26, 0.20),
          (70, 92, 80), (64, 84, 72), (86, 108, 94))
    q.box((cx - 0.55, cy - 0.24, 0.16), (cx + 0.55, cy + 0.24, 0.52),
          (120, 155, 140), (96, 128, 114), (145, 175, 160))
    q.box((cx - 0.30, cy - 0.19, 0.50), (cx + 0.28, cy + 0.19, 0.84),
          (150, 165, 155), (120, 138, 128), (172, 186, 176))
    # Glass band proud of the +Y cabin face + +X flank, painted after.
    q.fp(cx - 0.27, cx + 0.25, cy + 0.192, 0.60, 0.76, (64, 84, 92))
    q.fp(cx - 0.20, cx + 0.25, cy + 0.194, 0.63, 0.68, (96, 118, 128))
    q.box((cx + 0.281, cy - 0.16, 0.60), (cx + 0.30, cy + 0.16, 0.76),
          (120, 138, 128), (64, 84, 92), (64, 84, 92))
    # Near-side wheels after the body: well arch, tire, hub, axle dot.
    for wx in (cx - 0.38, cx + 0.38):
        q.disc_y(wx, cy + 0.268, 0.07, 0.205, (64, 84, 72))
        q.disc_y(wx, cy + 0.27, 0.07, 0.17, (62, 68, 64))
        q.disc_y(wx, cy + 0.272, 0.07, 0.085, (150, 160, 155))
    q.dot((cx - 0.38, cy + 0.274, 0.07), 0.9, (90, 96, 90, 255))
    q.dot((cx + 0.38, cy + 0.274, 0.07), 0.9, (90, 96, 90, 255))
    # Headlights + grille on the +Y nose, charge port on +X.
    q.fp(cx + 0.30, cx + 0.48, cy + 0.262, 0.30, 0.38, (238, 240, 220))
    q.fp(cx - 0.48, cx - 0.30, cy + 0.262, 0.30, 0.38, (238, 240, 220))
    q.fp(cx - 0.10, cx + 0.24, cy + 0.262, 0.22, 0.26, (64, 88, 78))
    q.dot((cx + 0.552, cy + 0.05, 0.35), 1.0, (255, 176, 92, 255))
    # Small body-colour mirrors at the cabin belt line.
    q.box((cx - 0.32, cy + 0.17, 0.55), (cx - 0.28, cy + 0.22, 0.60),
          (96, 128, 114), (96, 128, 114), (96, 128, 114))
    q.box((cx + 0.26, cy + 0.17, 0.55), (cx + 0.30, cy + 0.22, 0.60),
          (96, 128, 114), (96, 128, 114), (96, 128, 114))


def junction_box(q, cx, cy, P):
    """Small grey junction box on a concrete post, lid, glands, two
    cable stubs running down into the ground."""
    # Post + base pad.
    q.box((cx - 0.10, cy - 0.09, 0.0), (cx + 0.10, cy + 0.09, 0.06),
          (120, 132, 122), (100, 112, 102), (140, 152, 142))
    q.box((cx - 0.07, cy - 0.06, 0.05), (cx + 0.07, cy + 0.06, 0.72),
          (150, 156, 148), (126, 134, 126), (170, 176, 168))
    # Hero box (back overlaps the post) + proud lid.
    q.box((cx - 0.20, cy - 0.02, 0.55), (cx + 0.20, cy + 0.26, 1.00),
          (168, 176, 166), (140, 150, 140), (188, 196, 186))
    q.box((cx - 0.21, cy + 0.25, 0.56), (cx + 0.21, cy + 0.285, 0.99),
          (182, 190, 180), (150, 160, 150), (200, 208, 198))
    # Lid screws (tiny dots) + embossed mark lines (no text).
    for sx in (cx - 0.17, cx + 0.17):
        for sz in (0.61, 0.94):
            q.dot((sx, cy + 0.287, sz), 0.8, (90, 98, 90, 255))
    for lz in (0.72, 0.78):
        q.line([(cx - 0.10, cy + 0.287, lz), (cx + 0.10, cy + 0.287, lz)],
               (120, 130, 122), 0.8)
    # Blank nameplate frame on the lid face.
    q.box((cx - 0.09, cy + 0.283, 0.79), (cx + 0.09, cy + 0.296, 0.90),
          (150, 160, 150), (150, 160, 150), (150, 160, 150))
    # Side (+X) face: seam lines + corner screws (that face is visible).
    for lz in (0.62, 0.93):
        q.line([(cx + 0.202, cy + 0.02, lz), (cx + 0.202, cy + 0.24, lz)],
               (120, 130, 122), 0.8)
    for sy in (cy + 0.05, cy + 0.21):
        for sz in (0.62, 0.93):
            q.dot((cx + 0.203, sy, sz), 0.8, (90, 98, 90, 255))
    # Base pad bolts on the top face.
    for bx in (cx - 0.085, cx + 0.085):
        for by in (cy - 0.075, cy + 0.075):
            q.dot((bx, by, 0.065), 0.8, (90, 98, 90, 255))
    # Glands under the box + nuts, stubs into the ground.
    for gx in (cx - 0.09, cx + 0.09):
        _cylinder(q, gx, cy + 0.12, 0.40, 0.56, 0.035,
                  (96, 104, 96), (70, 78, 70), (116, 124, 116), n=12)
        _cylinder(q, gx, cy + 0.12, 0.48, 0.54, 0.052,
                  (70, 78, 70), (60, 66, 60), (88, 96, 88), n=12)
        # Stubs bury 0.035 into the plinth (was -0.10, floated 0.025
        # above it — corpus gate 2026-11-12).
        q.box((gx - 0.025, cy + 0.095, -0.16), (gx + 0.025, cy + 0.145, 0.42),
              (66, 80, 74), (60, 72, 66), (84, 98, 90))


def cable_drum(q, cx, cy, P):
    """Wooden cable drum with the axle across the view (axis Y): both
    flanges read as rims, the wound cable core shows between them, the
    through-axle rests on two stands, tail runs into the ground."""
    # Wound cable core first (flanges cover its ends), poking 0.01
    # through each flange plane.
    q.box((cx - 0.20, cy - 0.29, 0.40), (cx + 0.20, cy + 0.29, 0.80),
          (70, 80, 74), (62, 72, 66), (86, 96, 88))
    q.box((cx - 0.20, cy - 0.29, 0.50), (cx + 0.20, cy + 0.29, 0.70),
          (84, 94, 86), (70, 80, 74), (98, 108, 100))
    for bx in (cx - 0.10, cx + 0.10):
        q.box((bx - 0.02, cy - 0.295, 0.46), (bx + 0.02, cy + 0.295, 0.74),
              (110, 122, 112), (110, 122, 112), (110, 122, 112))
    # Winding grooves on the visible +Y/+X core faces (read as layers).
    for gz in (0.44, 0.47, 0.50, 0.54, 0.57, 0.60, 0.64, 0.67, 0.70):
        q.fp(cx - 0.19, cx + 0.19, cy + 0.292, gz, gz + 0.02, (60, 70, 64))
    # Back flange, then the axle (near flange covers its middle: the axle
    # reads as passing THROUGH the drum, not in front of it).
    q.disc_y(cx, cy - 0.28, 0.60, 0.36, (168, 128, 88))
    q.disc_y(cx, cy - 0.282, 0.60, 0.13, (146, 108, 72))
    q.box((cx - 0.035, cy - 0.46, 0.565), (cx + 0.035, cy + 0.46, 0.635),
          (120, 130, 122), (96, 106, 98), (140, 150, 142))
    # Near flange + hub + bolts + amber grease cap.
    q.disc_y(cx, cy + 0.28, 0.60, 0.36, (176, 134, 92))
    q.disc_y(cx, cy + 0.282, 0.60, 0.13, (150, 112, 76))
    for k in range(6):
        ang = 0.5 + k * 1.047
        q.dot((cx + 0.26 * math.cos(ang), cy + 0.284,
               0.60 + 0.26 * math.sin(ang)), 0.8, (110, 84, 58, 255))
    q.dot((cx, cy + 0.284, 0.60), 1.0, (255, 176, 92, 255))
    # Stands swallowing the axle ends at both spans.
    for sy in (cy - 0.42, cy + 0.42):
        q.box((cx - 0.10, sy - 0.09, 0.0), (cx + 0.10, sy + 0.09, 0.05),
              (110, 122, 112), (92, 104, 94), (130, 142, 132))
        q.box((cx - 0.055, sy - 0.055, 0.04), (cx + 0.055, sy + 0.055, 0.60),
              (140, 152, 140), (116, 128, 116), (160, 172, 160))
        q.box((cx - 0.065, sy - 0.065, 0.55), (cx + 0.065, sy + 0.065, 0.68),
              (100, 112, 102), (84, 96, 86), (120, 132, 122))
    # No cable tail: a loose end reads as a floating block. The wound
    # core bands above carry the cable read on their own.


def trafo_station(q, cx, cy, P):
    """Small transformer hut: stepped base, roof slab, door, radiator
    fins, roof bushings with sheds, embossed warning plate."""
    # Stepped base + hero hut + roof slab (overlaps, never touches).
    q.boxg((cx - 0.38, cy - 0.26, 0.0), (cx + 0.38, cy + 0.26, 0.10),
          (120, 132, 122), (100, 112, 102), (140, 152, 142))
    q.boxg((cx - 0.34, cy - 0.22, 0.08), (cx + 0.34, cy + 0.22, 0.95),
          (150, 160, 148), (124, 136, 124), (172, 180, 168))
    q.boxg((cx - 0.40, cy - 0.28, 0.93), (cx + 0.40, cy + 0.28, 1.05),
          (140, 150, 140), (116, 128, 118), (164, 174, 164))
    # Door on the +Y face + handle.
    q.fp(cx - 0.12, cx + 0.12, cy + 0.222, 0.10, 0.70, (86, 100, 92))
    q.fp(cx - 0.10, cx + 0.10, cy + 0.224, 0.62, 0.66, (100, 114, 106))
    q.dot((cx + 0.07, cy + 0.226, 0.42), 0.9, (190, 200, 190, 255))
    # Radiator fins proud of the +X flank.
    for j in range(3):
        fy0 = cy - 0.15 + j * 0.13
        q.boxg((cx + 0.33, fy0, 0.25), (cx + 0.40, fy0 + 0.07, 0.75),
              (124, 136, 124), (100, 112, 102), (146, 158, 146))
    # Warning plate + embossed rows (no text) on the +Y face.
    q.boxg((cx - 0.14, cy + 0.222, 0.55), (cx + 0.14, cy + 0.246, 0.80),
          (210, 160, 90), (180, 136, 74), (226, 180, 110))
    for lz in (0.62, 0.68, 0.74):
        q.line([(cx - 0.10, cy + 0.248, lz), (cx + 0.10, cy + 0.248, lz)],
               (150, 112, 62), 0.9)
    # Roof bushings: stems first, sheds + caps after (all connected).
    for bx in (cx - 0.18, cx, cx + 0.18):
        _cylinder(q, bx, cy, 1.05, 1.27, 0.030,
                  (120, 128, 120), (92, 100, 92), (140, 148, 140), n=12)
        for sz in (1.12, 1.18, 1.24):
            q.ground_ellipse(bx, cy, 0.055, 0.055, (150, 158, 150),
                             z=sz, n=16)
        q.dot((bx, cy, 1.29), 1.0, (90, 98, 90, 255))


def pylon(q, cx, cy, P):
    """Lattice-free HV pole: stepped footing, steel mast, two
    crossarms, hanging insulator strings, climbing pegs."""
    # Stepped footing.
    q.box((cx - 0.22, cy - 0.20, -0.10), (cx + 0.22, cy + 0.20, 0.06),
          (130, 140, 132), (108, 118, 110), (150, 160, 152))
    q.box((cx - 0.15, cy - 0.13, 0.05), (cx + 0.15, cy + 0.13, 0.20),
          (140, 150, 142), (116, 126, 118), (160, 170, 162))
    # Mast (rim reaches z1 + 0.05) + peak cap.
    _cylinder(q, cx, cy, 0.15, 1.85, 0.11,
              (130, 140, 132), (96, 106, 98), (150, 160, 150), n=24)
    q.box((cx - 0.06, cy - 0.06, 1.84), (cx + 0.06, cy + 0.06, 1.98),
          (100, 112, 104), (84, 96, 88), (120, 132, 124))
    q.dot((cx, cy, 2.0), 1.0, (90, 98, 90, 255))
    # Two crossarms through the mast + end caps.
    q.box((cx - 0.55, cy - 0.06, 1.45), (cx + 0.55, cy + 0.06, 1.55),
          (100, 112, 104), (84, 96, 88), (120, 132, 124))
    q.box((cx - 0.42, cy - 0.06, 1.15), (cx + 0.42, cy + 0.06, 1.25),
          (100, 112, 104), (84, 96, 88), (120, 132, 124))
    # Insulator strings hanging below the arm ends (tops overlap arms).
    for ex, arm_z in ((cx - 0.48, 1.45), (cx + 0.48, 1.45),
                      (cx - 0.36, 1.15), (cx + 0.36, 1.15)):
        q.box((ex - 0.025, cy - 0.025, arm_z - 0.24),
              (ex + 0.025, cy + 0.025, arm_z + 0.02),
              (150, 158, 150), (126, 136, 128), (168, 176, 168))
        q.box((ex - 0.048, cy - 0.048, arm_z - 0.20),
              (ex + 0.048, cy + 0.048, arm_z - 0.16),
              (126, 136, 128), (126, 136, 128), (126, 136, 128))
        q.box((ex - 0.048, cy - 0.048, arm_z - 0.12),
              (ex + 0.048, cy + 0.048, arm_z - 0.08),
              (126, 136, 128), (126, 136, 128), (126, 136, 128))
        q.dot((ex, cy, arm_z - 0.25), 0.9, (90, 98, 90, 255))
    # Climbing pegs alternating on the +Y mast face.
    for pz, px in ((0.55, -0.04), (0.85, 0.04), (1.45 - 0.45, -0.04)):
        q.box((cx + px - 0.03, cy + 0.10, pz), (cx + px + 0.03, cy + 0.17, pz + 0.035),
              (110, 122, 114), (110, 122, 114), (110, 122, 114))


def lamp_pole(q, cx, cy, P):
    """Street lamp: base plate with bolts, pole, outreach arm,
    lamp head with lamp panel and LEDs."""
    # Base plate + bolts + pole.
    q.box((cx - 0.14, cy - 0.12, 0.0), (cx + 0.14, cy + 0.12, 0.10),
          (110, 122, 114), (92, 104, 96), (130, 142, 134))
    for bx in (cx - 0.10, cx + 0.10):
        for by in (cy - 0.08, cy + 0.08):
            q.dot((bx, by, 0.105), 0.8, (70, 78, 70, 255))
    _cylinder(q, cx, cy, 0.08, 1.70, 0.07,
              (120, 132, 124), (92, 104, 96), (140, 152, 144), n=20)
    # Collar at the arm joint (proud, after the pole) + outreach arm.
    _cylinder(q, cx, cy, 1.52, 1.64, 0.09,
              (100, 112, 104), (80, 92, 84), (120, 132, 124), n=16)
    q.box((cx - 0.05, cy - 0.02, 1.58), (cx + 0.05, cy + 0.55, 1.70),
          (110, 122, 114), (92, 104, 96), (130, 142, 134))
    # Lamp head swallowing the arm end + lamp panel + LEDs.
    q.box((cx - 0.09, cy + 0.48, 1.52), (cx + 0.09, cy + 0.78, 1.66),
          (150, 160, 152), (124, 136, 128), (172, 182, 174))
    q.box((cx - 0.07, cy + 0.50, 1.50), (cx + 0.07, cy + 0.76, 1.535),
          (240, 240, 228), (240, 240, 228), (240, 240, 228))
    q.dot((cx - 0.03, cy + 0.63, 1.528), 0.8, (255, 200, 120, 255))
    q.dot((cx + 0.03, cy + 0.63, 1.528), 0.8, (255, 200, 120, 255))


def pole_nn(q, cx, cy, P):
    """Concrete LV pole: footing, wood crossarm with three insulators,
    hooks, drop wire into a meter box, embossed plate."""
    # Footing + pole + cap.
    q.boxg((cx - 0.16, cy - 0.14, -0.10), (cx + 0.16, cy + 0.14, 0.08),
          (130, 140, 132), (108, 118, 110), (150, 160, 152))
    q.boxg((cx - 0.10, cy - 0.09, 0.06), (cx + 0.10, cy + 0.09, 1.60),
          (158, 162, 152), (130, 136, 126), (178, 182, 172))
    q.boxg((cx - 0.11, cy - 0.10, 1.58), (cx + 0.11, cy + 0.10, 1.66),
          (140, 150, 142), (118, 128, 120), (162, 172, 164))
    # Wood crossarm through the pole + insulators on top.
    q.boxg((cx - 0.35, cy - 0.05, 1.30), (cx + 0.35, cy + 0.05, 1.40),
          (150, 118, 82), (122, 96, 66), (170, 138, 100))
    for ix in (cx - 0.25, cx, cx + 0.25):
        _cylinder(q, ix, cy, 1.38, 1.52, 0.035,
                  (150, 158, 150), (120, 130, 122), (168, 176, 168), n=12)
        q.ground_ellipse(ix, cy, 0.05, 0.05, (126, 136, 128), z=1.45, n=14)
        q.dot((ix, cy, 1.54), 0.9, (90, 98, 90, 255))
    # Hooks on the +Y face.
    for hz in (0.70, 1.00):
        q.boxg((cx - 0.10, cy + 0.08, hz), (cx - 0.04, cy + 0.14, hz + 0.04),
              (110, 122, 114), (110, 122, 114), (110, 122, 114))
    # Meter box on the +Y face + drop wire from arm into its top.
    q.boxg((cx + 0.10, cy + 0.08, 0.22), (cx + 0.30, cy + 0.17, 0.52),
          (168, 176, 166), (140, 150, 140), (188, 196, 186))
    q.fp(cx + 0.13, cx + 0.27, cy + 0.172, 0.30, 0.44, (86, 100, 92))
    q.boxg((cx + 0.225, cy - 0.02, 0.30), (cx + 0.275, cy + 0.10, 1.33),
          (66, 80, 74), (60, 72, 66), (84, 98, 90))
    # Emblem plate with embossed lines (no text) above the meter box.
    q.boxg((cx - 0.16, cy + 0.088, 0.78), (cx + 0.02, cy + 0.108, 0.98),
          (210, 160, 90), (210, 160, 90), (226, 180, 110))
    for lz in (0.84, 0.90):
        q.line([(cx - 0.13, cy + 0.110, lz), (cx - 0.01, cy + 0.110, lz)],
               (150, 112, 62), 0.9)


PROPS = {
    "wallbox": {
        "fn": wallbox, "focus": (0.0, 0.15, 0.578), "k": 476,
        "plinth": (0.0, 0.15, 0.62, 0.40),
        "brief": "EV wall charger box on a pedestal post with a coiled "
                 "cable loop, plug head and status LED",
    },
    "ev-car": {
        "fn": ev_car, "focus": (0.0, 0.15, 0.453), "k": 399,
        "plinth": (0.0, 0.15, 0.85, 0.50),
        "brief": "simple compact isometric electric car with a dark glass "
                 "band, four wheels and headlights",
    },
    "junction-box": {
        "fn": junction_box, "focus": (0.0, 0.15, 0.521), "k": 434,
        "plinth": (0.0, 0.15, 0.55, 0.36),
        "brief": "small grey junction box with lid and cable glands on a "
                 "concrete post",
    },
    "cable-drum": {
        "fn": cable_drum, "focus": (0.0, 0.15, 0.503), "k": 395,
        "plinth": (0.0, 0.15, 0.70, 0.44),
        "brief": "wooden cable drum with wound cable on a through-axle "
                 "resting on two stands",
    },
    "trafo-station": {
        "fn": trafo_station, "focus": (0.0, 0.15, 0.662), "k": 332,
        "plinth": (0.0, 0.15, 0.70, 0.44),
        "brief": "small transformer hut with radiator fins, roof "
                 "insulators and an embossed warning plate",
    },
    "pylon": {
        "fn": pylon, "focus": (0.0, 0.15, 1.004), "k": 253,
        "plinth": (0.0, 0.15, 0.62, 0.40),
        "brief": "lattice-free high-voltage pole with two crossarms and "
                 "hanging insulator strings",
    },
    "lamp-pole": {
        "fn": lamp_pole, "focus": (0.0, 0.25, 1.002), "k": 302,
        "plinth": (0.0, 0.25, 0.70, 0.50),
        "brief": "street lamp pole with an outreach arm and a lamp head",
    },
    "pole-nn": {
        "fn": pole_nn, "focus": (0.0, 0.15, 0.873), "k": 307,
        "plinth": (0.0, 0.15, 0.60, 0.38),
        "brief": "concrete low-voltage pole with a crossarm, insulators "
                 "and a meter box with a drop wire",
    },
}
