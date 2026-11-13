"""Carbon v10 motion curves applied to actual Studio appearance tracks.

Source constants are separated from authored film adaptations. Opt-in only.
"""
from __future__ import annotations
import math
from dataclasses import replace

SOURCE = "https://v10.carbondesignsystem.com/guidelines/motion/overview/"
CHOREOGRAPHY_SOURCE = "https://v10.carbondesignsystem.com/guidelines/motion/choreography/"
CURVES = {
    "productive": {"standard": (.2, 0., .38, .9),
                   "entrance": (0., 0., .38, .9), "exit": (.2, 0., 1., .9)},
    "expressive": {"standard": (.4, .14, .3, 1.),
                   "entrance": (0., 0., .3, 1.), "exit": (.4, .14, 1., 1.)},
}
DURATION_MS = {"fast-01": 70, "fast-02": 110, "moderate-01": 150,
               "moderate-02": 240, "slow-01": 400, "slow-02": 700}
APPEARANCE = frozenset({"opacity", "dx", "dy", "scale", "reveal", "rotation",
                        "prop.tracking_offset"})


def curve_params(mode="productive", phase="standard"):
    if not isinstance(mode, str) or not isinstance(phase, str) or mode not in CURVES or phase not in ("standard", "entrance", "exit"):
        raise ValueError("Choose productive/expressive and standard/entrance/exit")
    return tuple(zip(("x1", "y1", "x2", "y2"), CURVES[mode][phase]))


def duration_seconds(token, fps, film_scale=1.0):
    if not isinstance(token, str) or token not in DURATION_MS:
        raise ValueError("Unknown Carbon duration token")
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError("FPS must be an integer in 1..120")
    if (isinstance(film_scale, bool) or not isinstance(film_scale, (int, float))
            or not math.isfinite(film_scale) or not .25 <= film_scale <= 4):
        raise ValueError("film_scale must be finite in .25..4")
    return max(1, math.ceil(DURATION_MS[token] / 1000 * film_scale * fps)) / fps


def _profile(config):
    if not isinstance(config, dict) or set(config) - {"mode", "roles", "minimum_hold"}:
        raise ValueError("carbon_motion accepts mode, roles, minimum_hold only")
    mode = config.get("mode", "productive")
    curve_params(mode)
    hold = config.get("minimum_hold", .8)
    if (isinstance(hold, bool) or not isinstance(hold, (int, float))
            or not math.isfinite(hold) or not 0 <= hold <= 30):
        raise ValueError("minimum_hold must be finite in 0..30")
    roles = config.get("roles", {})
    if not isinstance(roles, dict):
        raise ValueError("roles must be an object")
    for role, item in roles.items():
        if not isinstance(role, str) or not role or not isinstance(item, dict):
            raise ValueError("Each role requires a nonempty name and object")
        if set(item) - {"mode", "phase", "duration_token", "film_scale"}:
            raise ValueError("Unknown role motion option")
        curve_params(item.get("mode", mode), item.get("phase", "standard"))
        if "film_scale" in item and "duration_token" not in item:
            raise ValueError("film_scale requires duration_token")
        if "duration_token" in item:
            duration_seconds(item["duration_token"], 30, item.get("film_scale", 1.0))
    return mode, roles, float(hold)


def _phase(prop, keys):
    if prop == "opacity":
        return "entrance" if keys[-1].value > keys[0].value else "exit"
    neutral = {"dx": 0, "dy": 0, "scale": 1, "reveal": 1,
               "rotation": 0, "prop.tracking_offset": 0}
    return "entrance" if keys[-1].value == neutral[prop] else "standard"


def apply_carbon_motion(built, config, *, duration, fps):
    """Atomically restyle simple appearance tracks in the existing scene graph.

    Data/progress/counter tracks and complex multi-key choreography are kept.
    No external model, renderer or global easing registration is introduced.
    """
    mode, roles, hold = _profile(config)
    if (isinstance(duration, bool) or not isinstance(duration, (int, float))
            or not math.isfinite(duration) or duration <= 0):
        raise ValueError("Scene duration must be positive and finite")
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError("FPS must be an integer in 1..120")
    nodes = []
    seen = set()
    for root in built.nodes:
        for node in root.flatten():
            if id(node) not in seen:
                seen.add(id(node)); nodes.append(node)
    if set(roles) - {node.role for node in nodes}:
        raise ValueError("Carbon role selection contains missing node roles")
    changes, applied, skipped = [], [], []
    for node in nodes:
        if roles and node.role not in roles:
            continue
        options = roles.get(node.role, {})
        for prop, track in node.tracks.items():
            keys = track.keys
            if prop not in APPEARANCE or len(keys) != 2 or keys[0].value == keys[-1].value:
                skipped.append({"role": node.role, "property": prop,
                                "reason": "data, static, or complex track preserved"})
                continue
            if keys[-1].time <= keys[0].time:
                raise ValueError("Carbon requires a positive track interval")
            chosen_mode = options.get("mode", mode)
            phase = options.get("phase", _phase(prop, keys))
            params = curve_params(chosen_mode, phase)
            end = keys[-1].time
            if "duration_token" in options:
                end = keys[0].time + duration_seconds(
                    options["duration_token"], fps, options.get("film_scale", 1.0))
                if end > duration + 1e-9 or (phase != "exit" and duration - end < hold - 1e-9):
                    raise ValueError("Carbon duration would exceed scene or consume reading hold")
                if phase == "exit" and keys[0].time < hold - 1e-9:
                    raise ValueError("Carbon exit would start before minimum hold")
            new_keys = [replace(keys[0], easing="cubic-bezier", params=params),
                        replace(keys[-1], time=end, easing="cubic-bezier", params=params)]
            updated = type(track)(new_keys, clamp_before=track.clamp_before,
                                  clamp_after=track.clamp_after)
            changes.append((node, prop, updated))
            applied.append({"role": node.role, "property": prop, "mode": chosen_mode,
                            "phase": phase, "params": dict(params),
                            "start": keys[0].time, "end": end})
    for node, prop, track in changes:
        node.tracks[prop] = track
    built.meta["carbon_motion"] = {"source": SOURCE, "status": "experimental",
                                    "applied": applied, "skipped": skipped,
                                    "visual_approval": None}
    return built


def compile_carbon_spec(spec, *, source_dir=".", root=None, expressive_shots=()):
    """Use the existing craft compiler and emit opt-in Carbon Studio scenes."""
    from ..creative.professional_direction import compile_professional_spec
    accents = set(expressive_shots)
    if accents - {shot["id"] for shot in spec.get("shots", [])}:
        raise ValueError("Unknown expressive shot ID")
    manifest, report = compile_professional_spec(spec, source_dir=source_dir, root=root)
    if spec.get("mode", "studio") != "studio":
        raise ValueError("Carbon integration currently supports Studio only")
    for scene in manifest["scenes"]:
        scene["carbon_motion"] = {"mode": "expressive" if scene["id"] in accents else "productive"}
    report["carbon_motion"] = {"source": SOURCE, "status": "experimental",
                                "expressive_shots": sorted(accents),
                                "timing": "existing timings preserved unless role token explicitly requested",
                                "visual_approval": None}
    return manifest, report


def main(argv=None):
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description="Compile opt-in Carbon motion into Studio")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--expressive-shot", action="append", default=[])
    parser.add_argument("--allow-warnings", action="store_true")
    args = parser.parse_args(argv)
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        manifest, report = compile_carbon_spec(spec, source_dir=args.spec.parent,
                                              root=args.root, expressive_shots=args.expressive_shot)
        if not report["qa"]["ok"] or (report["qa"]["warnings"] and not args.allow_warnings):
            print(json.dumps({"status": "review_required", "report": report}, ensure_ascii=False))
            return 2
        out = args.output.resolve(); log = out.with_suffix(".carbon-report.json")
        if out == args.spec.resolve() or log == args.spec.resolve() or out.exists() or log.exists():
            raise ValueError("Choose new output paths; input and existing files are protected")
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        with log.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"status": "compiled_for_review", "manifest": str(out),
                          "report": str(log), "visual_approval": None}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
