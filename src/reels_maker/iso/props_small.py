"""Small gallery props batch (55-61): van, ladder, drone, savings, calendar, weather, anemostat."""
from __future__ import annotations

import math


def van(q, cx, cy, P):
    """Service van: white body hero, cab glass, blank logo plate, 4 proud wheels."""
    # Bumpers first (behind body ends), then body, then proud details.
    q.box((cx - 0.505, cy - 0.13, 0.10), (cx - 0.45, cy + 0.13, 0.20),
          (120, 132, 124), (96, 108, 98), (140, 152, 142))
    q.box((cx + 0.45, cy - 0.13, 0.10), (cx + 0.505, cy + 0.13, 0.20),
          (120, 132, 124), (96, 108, 98), (140, 152, 142))
    q.box((cx - 0.46, cy - 0.15, 0.12), (cx + 0.46, cy + 0.15, 0.60),
          (236, 241, 232), (170, 190, 168), (248, 250, 243))
    q.box((cx - 0.44, cy - 0.13, 0.59), (cx + 0.44, cy + 0.13, 0.63),
          (240, 246, 240), (170, 190, 168), (250, 252, 245))
    # Windshield on the +X face + side cab glass on the +Y flank.
    q.poly([(cx + 0.461, cy - 0.10, 0.34), (cx + 0.461, cy + 0.10, 0.34),
            (cx + 0.461, cy + 0.10, 0.54), (cx + 0.461, cy - 0.10, 0.54)],
           (168, 198, 212))
    q.fp(cx + 0.20, cx + 0.42, cy + 0.151, 0.38, 0.54, (168, 198, 212))
    # Mint stripe along the flank, then the blank logo plate over it.
    q.fp(cx - 0.44, cx + 0.44, cy + 0.151, 0.20, 0.26, (105, 200, 120))
    q.box((cx - 0.28, cy + 0.15, 0.30), (cx + 0.02, cy + 0.168, 0.50),
          (242, 246, 238), (200, 212, 200), (248, 250, 244))
    by = cy + 0.169
    q.line([(cx - 0.25, by, 0.33), (cx - 0.01, by, 0.33)], (150, 164, 152), 0.8)
    q.line([(cx - 0.25, by, 0.47), (cx - 0.01, by, 0.47)], (150, 164, 152), 0.8)
    q.line([(cx - 0.25, by, 0.33), (cx - 0.25, by, 0.47)], (150, 164, 152), 0.8)
    q.line([(cx - 0.01, by, 0.33), (cx - 0.01, by, 0.47)], (150, 164, 152), 0.8)
    # Grille + headlights on the +X face (proud of the body, painted last).
    q.box((cx + 0.46, cy - 0.12, 0.18), (cx + 0.475, cy + 0.12, 0.26),
          (120, 132, 124), (120, 132, 124), (120, 132, 124))
    q.dot((cx + 0.476, cy - 0.09, 0.30), 1.2, (255, 240, 180, 255))
    q.dot((cx + 0.476, cy + 0.09, 0.30), 1.2, (255, 240, 180, 255))
    # Wheels proud of the +Y flank; hubs after the tyres.
    for wx in (cx - 0.27, cx + 0.27):
        q.disc_y(wx, cy + 0.152, 0.12, 0.13, (66, 74, 68))
        q.disc_y(wx, cy + 0.154, 0.12, 0.055, (140, 150, 140))
        q.dot((wx, cy + 0.156, 0.12), 1.0, (90, 100, 92, 255))


def ladder(q, cx, cy, P):
    """Wooden ladder leaning on a slim wall chip; feet sunk, top embedded."""
    # Wall chip + cap + grounding skirt first (far), ladder after (near).
    q.box((cx - 0.36, cy - 0.14, -0.02), (cx + 0.36, cy + 0.04, 0.08),
          (150, 164, 152), (120, 136, 124), (170, 182, 170))
    q.box((cx - 0.34, cy - 0.12, 0.0), (cx + 0.34, cy + 0.02, 1.02),
          (226, 232, 218), (200, 210, 194), (238, 242, 232))
    q.box((cx - 0.35, cy - 0.13, 1.015), (cx + 0.35, cy + 0.03, 1.06),
          (200, 210, 194), (200, 210, 194), (200, 210, 194))
    # Rails: bottoms sunk below 0, tops embedded in the wall face.
    yb, yt, zt, zb = cy + 0.46, cy + 0.005, 0.94, -0.02
    for rx0 in (cx - 0.17, cx + 0.13):
        q.poly([(rx0, yb, zb), (rx0 + 0.04, yb, zb),
                (rx0 + 0.04, yt, zt), (rx0, yt, zt)], (206, 150, 88))
    # Rungs overlap both rails in X.
    for z in (0.10, 0.28, 0.46, 0.64, 0.82):
        s = (z - zb) / (zt - zb)
        yz = yb + (yt - yb) * s
        q.box((cx - 0.175, yz - 0.018, z - 0.018),
              (cx + 0.175, yz + 0.018, z + 0.018),
              (220, 170, 100), (180, 132, 74), (228, 182, 112))


def drone(q, cx, cy, P):
    """Quad inspection drone: skids, legs, mint body, arms, motors, rotors, camera."""
    # Skids + legs first, body over the leg tops, arms/rotors/camera last.
    for sy in (cy - 0.10, cy + 0.10):
        q.box((cx - 0.24, sy - 0.03, 0.0), (cx + 0.24, sy + 0.03, 0.05),
              (90, 104, 94), (70, 84, 74), (108, 122, 110))
    for lx in (cx - 0.14, cx + 0.14):
        for ly in (cy - 0.09, cy + 0.09):
            q.box((lx - 0.025, ly - 0.025, 0.03), (lx + 0.025, ly + 0.025, 0.34),
                  (110, 126, 114), (88, 104, 92), (128, 144, 130))
    q.box((cx - 0.17, cy - 0.12, 0.30), (cx + 0.17, cy + 0.12, 0.45),
          (105, 200, 120), (70, 150, 90), (140, 220, 150))
    q.box((cx - 0.08, cy - 0.06, 0.445), (cx + 0.08, cy + 0.06, 0.50),
          (240, 170, 95), (200, 130, 70), (250, 190, 120))
    # Arms reach out of the body sides to the four motors.
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            q.box((min(sx * 0.10, sx * 0.30) + cx, cy + sy * 0.06 - 0.03, 0.35),
                  (max(sx * 0.10, sx * 0.30) + cx, cy + sy * 0.20 + 0.03, 0.41),
                  (120, 140, 125), (95, 115, 100), (140, 158, 142))
            mx, my = cx + sx * 0.30, cy + sy * 0.20
            q.box((mx - 0.05, my - 0.05, 0.38), (mx + 0.05, my + 0.05, 0.50),
                  (80, 94, 84), (62, 76, 66), (100, 114, 102))
            q.ground_ellipse(mx, my, 0.13, 0.13, (210, 220, 210, 255), z=0.505)
    # Camera gimbal under the belly + lens dot + status LEDs on +Y.
    q.box((cx + 0.04, cy - 0.05, 0.22), (cx + 0.14, cy + 0.05, 0.31),
          (60, 72, 64), (60, 72, 64), (78, 92, 80))
    q.dot((cx + 0.09, cy + 0.052, 0.26), 1.4, (25, 32, 28, 255))
    q.dot((cx - 0.10, cy + 0.121, 0.38), 0.9, (255, 200, 120, 255))
    q.dot((cx + 0.10, cy + 0.121, 0.38), 0.9, (110, 190, 170, 255))


def savings(q, cx, cy, P):
    """Three coin stacks with a green rising arrow growing out of the tallest."""
    # Stacks: (dx, radius, height, light, dark, top).
    stacks = [(-0.26, 0.15, 0.34, (232, 186, 96), (170, 128, 62), (244, 204, 120)),
              (0.00, 0.17, 0.52, (208, 120, 78), (150, 84, 52), (224, 142, 96)),
              (0.27, 0.13, 0.26, (240, 160, 86), (176, 110, 56), (250, 180, 110))]
    for dx, r, h, cl, cd, ct in stacks:
        sx = cx + dx
        q.box((sx - r, cy - r, 0.0), (sx + r, cy + r, 0.035),
              cd, cd, cd)
        for i in range(int(h / 0.045)):
            z0 = 0.03 + i * 0.045
            q.ground_ellipse(sx, cy, r * 1.0, r * 1.0, cd, z=z0)
            q.ground_ellipse(sx, cy, r * 1.0, r * 1.0, cl, z=z0 + 0.030)
        q.ground_ellipse(sx, cy, r * 1.0, r * 1.0, ct, z=h)
    # Two flat coins leaning on stack bases (overlap the stacks).
    for px, pr, pc in ((cx + 0.02, 0.09, (232, 186, 96)),
                       (cx - 0.44, 0.09, (240, 160, 86))):
        q.ground_ellipse(px, cy + 0.22, pr, pr, (170, 128, 62), z=0.0)
        q.ground_ellipse(px, cy + 0.22, pr, pr, pc, z=0.030)
    # Arrow grows out of the tallest stack (shaft base buried in coins).
    ay = cy + 0.10
    x0, z0, x1, z1, hw = cx - 0.02, 0.40, cx + 0.30, 1.00, 0.038
    dx, dz = x1 - x0, z1 - z0
    ln = math.hypot(dx, dz)
    nx, nz = -dz / ln * hw, dx / ln * hw
    q.poly([(x0 + nx, ay, z0 + nz), (x0 - nx, ay, z0 - nz),
            (x1 - nx, ay, z1 - nz), (x1 + nx, ay, z1 + nz)], (110, 195, 120))
    q.poly([(cx + 0.36, ay, 1.08), (cx + 0.22, ay, 0.94),
            (cx + 0.38, ay, 0.90)], (110, 195, 120))


def calendar(q, cx, cy, P):
    """Standing wall calendar: board, spiral bar, line grid, one amber day."""
    q.box((cx - 0.30, cy - 0.02, 0.0), (cx + 0.30, cy + 0.16, 0.07),
          (150, 164, 152), (120, 136, 124), (170, 182, 170))
    q.box((cx + 0.18, cy - 0.14, 0.0), (cx + 0.26, cy + 0.01, 0.62),
          (180, 160, 120), (150, 130, 95), (196, 178, 140))
    q.box((cx - 0.28, cy + 0.0, 0.05), (cx + 0.28, cy + 0.08, 0.80),
          (240, 244, 232), (206, 216, 200), (248, 250, 242))
    # Spiral bar proud of the face + ring dots.
    q.box((cx - 0.30, cy + 0.075, 0.74), (cx + 0.30, cy + 0.105, 0.80),
          (90, 100, 92), (70, 80, 72), (110, 120, 112))
    for i in range(7):
        q.dot((cx - 0.24 + i * 0.08, cy + 0.107, 0.77), 0.8, (60, 70, 62, 255))
    # Header band (no text) + 3x4 day-cell grid, all embossed lines.
    q.fp(cx - 0.245, cx + 0.245, cy + 0.082, 0.665, 0.715, (170, 210, 175))
    fy = cy + 0.082
    cols, rows = 3, 4
    cw, chh, gx, gz = 0.15, 0.11, 0.02, 0.02
    x0, z0 = cx - 0.245, 0.16
    for i in range(cols + 1):
        xx = x0 + i * (cw + gx) - (gx / 2 if 0 < i < cols else 0)
        q.line([(xx, fy, z0), (xx, fy, z0 + rows * chh + (rows - 1) * gz)],
               (130, 142, 132), 0.8)
    for j in range(rows + 1):
        zz = z0 + j * (chh + gz) - (gz / 2 if 0 < j < rows else 0)
        q.line([(x0, fy, zz), (x0 + cols * cw + (cols - 1) * gx, fy, zz)],
               (130, 142, 132), 0.8)
    # The one marked day: amber fill + inner border, painted after the grid.
    mx0, mz0 = x0 + 1 * (cw + gx), z0 + 2 * (chh + gz)
    q.fp(mx0, mx0 + cw, fy + 0.001, mz0, mz0 + chh, (240, 160, 90))
    q.line([(mx0 + 0.015, fy + 0.002, mz0 + 0.015),
            (mx0 + cw - 0.015, fy + 0.002, mz0 + 0.015)], (150, 90, 50), 0.8)
    q.line([(mx0 + 0.015, fy + 0.002, mz0 + 0.015),
            (mx0 + 0.015, fy + 0.002, mz0 + chh - 0.015)], (150, 90, 50), 0.8)


def weather(q, cx, cy, P):
    """One display plate with three weather icons: sun, cloud, snowflake."""
    for px in (cx - 0.26, cx + 0.26):
        q.box((px - 0.03, cy - 0.04, 0.0), (px + 0.03, cy + 0.04, 0.34),
              (120, 134, 124), (96, 110, 100), (140, 154, 142))
    q.box((cx - 0.40, cy - 0.02, 0.30), (cx + 0.40, cy + 0.06, 0.88),
          (238, 243, 234), (204, 214, 200), (248, 250, 244))
    fy = cy + 0.064
    # Zone dividers.
    for dx in (cx - 0.133, cx + 0.133):
        q.line([(dx, fy, 0.34), (dx, fy, 0.84)], (150, 164, 152), 0.8)
    # Sun: disc + 8 rays starting inside the disc (overlap, never exact-touch).
    sx, sz = cx - 0.267, 0.60
    q.disc_y(sx, fy, sz, 0.085, (250, 200, 110))
    for k in range(8):
        a = k * math.tau / 8
        q.line([(sx + 0.06 * math.cos(a), fy, sz + 0.06 * math.sin(a)),
                (sx + 0.14 * math.cos(a), fy, sz + 0.14 * math.sin(a))],
               (240, 170, 80), 1.2)
    q.disc_y(sx, fy + 0.001, sz, 0.05, (255, 220, 140))
    # Cloud: base box + three overlapping puffs, all proud of the plate.
    mx = cx
    q.box((mx - 0.10, fy - 0.004, 0.52), (mx + 0.10, fy + 0.004, 0.60),
          (250, 252, 248), (250, 252, 248), (250, 252, 248))
    q.disc_y(mx - 0.06, fy, 0.60, 0.055, (250, 252, 248))
    q.disc_y(mx + 0.00, fy, 0.64, 0.070, (250, 252, 248))
    q.disc_y(mx + 0.06, fy, 0.60, 0.055, (250, 252, 248))
    # Snowflake: three crossed bars + hub dot.
    wx, wz = cx + 0.267, 0.60
    for k in range(3):
        a = k * math.pi / 3
        q.line([(wx - 0.10 * math.cos(a), fy, wz - 0.10 * math.sin(a)),
                (wx + 0.10 * math.cos(a), fy, wz + 0.10 * math.sin(a))],
               (170, 205, 230), 1.4)
    q.dot((wx, fy, wz), 1.2, (200, 225, 242, 255))


def anemostat(q, cx, cy, P):
    """Square ceiling vent: neck, frame, inner panel, five slots, cap."""
    q.box((cx - 0.13, cy - 0.13, 0.0), (cx + 0.13, cy + 0.13, 0.30),
          (200, 208, 200), (160, 176, 162), (216, 224, 216))
    q.box((cx - 0.28, cy + 0.02, 0.28), (cx + 0.28, cy + 0.16, 0.90),
          (225, 232, 220), (198, 210, 196), (240, 245, 236))
    q.fp(cx - 0.22, cx + 0.22, cy + 0.162, 0.34, 0.84, (245, 248, 242))
    for z in (0.40, 0.50, 0.60, 0.70, 0.80):
        q.box((cx - 0.20, cy + 0.162, z - 0.014),
              (cx + 0.20, cy + 0.172, z + 0.014),
              (74, 88, 78), (74, 88, 78), (74, 88, 78))
    for sx in (cx - 0.25, cx + 0.25):
        for sz in (0.365, 0.815):
            q.dot((sx, cy + 0.173, sz), 0.8, (60, 72, 64, 255))
    q.box((cx - 0.29, cy + 0.01, 0.895), (cx + 0.29, cy + 0.17, 0.93),
          (200, 210, 196), (200, 210, 196), (200, 210, 196))


PROPS = {
    "van": {"fn": van, "focus": (0.0, 0.15, 0.36), "k": 560,
            "plinth": (0.0, 0.15, 0.62, 0.38),
            "brief": "service van with blank logo plate"},
    "ladder": {"fn": ladder, "focus": (0.0, 0.15, 0.563), "k": 420,
               "plinth": (0.0, 0.15, 0.55, 0.34),
               "brief": "leaning ladder"},
    "drone": {"fn": drone, "focus": (0.0, 0.15, 0.35), "k": 620,
              "plinth": (0.0, 0.15, 0.55, 0.34),
              "brief": "inspection drone with camera dot"},
    "savings": {"fn": savings, "focus": (0.0, 0.15, 0.419), "k": 560,
                "plinth": (0.0, 0.15, 0.58, 0.36),
                "brief": "coin stacks with rising arrow"},
    "calendar": {"fn": calendar, "focus": (0.0, 0.15, 0.42), "k": 580,
                 "plinth": (0.0, 0.15, 0.52, 0.32),
                 "brief": "wall calendar with one marked day square"},
    "weather": {"fn": weather, "focus": (0.0, 0.15, 0.49), "k": 520,
                "plinth": (0.0, 0.15, 0.55, 0.34),
                "brief": "sun, cloud and snowflake icons on one plate"},
    "anemostat": {"fn": anemostat, "focus": (0.0, 0.15, 0.47), "k": 520,
                  "plinth": (0.0, 0.15, 0.52, 0.32),
                  "brief": "square ceiling air vent with slots"},
}
