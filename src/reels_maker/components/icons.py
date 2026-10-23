"""Vector icon primitives drawn from shapes, never emoji or random stock art.

Icons share a single stroke weight, rounded terminals and a consistent optical
size. Every icon is returned as a scene-graph group so it can be animated,
tinted and QA-checked like any other component.
"""
from __future__ import annotations

import math

from ..core.scene_graph import Node


def _stroke(width: float) -> dict:
    return {"width": max(1.0, width), "cap": "round", "join": "round"}


def group(role: str, cx: float, cy: float, size: float,
          children: list[Node]) -> Node:
    size = max(4.0, float(size))
    return Node(kind="group", role=role, children=children,
                meta={"icon": role, "size": size},
                props={"cx": cx, "cy": cy, "size": size})


def battery(cx: float, cy: float, size: float, color, *,
            level: float = .72, shell=None, role: str = "battery") -> Node:
    """A calm product-style battery with five cells and a terminal."""
    shell = shell or color
    width, height = size, size * .58
    x, y = cx - width / 2, cy - height / 2
    stroke = max(2.0, size * .035)
    radius = size * .10
    cell_gap = size * .022
    inner = width * .84
    cell_w = inner / 5 - cell_gap
    children = [
        Node(kind="round", role="battery-shell",
             props={"x": x, "y": y, "w": width, "h": height,
                    "r": radius, "fill": None,
                    "border": shell, "border_width": stroke}),
        Node(kind="round", role="battery-terminal",
             props={"x": x + width + stroke * .6, "y": cy - height * .18,
                    "w": width * .07, "h": height * .36,
                    "r": radius * .5, "fill": shell}),
    ]
    active = max(0.0, min(1.0, level)) * 5
    for index in range(5):
        visible = max(0.0, min(1.0, active - index))
        if visible <= 0:
            continue
        children.append(Node(
            kind="round", role=f"battery-cell-{index}",
            props={"x": x + (width - inner) / 2 + index * (cell_w + cell_gap),
                   "y": y + height * .14,
                   "w": cell_w, "h": height * .72 * visible,
                   "r": cell_gap * .7, "fill": color},
            meta={"fill_level": round(visible, 3)}))
    return group(role, cx, cy, size, children)


def sun(cx: float, cy: float, size: float, color, *, rays: int = 12,
        role: str = "sun") -> Node:
    radius = size * .24
    children = [Node(kind="circle", role="sun-core",
                     props={"cx": cx, "cy": cy, "r": radius, "fill": color})]
    for index in range(rays):
        angle = index * 2 * math.pi / rays
        inner = radius * 1.45
        outer = radius * 1.85
        children.append(Node(
            kind="line", role=f"sun-ray-{index}",
            props={"x1": cx + inner * math.cos(angle),
                   "y1": cy + inner * math.sin(angle),
                   "x2": cx + outer * math.cos(angle),
                   "y2": cy + outer * math.sin(angle),
                   "color": color, **_stroke(size * .028)}))
    return group(role, cx, cy, size, children)


def house(cx: float, cy: float, size: float, color, *,
          role: str = "house") -> Node:
    w, h = size * .72, size * .56
    roof = [Node(kind="path", role="roof",
                 props={"points": [(cx - w / 2 - size * .05, cy - h * .18),
                                   (cx, cy - h * .62),
                                   (cx + w / 2 + size * .05, cy - h * .18)],
                        "color": color, "closed": False,
                        **_stroke(size * .045)})]
    body = [Node(kind="round", role="body",
                 props={"x": cx - w / 2, "y": cy - h * .16, "w": w, "h": h * .7,
                        "r": size * .04, "fill": None, "border": color,
                        "border_width": size * .04}),
            Node(kind="round", role="door",
                 props={"x": cx - w * .12, "y": cy + h * .18,
                        "w": w * .24, "h": h * .34, "r": size * .02,
                        "fill": color})]
    return group(role, cx, cy, size, roof + body)


def shield_check(cx: float, cy: float, size: float, color, *,
                 role: str = "shield") -> Node:
    points = [(cx, cy - size * .42),
              (cx + size * .30, cy - size * .30),
              (cx + size * .30, cy + size * .02),
              (cx, cy + size * .42),
              (cx - size * .30, cy + size * .02),
              (cx - size * .30, cy - size * .30)]
    return group(role, cx, cy, size, [
        Node(kind="path", role="shield-shape",
             props={"points": points, "color": color, "closed": True,
                    "fill": None, **_stroke(size * .045)}),
        Node(kind="path", role="shield-tick",
             props={"points": [(cx - size * .13, cy - size * .01),
                               (cx - size * .03, cy + size * .10),
                               (cx + size * .16, cy - size * .14)],
                    "color": color, "closed": False,
                    **_stroke(size * .055)}),
    ])


def phone(cx: float, cy: float, size: float, color, *,
          role: str = "phone") -> Node:
    w, h = size * .38, size * .66
    return group(role, cx, cy, size, [
        Node(kind="round", role="phone-body",
             props={"x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h,
                    "r": size * .07, "fill": None, "border": color,
                    "border_width": size * .038}),
        Node(kind="round", role="phone-speaker",
             props={"x": cx - w * .14, "y": cy - h * .36,
                    "w": w * .28, "h": size * .018,
                    "r": size * .01, "fill": color}),
        Node(kind="circle", role="phone-button",
             props={"cx": cx, "cy": cy + h * .37, "r": size * .026,
                    "fill": color}),
    ])


def calendar(cx: float, cy: float, size: float, color, *,
             accent=None, role: str = "calendar") -> Node:
    accent = accent or color
    w, h = size * .78, size * .70
    x, y = cx - w / 2, cy - h / 2
    children = [
        Node(kind="round", role="calendar-body",
             props={"x": x, "y": y, "w": w, "h": h, "r": size * .06,
                    "fill": None, "border": color,
                    "border_width": size * .035}),
        Node(kind="round", role="calendar-header",
             props={"x": x, "y": y, "w": w, "h": h * .22, "r": size * .06,
                    "fill": color}),
        Node(kind="round", role="calendar-ring-left",
             props={"x": cx - w * .28, "y": y - size * .035,
                    "w": size * .045, "h": size * .09, "r": size * .02,
                    "fill": accent}),
        Node(kind="round", role="calendar-ring-right",
             props={"x": cx + w * .24, "y": y - size * .035,
                    "w": size * .045, "h": size * .09, "r": size * .02,
                    "fill": accent}),
    ]
    return group(role, cx, cy, size, children)


def clock(cx: float, cy: float, size: float, color, *,
          minute_angle: float = -0.2, role: str = "clock") -> Node:
    radius = size * .40
    children = [Node(kind="ring", role="clock-face",
                     props={"cx": cx, "cy": cy, "r": radius,
                            "width": size * .04, "color": color})]
    for index in range(12):
        angle = index * math.pi / 6
        inner, outer = radius * .80, radius * .90
        children.append(Node(
            kind="line", role=f"clock-tick-{index}",
            props={"x1": cx + inner * math.cos(angle),
                   "y1": cy + inner * math.sin(angle),
                   "x2": cx + outer * math.cos(angle),
                   "y2": cy + outer * math.sin(angle),
                   "color": color, **_stroke(size * .018)}))
    children.extend([
        Node(kind="line", role="clock-hour",
             props={"x1": cx, "y1": cy,
                    "x2": cx + radius * .42 * math.cos(-math.pi / 2 + .5),
                    "y2": cy + radius * .42 * math.sin(-math.pi / 2 + .5),
                    "color": color, **_stroke(size * .045)}),
        Node(kind="line", role="clock-minute",
             props={"x1": cx, "y1": cy,
                    "x2": cx + radius * .62 * math.cos(minute_angle),
                    "y2": cy + radius * .62 * math.sin(minute_angle),
                    "color": color, **_stroke(size * .032)}),
        Node(kind="circle", role="clock-pin",
             props={"cx": cx, "cy": cy, "r": size * .025, "fill": color}),
    ])
    return group(role, cx, cy, size, children)


def eu_stars(cx: float, cy: float, size: float, color, *,
             accent=None, role: str = "eu") -> Node:
    accent = accent or color
    radius = size * .40
    children = [Node(kind="circle", role="eu-disc",
                     props={"cx": cx, "cy": cy, "r": radius, "fill": color})]
    for index in range(12):
        angle = index * math.pi / 6 - math.pi / 2
        children.append(Node(
            kind="circle", role=f"eu-star-{index}",
            props={"cx": cx + radius * .68 * math.cos(angle),
                   "cy": cy + radius * .68 * math.sin(angle),
                   "r": max(1.5, size * .035), "fill": accent}))
    return group(role, cx, cy, size, children)


def heat_waves(cx: float, cy: float, size: float, color, *,
               role: str = "heat") -> Node:
    children = [Node(kind="circle", role="heat-core",
                     props={"cx": cx, "cy": cy, "r": size * .30,
                            "fill": None, "border": color,
                            "border_width": size * .035})]
    for index in range(3):
        points = []
        for step in range(21):
            angle = math.pi * (.28 + .44 * step / 20)
            radius = size * (.10 + .055 * index)
            points.append((cx + radius * math.cos(angle),
                           cy - size * .06 + radius * math.sin(angle)
                           + index * size * .055))
        children.append(Node(
            kind="path", role=f"heat-wave-{index}",
            props={"points": points, "color": color, "closed": False,
                    **_stroke(size * .026)}))
    return group(role, cx, cy, size, children)


def check(cx: float, cy: float, size: float, color, *,
          role: str = "check") -> Node:
    return group(role, cx, cy, size, [
        Node(kind="path", role="check-tick",
             props={"points": [(cx - size * .30, cy + size * .01),
                               (cx - size * .08, cy + size * .22),
                               (cx + size * .32, cy - size * .25)],
                    "color": color, "closed": False,
                    **_stroke(size * .075)}),
    ])


def arrow(cx: float, cy: float, size: float, color, *,
          angle: float = 0.0, role: str = "arrow") -> Node:
    length = size * .42
    tip_x = cx + length * math.cos(angle)
    tip_y = cy + length * math.sin(angle)
    left = angle + math.pi * .78
    right = angle - math.pi * .78
    head = size * .16
    return group(role, cx, cy, size, [
        Node(kind="line", role="arrow-shaft",
             props={"x1": cx - length * math.cos(angle),
                    "y1": cy - length * math.sin(angle),
                    "x2": tip_x, "y2": tip_y,
                    "color": color, **_stroke(size * .038)}),
        Node(kind="path", role="arrow-head",
             props={"points": [
                 (tip_x, tip_y),
                 (tip_x + head * math.cos(left), tip_y + head * math.sin(left)),
                 (tip_x + head * math.cos(right), tip_y + head * math.sin(right))],
                 "color": color, "closed": True, "fill": color,
                 **_stroke(size * .01)}),
    ])
