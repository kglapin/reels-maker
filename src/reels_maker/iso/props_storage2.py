"""Iso gallery props batch: storage2 (battery storage + safety, 127-141).

Builders take ``(q, cx, cy, P)`` with all coordinates relative to the
placement center. Rules: overlap mating parts >= 0.005 (never
exact-touch), NO contact_shadow anywhere, mid-tone palette (nothing below
RGB 60 except tiny dots), hero element biggest, stubs start AT parent
surfaces, proud details painted AFTER parents, details only on +X/+Y
faces, no text decals (embossed lines only).
"""
from __future__ import annotations

import math

from .world import _cylinder, chamfered_box


def battery_rack(q, cx, cy, P):
    """Battery rack cabinet: feet, skirt, hero body, cap, 3 proud modules, display."""
    for fx in (cx - 0.22, cx + 0.22):
        q.boxg((fx - 0.05, cy - 0.12, 0.0), (fx + 0.05, cy + 0.12, 0.06),
              (110, 122, 112), (92, 104, 94), (130, 142, 130))
    q.boxg((cx - 0.30, cy - 0.16, 0.04), (cx + 0.30, cy + 0.16, 0.12),
          (140, 154, 144), (118, 132, 122), (160, 174, 162))
    q.boxg((cx - 0.28, cy - 0.14, 0.10), (cx + 0.28, cy + 0.14, 1.05),
          (168, 184, 172), (140, 158, 146), (190, 204, 192))
    q.boxg((cx - 0.29, cy - 0.15, 1.03), (cx + 0.29, cy + 0.15, 1.09),
          (140, 154, 144), (118, 132, 122), (160, 174, 162))
    fy = cy + 0.141
    q.line([(cx, fy, 0.13), (cx, fy, 1.01)], (110, 124, 114), 0.8)
    for j in range(3):
        z0 = 0.20 + j * 0.26
        q.boxg((cx - 0.20, cy + 0.135, z0 - 0.01),
              (cx + 0.20, cy + 0.175, z0 + 0.17),
              (120, 150, 135), (100, 128, 114), (140, 170, 152))
        q.line([(cx - 0.16, cy + 0.176, z0 + 0.08),
                (cx + 0.16, cy + 0.176, z0 + 0.08)], (90, 110, 100), 0.8)
    q.fp(cx - 0.08, cx + 0.08, cy + 0.176, 0.80, 0.88, (62, 76, 70))
    q.dot((cx - 0.14, cy + 0.177, 0.84), 0.9, (110, 190, 170, 255))
    q.dot((cx + 0.14, cy + 0.177, 0.84), 0.9, (255, 176, 92, 255))
    for j in range(4):
        vz = 0.30 + j * 0.12
        q.boxg((cx + 0.275, cy - 0.08, vz), (cx + 0.295, cy + 0.08, vz + 0.035),
              (96, 112, 102), (96, 112, 102), (96, 112, 102))
    q.ao(cx, cy, 0.45)


def battery_module(q, cx, cy, P):
    """Single LFP block close-up: lid, top terminals, rear handle, side ribs."""
    q.boxg((cx - 0.32, cy - 0.18, 0.0), (cx + 0.32, cy + 0.18, 0.05),
          (120, 132, 122), (100, 112, 102), (140, 152, 142))
    chamfered_box(q, (cx - 0.30, cy - 0.16, 0.03), (cx + 0.30, cy + 0.16, 0.42),
                  chamfer=0.022, c=(142, 158, 168), dl=0.12)
    q.boxg((cx - 0.31, cy - 0.17, 0.40), (cx + 0.31, cy + 0.17, 0.46),
          (130, 148, 156), (108, 126, 134), (152, 168, 176))
    for tx in (cx - 0.12, cx + 0.12):
        _cylinder(q, tx, cy + 0.08, 0.44, 0.55, 0.035,
                  (198, 132, 82), (150, 96, 58), (218, 152, 100), n=12)
    q.dot((cx - 0.12, cy + 0.08, 0.605), 0.9, (150, 96, 58, 255))
    q.dot((cx + 0.12, cy + 0.08, 0.605), 0.9, (150, 96, 58, 255))
    for hx in (cx - 0.15, cx + 0.15):
        q.boxg((hx - 0.025, cy - 0.13, 0.44), (hx + 0.025, cy - 0.07, 0.58),
              (96, 110, 100), (80, 94, 84), (116, 130, 118))
    q.boxg((cx - 0.175, cy - 0.13, 0.555), (cx + 0.175, cy - 0.07, 0.595),
          (96, 110, 100), (80, 94, 84), (116, 130, 118))
    for j in range(3):
        rz = 0.12 + j * 0.10
        q.boxg((cx + 0.295, cy - 0.10, rz), (cx + 0.315, cy + 0.10, rz + 0.04),
              (108, 126, 134), (108, 126, 134), (108, 126, 134))
    q.dot((cx - 0.20, cy + 0.162, 0.30), 0.9, (110, 190, 170, 255))
    q.line([(cx - 0.10, cy + 0.161, 0.14), (cx + 0.10, cy + 0.161, 0.14)],
           (110, 124, 132), 0.8)
    q.line([(cx - 0.10, cy + 0.161, 0.18), (cx + 0.10, cy + 0.161, 0.18)],
           (110, 124, 132), 0.8)


def bms_box(q, cx, cy, P):
    """Small BMS controller box on feet: lid, LEDs, connectors, embossed bars."""
    for fx in (cx - 0.13, cx + 0.13):
        q.boxg((fx - 0.035, cy - 0.09, 0.0), (fx + 0.035, cy + 0.09, 0.05),
              (110, 122, 112), (92, 104, 94), (130, 142, 130))
    q.boxg((cx - 0.20, cy - 0.12, 0.03), (cx + 0.20, cy + 0.12, 0.35),
          (158, 172, 178), (130, 144, 150), (180, 192, 198))
    q.boxg((cx - 0.21, cy - 0.13, 0.33), (cx + 0.21, cy + 0.13, 0.38),
          (130, 144, 150), (108, 122, 128), (152, 164, 170))
    q.fp(cx - 0.16, cx + 0.08, cy + 0.121, 0.21, 0.33, (62, 76, 70))
    for i, col in enumerate(((110, 190, 170), (255, 176, 92), (110, 190, 170))):
        q.dot((cx - 0.10 + i * 0.06, cy + 0.122, 0.27), 1.8, col + (255,))
    for sx in (cx - 0.17, cx + 0.17):
        for sz in (0.345, 0.365):
            q.dot((sx, cy + 0.131, sz), 0.8, (90, 98, 90, 255))
    for j in range(3):
        vz = 0.10 + j * 0.06
        q.boxg((cx + 0.195, cy - 0.06, vz), (cx + 0.21, cy + 0.06, vz + 0.03),
              (80, 94, 102), (80, 94, 102), (80, 94, 102))
    for j in range(2):
        q.line([(cx - 0.14, cy + 0.121, 0.12 + j * 0.04),
                (cx + 0.02, cy + 0.121, 0.12 + j * 0.04)],
               (105, 120, 126), 0.8)
    for gx in (cx - 0.09, cx + 0.09):
        q.boxg((gx - 0.045, cy + 0.115, 0.02), (gx + 0.045, cy + 0.155, 0.16),
              (96, 110, 100), (80, 94, 84), (116, 130, 118))
        q.boxg((gx - 0.055, cy + 0.105, 0.13), (gx + 0.055, cy + 0.165, 0.17),
              (80, 94, 84), (66, 80, 70), (100, 114, 102))
        q.dot((gx, cy + 0.166, 0.15), 0.8, (200, 210, 200, 255))


def busbar(q, cx, cy, P):
    """Copper busbar set: base rail, 3 insulators, 3 stacked copper bars, bolts."""
    q.boxg((cx - 0.34, cy - 0.07, 0.0), (cx + 0.34, cy + 0.07, 0.08),
          (120, 132, 122), (100, 112, 102), (140, 152, 142))
    for ix in (cx - 0.20, cx, cx + 0.20):
        _cylinder(q, ix, cy, 0.06, 0.30, 0.045,
                  (150, 160, 150), (110, 124, 114), (170, 180, 170), n=12)
    for j in range(3):
        z0 = 0.28 + j * 0.07
        q.boxg((cx - 0.32, cy - 0.05, z0), (cx + 0.32, cy + 0.05, z0 + 0.045),
              (198, 132, 82), (150, 96, 58), (218, 152, 100))
    for ix in (cx - 0.20, cx, cx + 0.20):
        q.dot((ix, cy, 0.475), 0.9, (120, 80, 50, 255))


def fuse_switch(q, cx, cy, P):
    """Fuse-switch disconnector: back plate, hero body, lever, fuse clips."""
    q.boxg((cx - 0.16, cy - 0.10, 0.0), (cx + 0.16, cy + 0.10, 0.05),
          (120, 132, 122), (100, 112, 102), (140, 152, 142))
    q.boxg((cx - 0.22, cy - 0.12, 0.03), (cx + 0.22, cy + 0.06, 0.75),
          (150, 160, 150), (122, 134, 124), (170, 180, 170))
    q.boxg((cx - 0.12, cy + 0.055, 0.22), (cx + 0.12, cy + 0.14, 0.60),
          (130, 144, 152), (104, 118, 126), (152, 164, 172))
    q.boxg((cx - 0.10, cy + 0.135, 0.585), (cx + 0.10, cy + 0.175, 0.68),
          (104, 118, 126), (84, 98, 106), (124, 138, 146))
    q.boxg((cx - 0.14, cy + 0.165, 0.42), (cx + 0.14, cy + 0.205, 0.50),
          (198, 132, 82), (150, 96, 58), (218, 152, 100))
    lx0, lz0, lx1, lz1, hw = cx - 0.02, 0.55, cx + 0.16, 0.78, 0.028
    dx, dz = lx1 - lx0, lz1 - lz0
    ln = math.hypot(dx, dz)
    nx, nz = -dz / ln * hw, dx / ln * hw
    ly = cy + 0.178
    q.poly([(lx0 + nx, ly, lz0 + nz), (lx0 - nx, ly, lz0 - nz),
            (lx1 - nx, ly, lz1 - nz), (lx1 + nx, ly, lz1 + nz)],
           (96, 110, 100))
    q.dot((lx1, ly, lz1 + 0.01), 1.6, (200, 70, 60, 255))
    for tx in (cx - 0.10, cx + 0.10):
        q.boxg((tx - 0.022, cy + 0.16, 0.405), (tx + 0.022, cy + 0.21, 0.515),
              (84, 98, 106), (68, 82, 90), (104, 118, 126))
    q.boxg((cx - 0.08, cy + 0.055, 0.10), (cx + 0.08, cy + 0.135, 0.18),
          (96, 110, 100), (80, 94, 84), (116, 130, 118))
    q.boxg((cx - 0.08, cy + 0.055, 0.66), (cx + 0.08, cy + 0.135, 0.74),
          (96, 110, 100), (80, 94, 84), (116, 130, 118))


def contactor(q, cx, cy, P):
    """Contactor block: base, hero body, lid, top terminals, side aux block."""
    q.boxg((cx - 0.18, cy - 0.11, 0.0), (cx + 0.18, cy + 0.11, 0.05),
          (120, 132, 122), (100, 112, 102), (140, 152, 142))
    q.boxg((cx - 0.16, cy - 0.10, 0.03), (cx + 0.16, cy + 0.10, 0.42),
          (140, 152, 160), (112, 124, 132), (162, 172, 180))
    q.boxg((cx - 0.17, cy - 0.11, 0.40), (cx + 0.17, cy + 0.11, 0.46),
          (120, 132, 140), (98, 110, 118), (142, 152, 160))
    for i in range(4):
        tx = cx - 0.12 + i * 0.08
        q.boxg((tx - 0.028, cy - 0.06, 0.44), (tx + 0.028, cy + 0.06, 0.55),
              (170, 178, 168), (140, 150, 140), (190, 198, 188))
        q.dot((tx, cy, 0.555), 0.8, (90, 100, 92, 255))
    q.boxg((cx + 0.155, cy - 0.04, 0.12), (cx + 0.225, cy + 0.08, 0.34),
          (168, 130, 84), (130, 96, 60), (188, 150, 104))
    q.dot((cx - 0.08, cy + 0.102, 0.32), 1.0, (110, 190, 170, 255))
    q.line([(cx - 0.12, cy + 0.101, 0.14), (cx + 0.02, cy + 0.101, 0.14)],
           (100, 114, 122), 0.8)
    q.line([(cx - 0.12, cy + 0.101, 0.18), (cx + 0.02, cy + 0.101, 0.18)],
           (100, 114, 122), 0.8)


def control_cabinet(q, cx, cy, P):
    """Tall control cabinet: skirt, hero door body, cap, vents, handle."""
    for fx in (cx - 0.24, cx + 0.24):
        q.box((fx - 0.05, cy - 0.12, 0.0), (fx + 0.05, cy + 0.12, 0.06),
              (110, 122, 112), (92, 104, 94), (130, 142, 130))
    q.box((cx - 0.30, cy - 0.16, 0.04), (cx + 0.30, cy + 0.16, 0.14),
          (130, 142, 150), (108, 120, 128), (150, 162, 170))
    q.box((cx - 0.28, cy - 0.14, 0.12), (cx + 0.28, cy + 0.14, 1.10),
          (168, 182, 190), (138, 152, 160), (190, 202, 210))
    q.box((cx - 0.29, cy - 0.15, 1.08), (cx + 0.29, cy + 0.15, 1.14),
          (130, 142, 150), (108, 120, 128), (150, 162, 170))
    fy = cy + 0.141
    q.line([(cx - 0.24, fy, 0.20), (cx + 0.24, fy, 0.20)], (115, 130, 138), 0.8)
    q.line([(cx, fy, 0.20), (cx, fy, 1.04)], (115, 130, 138), 0.8)
    for j in range(5):
        vz = 0.30 + j * 0.08
        q.box((cx - 0.16, cy + 0.135, vz), (cx + 0.02, cy + 0.155, vz + 0.035),
              (80, 94, 102), (80, 94, 102), (80, 94, 102))
    q.box((cx + 0.12, cy + 0.135, 0.55), (cx + 0.17, cy + 0.175, 0.75),
          (96, 110, 118), (80, 94, 102), (116, 130, 138))
    q.dot((cx - 0.18, cy + 0.142, 0.92), 1.0, (110, 190, 170, 255))
    q.dot((cx - 0.12, cy + 0.142, 0.92), 1.0, (255, 176, 92, 255))


def cable_ladder(q, cx, cy, P):
    """Cable ladder section: two rails on pads, seven rungs, top caps."""
    for rx in (cx - 0.18, cx + 0.18):
        q.box((rx - 0.05, cy - 0.07, 0.0), (rx + 0.05, cy + 0.07, 0.05),
              (120, 132, 122), (100, 112, 102), (140, 152, 142))
        q.box((rx - 0.025, cy - 0.05, 0.03), (rx + 0.025, cy + 0.05, 0.95),
              (150, 162, 152), (122, 136, 126), (170, 182, 172))
        q.box((rx - 0.032, cy - 0.057, 0.93), (rx + 0.032, cy + 0.057, 0.98),
              (120, 132, 122), (100, 112, 102), (140, 152, 142))
    for j in range(7):
        rz = 0.12 + j * 0.115
        q.box((cx - 0.215, cy - 0.03, rz - 0.02),
              (cx + 0.215, cy + 0.03, rz + 0.02),
              (168, 180, 168), (140, 154, 142), (188, 200, 188))


def earth_bar(q, cx, cy, P):
    """Earthing bar: two posts, copper bar, 4 clamps with bolt dots."""
    for px in (cx - 0.26, cx + 0.26):
        q.box((px - 0.05, cy - 0.06, 0.0), (px + 0.05, cy + 0.06, 0.05),
              (120, 132, 122), (100, 112, 102), (140, 152, 142))
        q.box((px - 0.035, cy - 0.045, 0.03), (px + 0.035, cy + 0.045, 0.34),
              (150, 160, 150), (122, 134, 124), (170, 180, 170))
        q.box((px - 0.045, cy - 0.055, 0.30), (px + 0.045, cy + 0.055, 0.35),
              (120, 132, 122), (100, 112, 102), (140, 152, 142))
    q.box((cx - 0.30, cy - 0.04, 0.315), (cx + 0.30, cy + 0.04, 0.365),
          (198, 132, 82), (150, 96, 58), (218, 152, 100))
    for tx in (cx - 0.18, cx - 0.06, cx + 0.06, cx + 0.18):
        q.box((tx - 0.03, cy - 0.045, 0.30), (tx + 0.03, cy + 0.045, 0.38),
              (110, 124, 114), (90, 104, 94), (130, 144, 132))
        q.dot((tx, cy + 0.046, 0.34), 0.9, (200, 210, 200, 255))


def warning_sign(q, cx, cy, P):
    """Warning plate on two posts: cap rail, embossed border + bars, no text."""
    for px in (cx - 0.20, cx + 0.20):
        q.box((px - 0.035, cy - 0.035, 0.0), (px + 0.035, cy + 0.035, 0.05),
              (120, 132, 122), (100, 112, 102), (140, 152, 142))
        q.box((px - 0.028, cy - 0.028, 0.03), (px + 0.028, cy + 0.028, 0.62),
              (110, 124, 114), (90, 104, 94), (130, 144, 132))
    q.box((cx - 0.32, cy - 0.03, 0.42), (cx + 0.32, cy + 0.05, 0.72),
          (232, 190, 100), (200, 158, 76), (242, 206, 122))
    q.box((cx - 0.33, cy - 0.04, 0.715), (cx + 0.33, cy + 0.06, 0.755),
          (150, 160, 150), (122, 134, 124), (170, 180, 170))
    fy = cy + 0.051
    q.line([(cx - 0.28, fy, 0.475), (cx + 0.28, fy, 0.475)],
           (150, 100, 50), 0.9)
    q.line([(cx - 0.28, fy, 0.665), (cx + 0.28, fy, 0.665)],
           (150, 100, 50), 0.9)
    q.line([(cx - 0.28, fy, 0.475), (cx - 0.28, fy, 0.665)],
           (150, 100, 50), 0.9)
    q.line([(cx + 0.28, fy, 0.475), (cx + 0.28, fy, 0.665)],
           (150, 100, 50), 0.9)
    for bz in (0.52, 0.57, 0.62):
        q.box((cx - 0.20, fy - 0.006, bz), (cx + 0.20, fy + 0.008, bz + 0.025),
              (120, 110, 90), (120, 110, 90), (120, 110, 90))


def lockout_kit(q, cx, cy, P):
    """Lockout tag box: body, lid, hasp, two padlocks with shackles."""
    q.box((cx - 0.20, cy - 0.12, 0.0), (cx + 0.20, cy + 0.12, 0.05),
          (120, 132, 122), (100, 112, 102), (140, 152, 142))
    q.box((cx - 0.18, cy - 0.10, 0.03), (cx + 0.18, cy + 0.10, 0.40),
          (200, 70, 60), (160, 52, 44), (220, 96, 84))
    q.box((cx - 0.19, cy - 0.11, 0.38), (cx + 0.19, cy + 0.11, 0.44),
          (160, 52, 44), (128, 42, 36), (180, 66, 56))
    q.fp(cx - 0.12, cx + 0.12, cy + 0.102, 0.16, 0.30, (232, 190, 100))
    q.line([(cx - 0.10, cy + 0.103, 0.19), (cx + 0.10, cy + 0.103, 0.19)],
           (150, 100, 50), 0.8)
    q.line([(cx - 0.10, cy + 0.103, 0.27), (cx + 0.10, cy + 0.103, 0.27)],
           (150, 100, 50), 0.8)
    for lx in (cx - 0.09, cx + 0.09):
        q.box((lx - 0.045, cy + 0.095, 0.30), (lx + 0.045, cy + 0.135, 0.42),
              (232, 190, 100), (200, 158, 76), (242, 206, 122))
        q.line([(lx - 0.028, cy + 0.136, 0.42), (lx - 0.028, cy + 0.136, 0.48)],
               (150, 160, 150), 1.2)
        q.line([(lx + 0.028, cy + 0.136, 0.42), (lx + 0.028, cy + 0.136, 0.48)],
               (150, 160, 150), 1.2)
        q.line([(lx - 0.028, cy + 0.136, 0.48), (lx + 0.028, cy + 0.136, 0.48)],
               (150, 160, 150), 1.2)


def extinguisher(q, cx, cy, P):
    """Fire extinguisher: ring base, red cylinder, valve, hose, gauge."""
    _cylinder(q, cx, cy, 0.02, 0.08, 0.13,
              (110, 124, 114), (90, 104, 94), (130, 144, 132), n=16)
    _cylinder(q, cx, cy, 0.06, 0.60, 0.11,
              (188, 64, 56), (150, 50, 42), (208, 88, 76), n=24)
    _cylinder(q, cx, cy, 0.56, 0.68, 0.06,
              (120, 134, 122), (96, 110, 100), (140, 154, 142), n=12)
    q.box((cx - 0.035, cy - 0.035, 0.63), (cx + 0.035, cy + 0.035, 0.72),
          (150, 160, 150), (122, 134, 124), (170, 180, 170))
    q.box((cx - 0.09, cy - 0.02, 0.66), (cx + 0.09, cy + 0.02, 0.71),
          (96, 110, 118), (80, 94, 102), (116, 130, 138))
    q.box((cx + 0.10, cy - 0.03, 0.50), (cx + 0.135, cy + 0.02, 0.68),
          (120, 134, 124), (100, 114, 104), (140, 154, 142))
    q.box((cx + 0.095, cy - 0.035, 0.60), (cx + 0.14, cy + 0.025, 0.68),
          (96, 110, 100), (80, 94, 84), (116, 130, 118))
    q.box((cx + 0.10, cy - 0.035, 0.30), (cx + 0.135, cy + 0.015, 0.52),
          (120, 134, 124), (100, 114, 104), (140, 154, 142))
    q.box((cx + 0.095, cy - 0.04, 0.22), (cx + 0.135, cy + 0.01, 0.32),
          (150, 160, 150), (122, 134, 124), (170, 180, 170))
    q.box((cx - 0.085, cy + 0.108, 0.20), (cx + 0.085, cy + 0.122, 0.42),
          (240, 238, 228), (210, 206, 192), (248, 246, 236))
    for pz in (0.24, 0.30, 0.36):
        q.box((cx - 0.06, cy + 0.120, pz), (cx + 0.06, cy + 0.126, pz + 0.03),
              (170, 60, 50), (170, 60, 50), (170, 60, 50))
    q.line([(cx - 0.05, cy + 0.124, 0.28), (cx + 0.05, cy + 0.124, 0.28)],
           (150, 140, 120), 0.8)
    q.disc_y(cx + 0.0, cy + 0.1235, 0.40, 0.052, (80, 94, 84))
    q.disc_y(cx + 0.0, cy + 0.1245, 0.40, 0.042, (245, 248, 242))
    q.line([(cx + 0.0, cy + 0.125, 0.40), (cx + 0.028, cy + 0.125, 0.415)],
           (200, 62, 52), 1.0)
    q.dot((cx + 0.0, cy + 0.1255, 0.40), 0.7, (90, 100, 92, 255))


def estop(q, cx, cy, P):
    """Emergency stop: pad, post, yellow collar, black ring, red mushroom."""
    q.boxg((cx - 0.10, cy - 0.09, 0.0), (cx + 0.10, cy + 0.09, 0.05),
          (120, 132, 122), (100, 112, 102), (140, 152, 142))
    q.boxg((cx - 0.07, cy - 0.06, 0.03), (cx + 0.07, cy + 0.06, 0.72),
          (150, 160, 150), (122, 134, 124), (170, 180, 170))
    q.boxg((cx - 0.13, cy - 0.10, 0.68), (cx + 0.13, cy + 0.10, 0.80),
          (232, 190, 100), (200, 158, 76), (242, 206, 122))
    _cylinder(q, cx, cy, 0.76, 0.80, 0.105,
              (80, 90, 82), (64, 74, 66), (100, 110, 102), n=16)
    _cylinder(q, cx, cy, 0.78, 0.88, 0.088,
              (200, 70, 60), (160, 52, 44), (220, 96, 84), n=24)


def smoke_detector(q, cx, cy, P):
    """Ceiling smoke detector: mount chip, drop rod, dome with LED."""
    q.box((cx - 0.25, cy - 0.15, 0.53), (cx + 0.25, cy + 0.15, 0.59),
          (200, 210, 196), (170, 182, 168), (216, 226, 212))
    _cylinder(q, cx, cy, 0.35, 0.55, 0.035,
              (150, 160, 150), (122, 134, 124), (170, 180, 170), n=12)
    _cylinder(q, cx, cy, 0.31, 0.355, 0.055,
              (120, 132, 122), (100, 112, 102), (140, 152, 142), n=12)
    _cylinder(q, cx, cy, 0.19, 0.33, 0.13,
              (238, 242, 234), (204, 214, 200), (248, 250, 244), n=24)
    q.dot((cx + 0.0, cy + 0.131, 0.26), 1.1, (200, 62, 52, 255))
    q.line([(cx - 0.08, cy + 0.131, 0.30), (cx + 0.08, cy + 0.131, 0.30)],
           (180, 190, 180), 0.8)


def first_aid(q, cx, cy, P):
    """First-aid wall box: chip, green cabinet, white cross, seam lines."""
    q.box((cx - 0.30, cy - 0.14, 0.0), (cx + 0.30, cy + 0.02, 0.95),
          (226, 232, 218), (200, 210, 194), (238, 242, 232))
    q.box((cx - 0.31, cy - 0.15, 0.93), (cx + 0.31, cy + 0.03, 0.98),
          (200, 210, 194), (200, 210, 194), (200, 210, 194))
    q.box((cx - 0.20, cy + 0.015, 0.20), (cx + 0.20, cy + 0.135, 0.70),
          (120, 170, 120), (96, 140, 98), (145, 195, 145))
    q.box((cx - 0.21, cy + 0.010, 0.68), (cx + 0.21, cy + 0.14, 0.73),
          (96, 140, 98), (80, 120, 82), (120, 170, 120))
    q.box((cx - 0.035, cy + 0.13, 0.36), (cx + 0.035, cy + 0.155, 0.56),
          (245, 248, 242), (225, 230, 222), (250, 252, 248))
    q.box((cx - 0.09, cy + 0.13, 0.43), (cx + 0.09, cy + 0.155, 0.49),
          (245, 248, 242), (225, 230, 222), (250, 252, 248))
    cfy = cy + 0.136
    q.line([(cx - 0.17, cfy, 0.25), (cx + 0.17, cfy, 0.25)],
           (90, 130, 92), 0.8)


def bess_container(q, cx, cy, P):
    """Container BESS: corner feet, sage hero, top castings, double
    doors with hinges + lock rods, vent slats, west HVAC unit."""
    steel = ((70, 80, 72), (56, 66, 58), (88, 98, 90))
    sage = ((168, 182, 158), (140, 156, 132), (188, 200, 178))
    sage_d = ((150, 166, 140), (126, 142, 116), (170, 186, 160))
    for fx in (cx - 1.02, cx + 1.02):
        for fy in (cy - 0.40, cy + 0.40):
            q.boxg((fx - 0.09, fy - 0.09, 0.0), (fx + 0.09, fy + 0.09, 0.16),
                   *steel)
    chamfered_box(q, (cx - 1.20, cy - 0.48, 0.10), (cx + 1.20, cy + 0.48, 1.20),
                  chamfer=0.05, c=(158, 172, 148), dl=0.12)
    for hx in (cx - 1.20, cx + 1.20):
        for hy in (cy - 0.48, cy + 0.48):
            q.boxg((hx - 0.07, hy - 0.07, 1.13), (hx + 0.07, hy + 0.07, 1.27),
                   *steel)
    for dx in (cx + 0.12, cx + 0.65):
        q.boxg((dx, cy + 0.475, 0.20), (dx + 0.51, cy + 0.525, 1.10), *sage_d)
    for hx in (cx + 0.12, cx + 1.16):
        for hz in (0.40, 0.90):
            q.boxg((hx - 0.03, cy + 0.52, hz - 0.045),
                   (hx + 0.03, cy + 0.56, hz + 0.045), *steel)
    for rx in (cx + 0.375, cx + 0.905):
        q.boxg((rx - 0.018, cy + 0.52, 0.24), (rx + 0.018, cy + 0.56, 1.06),
               *steel)
        q.boxg((rx, cy + 0.52, 0.60), (rx + 0.10, cy + 0.56, 0.66), *steel)
    for vz in (0.55, 0.70, 0.85):
        q.fp(cx - 1.05, cx - 0.20, cy + 0.482, vz, vz + 0.025, (80, 92, 82))
    q.boxg((cx - 1.48, cy - 0.28, 0.30), (cx - 1.15, cy + 0.28, 0.90),
           (200, 208, 198), (170, 180, 168), (216, 224, 212))
    for vz in (0.45, 0.65):
        q.boxg((cx - 1.50, cy - 0.20, vz), (cx - 1.46, cy + 0.20, vz + 0.03),
               *steel)
    q.fp(cx + 0.70, cx + 1.10, cy + 0.527, 0.88, 1.00, (210, 160, 90))


def ess_cabinet(q, cx, cy, P):
    """Outdoor ESS cabinet: base, sage hero, rain canopy, double door
    with display + LEDs, vent slats, cable-entry conduits."""
    steel = ((70, 80, 72), (56, 66, 58), (88, 98, 90))
    sage = ((172, 186, 160), (144, 160, 134), (192, 204, 180))
    sage_d = ((150, 166, 140), (126, 142, 116), (170, 186, 160))
    q.boxg((cx - 0.50, cy - 0.36, -0.02), (cx + 0.50, cy + 0.36, 0.14), *steel)
    chamfered_box(q, (cx - 0.45, cy - 0.32, 0.10), (cx + 0.45, cy + 0.32, 1.30),
                  chamfer=0.035, c=(162, 176, 150), dl=0.12)
    q.boxg((cx - 0.51, cy - 0.38, 1.28), (cx + 0.51, cy + 0.38, 1.40),
           *sage_d)
    q.boxg((cx - 0.40, cy + 0.315, 0.25), (cx - 0.02, cy + 0.36, 1.15),
           *sage_d)
    q.boxg((cx + 0.02, cy + 0.315, 0.25), (cx + 0.40, cy + 0.36, 1.15),
           *sage_d)
    for hx in (cx - 0.07, cx + 0.07):
        q.boxg((hx - 0.025, cy + 0.355, 0.62), (hx + 0.025, cy + 0.39, 0.80),
               *steel)
    q.fp(cx - 0.34, cx - 0.12, cy + 0.362, 0.86, 1.00, (62, 76, 70))
    q.fp(cx - 0.30, cx - 0.16, cy + 0.364, 0.90, 0.94, (110, 200, 130))
    q.dot((cx + 0.30, cy + 0.362, 1.02), 1.2, (110, 200, 130, 255))
    q.dot((cx + 0.30, cy + 0.362, 0.94), 1.2, (230, 150, 80, 255))
    for vz in (0.32, 0.40, 0.48):
        q.fp(cx - 0.38, cx + 0.38, cy + 0.362, vz, vz + 0.03, (80, 92, 82))
    for gx in (cx - 0.25, cx + 0.25):
        q.boxg((gx - 0.025, cy + 0.26, 0.08), (gx + 0.025, cy + 0.34, 0.30),
               *steel)


PROPS = {
    "battery-rack": {"fn": battery_rack, "focus": (0.0, 0.15, 0.60),
                     "k": 420, "plinth": (0.0, 0.15, 0.60, 0.38),
                     "brief": "battery rack cabinet with modules and display"},
    "battery-module": {"fn": battery_module, "focus": (0.0, 0.15, 0.30),
                       "k": 560, "plinth": (0.0, 0.15, 0.60, 0.38),
                       "brief": "LFP battery module close-up with terminals and handle"},
    "bms-box": {"fn": bms_box, "focus": (0.0, 0.15, 0.20), "k": 620,
                "plinth": (0.0, 0.15, 0.50, 0.32),
                "brief": "small BMS controller box with LEDs"},
    "busbar": {"fn": busbar, "focus": (0.0, 0.15, 0.22), "k": 560,
               "plinth": (0.0, 0.15, 0.60, 0.34),
               "brief": "copper busbar set with insulators"},
    "fuse-switch": {"fn": fuse_switch, "focus": (0.0, 0.15, 0.40),
                    "k": 500, "plinth": (0.0, 0.15, 0.50, 0.32),
                    "brief": "fuse-switch disconnector with lever"},
    "contactor": {"fn": contactor, "focus": (0.0, 0.15, 0.27), "k": 580,
                  "plinth": (0.0, 0.15, 0.50, 0.32),
                  "brief": "contactor block with terminals"},
    "control-cabinet": {"fn": control_cabinet, "focus": (0.0, 0.15, 0.62),
                        "k": 400, "plinth": (0.0, 0.15, 0.60, 0.38),
                        "brief": "tall control cabinet with door and vents"},
    "cable-ladder": {"fn": cable_ladder, "focus": (0.0, 0.15, 0.47),
                     "k": 460, "plinth": (0.0, 0.15, 0.52, 0.34),
                     "brief": "cable ladder section"},
    "earth-bar": {"fn": earth_bar, "focus": (0.0, 0.15, 0.20), "k": 580,
                  "plinth": (0.0, 0.15, 0.58, 0.34),
                  "brief": "earthing bar with terminals"},
    "warning-sign": {"fn": warning_sign, "focus": (0.0, 0.15, 0.40),
                     "k": 500, "plinth": (0.0, 0.15, 0.58, 0.34),
                     "brief": "warning plate on posts, embossed bars, no text"},
    "lockout-kit": {"fn": lockout_kit, "focus": (0.0, 0.15, 0.24),
                    "k": 580, "plinth": (0.0, 0.15, 0.52, 0.32),
                    "brief": "lockout tag box with padlocks"},
    "extinguisher": {"fn": extinguisher, "focus": (0.0, 0.15, 0.36),
                     "k": 540, "plinth": (0.0, 0.15, 0.48, 0.30),
                     "brief": "fire extinguisher with hose and gauge"},
    "estop": {"fn": estop, "focus": (0.0, 0.15, 0.44), "k": 520,
              "plinth": (0.0, 0.15, 0.46, 0.30),
              "brief": "red emergency stop mushroom on yellow collar"},
    "smoke-detector": {"fn": smoke_detector, "focus": (0.0, 0.15, 0.32),
                       "k": 460, "plinth": (0.0, 0.15, 0.38, 0.24),
                       "brief": "ceiling smoke detector dome with LED"},
    "first-aid": {"fn": first_aid, "focus": (0.0, 0.15, 0.47), "k": 420,
                  "plinth": (0.0, 0.15, 0.52, 0.32),
                  "brief": "first aid wall box with cross emblem"},
    "bess-container": {"fn": bess_container, "focus": (0.0, 0.15, 0.65),
                       "k": 220, "plinth": (0.0, 0.15, 2.90, 1.25),
                       "brief": "container battery storage with doors and HVAC"},
    "ess-cabinet": {"fn": ess_cabinet, "focus": (0.0, 0.15, 0.78),
                    "k": 320, "plinth": (0.0, 0.15, 0.60, 0.38),
                    "brief": "outdoor ESS cabinet with display and conduits"}
}
