"""Scene builders for the custom family."""
from __future__ import annotations

from .base import BuiltScene, SceneContext, resolve_text_style
from .scene_support import (
    _background, _decor, _finish, _headline, _measure, _spec, _subtitle,
    _text_elements, _theme,
)



def _build_stack(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    has_visual = bool(scene.get("photo"))
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        align="center", balance=True)
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    measurements = {
        "headline": _measure(_headline(scene), headline_style, width, ctx),
        "body": _measure(_subtitle(scene), body_style, width, ctx)}
    layout = ctx.layout.layout("stack-center", measurements,
                               has_visual=has_visual)
    elements = _text_elements(ctx, scene, layout, theme, align="center")
    specs = [_spec("kicker", 3), _spec("headline", 9, "display"),
             _spec("body", 4)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "stack"})


def _build_full_bleed(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "display", theme["ink"],
                                        align="center", balance=True,
                                        line_height=.94)
    body_style = resolve_text_style(ctx.tokens, "subtitle", theme["muted"],
                                    align="center")
    measurements = {
        "headline": _measure(_headline(scene), headline_style, width, ctx),
        "body": _measure(_subtitle(scene), body_style, width, ctx)}
    layout = ctx.layout.layout("full-bleed-type", measurements)
    elements = _text_elements(ctx, scene, layout, theme, align="center",
                              headline_role="display")
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, [_spec("kicker", 3),
                              _spec("headline", 10, "display"),
                              _spec("body", 4)],
                   decor=_decor(ctx, scene, theme),
                   meta={"component": "full-bleed"})


def _build_split(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        balance=True)
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    line_height=1.34)
    layout = ctx.layout.layout("split-editorial", {
        "headline": _measure(_headline(scene), headline_style, width, ctx),
        "body": _measure(_subtitle(scene), body_style, width, ctx)},
        has_visual=True)
    elements = _text_elements(ctx, scene, layout, theme, align="left")
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, [_spec("kicker", 3),
                              _spec("headline", 9, "display"),
                              _spec("body", 5)],
                   decor=_decor(ctx, scene, theme),
                   meta={"component": "split"})
