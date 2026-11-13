#!/usr/bin/env python3
"""LLM vision critic for iso prop gallery renders.

The pixel pre-check (tools/iso_prop_critique.py) only sees framing and
blobs — it cannot judge whether a prop looks right. This critic shows
the render to a vision model together with the prop brief and the
gallery rubric, and returns a structured verdict with concrete fixes::

    .venv/bin/python tools/iso_prop_critic_llm.py render.png \\
        --brief "wall inverter with display and DC switch"

The call goes to an OpenAI-compatible chat endpoint with a vision model.
Fix guidance for failed props: docs/iso-prop-playbook.md (read it before
editing geometry — every rule there cost a failed judge round).
Provider presets (pick with --provider)::

    nvidia      free NVIDIA vision models via OpenRouter
                (needs OPENROUTER_API_KEY; OpenCode users already have it in
                ~/.config/opencode/secrets/openrouter.key)
    gemini      Google Gemini vision direct (own free quota, bypasses
                OpenRouter limits; needs GEMINI_API_KEY)
    github-models
                GitHub Models free tier (own quota, vision via
                openai/gpt-4o-mini; token from `gh auth token`)
    nvidia-direct
                NVIDIA NIM trial key direct (no OpenRouter limits; key
                from the Pi agent auth store; vision via
                meta/llama-3.2-11b-vision-instruct)
    pollinations  Pollinations registry (needs a pollen key for vision
                models: POLLINATIONS_API_KEY)

Exit code is 0 on pass, 1 on fail or on tool error.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import urllib.request

PROVIDERS = {
    "nvidia": {
        "api_base": "https://openrouter.ai/api/v1",
        "model": "nvidia/nemotron-3.5-super-vl:free",
        "key_env": "OPENROUTER_API_KEY",
        "key_file": os.path.expanduser(
            "~/.config/opencode/secrets/openrouter.key"),
    },
    "pollinations": {
        "api_base": os.environ.get(
            "POLLINATIONS_API_BASE", "https://text.pollinations.ai"),
        "model": "openai/gpt-5.4-nano",
        "key_env": "POLLINATIONS_API_KEY",
        "key_file": "",
    },
    "gemini": {
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-flash-latest",
        "key_env": "GEMINI_API_KEY",
        "key_file": "",
    },
    "github-models": {
        "api_base": "https://models.github.ai/inference",
        "model": "openai/gpt-4o-mini",
        "key_env": "GITHUB_TOKEN",
        "key_file": "",
        "key_cmd": ("gh", "auth", "token"),
    },
    "nvidia-direct": {
        "api_base": "https://integrate.api.nvidia.com/v1",
        "model": "nvidia/nemotron-3.5-super-vl-120b-a12b",
        "key_env": "NVIDIA_API_KEY",
        "key_file": "",
        "key_json": {"file": "~/.pi/agent/auth.json",
                     "path": ["nvidia", "key"]},
    },
    "nvidia-diffusion": {
        "api_base": "https://integrate.api.nvidia.com/v1",
        "model": "google/diffusiongemma-26b-a4b-it",
        "no_json_mode": True,
        "key_env": "NVIDIA_API_KEY",
        "key_file": "",
        "key_json": {"file": "~/.pi/agent/auth.json",
                     "path": ["nvidia", "key"]},
    },
}

RUBRIC = """You are the art director reviewing an isometric product illustration
(flat-shaded vector style, dark green studio backdrop) for a client promo
about home energy devices. Judge ONLY what you see in the image.

Checklist (fail the render if any point is clearly violated):
1. FRAMING: subject fully visible and centered, fills the frame sensibly,
   nothing important cropped by the image edges.
2. ATTACHMENT: every part touches its parent (mounts, pipes, cables meet
   surfaces); nothing floats in mid-air; no part pierces through another
   in a way that reads as a glitch (separate stacked volumes are fine).
3. VISIBLE FACES: details live on camera-facing surfaces; backs stay clean;
   no mirrored or garbled text anywhere.
4. GLASS/REFLECTIONS: any shine sits strictly inside its glass or metal
   panel, never spilling over edges; subtle, never a gray bar artifact.
5. REALISM: proportions of a real device; functional parts read correctly
   (fasteners, vents, switches, cables that start AND end somewhere
   plausible, grounding shadows); consistent light (lit faces vs shade);
   no large dead-flat areas, no confusing extra limbs.
6. STYLE: clean flat-shaded isometric illustration, muted industrial
   palette (dark greens, light steel, small amber/red accents). No photo
   noise, no cartoon outlines, no clutter that does not serve the device.

7. AESTHETICS (judge like an art director, not a QA script):
   - TYPOGRAPHY: one clear focal headline per frame; size steps between
     title, body and captions are obvious; nothing competes with the
     headline; generous line spacing, no wall-of-text.
   - WHITESPACE & BALANCE: air around the subject and the copy; optical
     center holds the hero; no corner feels abandoned, none overstuffed.
   - COLOR HARMONY: one dominant hue family, one secondary, one accent;
     the accent (amber/mint) marks only the single most important thing
     per frame; no two elements shout at once.
   - FOCAL CLARITY: within 2 seconds you know where to look first,
     second, third. If the eye wanders without a path, fail it.
   - MOTION READINESS (stills): every element sits where its entrance
     animation can land it; nothing is framed so tight that motion
     would clip it; leader lines and pills leave room to breathe.
   When style reference images are attached, they set the craft bar:
   match their finish (edge treatment, shading depth, restraint) and
   fail anything visibly cruder — but never copy their content.

Output contract (machine-enforced): your ENTIRE reply must be ONE JSON
object, no prose before or after, no markdown fences, no analysis text.
Any reasoning stays silent. The JSON shape:
{"verdict": "pass" or "fail",
 "score": 1-10 overall craft,
 "issues": [{"severity": "major" or "minor", "area": "where in frame",
             "what": "what is wrong", "fix": "concrete fix suggestion"}],
 "aesthetic_notes": ["one line per aesthetics dimension you scored low"],
 "summary": "one sentence"}"""


def _provider_key(provider: str) -> str:
    name = PROVIDERS[provider]["key_env"]
    if os.environ.get(name):
        return os.environ[name]
    path = PROVIDERS[provider]["key_file"]
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            return handle.read().strip()
    cmd = PROVIDERS[provider].get("key_cmd") or ()
    if cmd:
        import subprocess as _sp
        try:
            out = _sp.run(cmd, capture_output=True, text=True,
                          timeout=15)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except Exception:
            pass
    spec = PROVIDERS[provider].get("key_json") or {}
    if spec:
        try:
            with open(os.path.expanduser(spec["file"]),
                      encoding="utf-8") as handle:
                node = json.load(handle)
            for part in spec.get("path", []):
                node = node[part]
            if isinstance(node, str) and node.strip():
                return node.strip()
        except Exception:
            pass
    return ""


DEFAULT_STYLE_REFS = (
    "renders/asta-energy/prop-galeria/13-pompa-ciepla.png",
    "renders/asta-energy/prop-galeria/14-kotlownia.png",
)


def _thumb_url(path: str, size: int, quality: int) -> str | None:
    from PIL import Image

    try:
        with Image.open(path) as im:
            frame = im.convert("RGB")
            frame.thumbnail((size, size))
            buffer = io.BytesIO()
            frame.save(buffer, format="JPEG", quality=quality)
    except Exception:
        return None
    return ("data:image/jpeg;base64,"
            + base64.b64encode(buffer.getvalue()).decode("ascii"))


def critique(image_path: str, brief: str, provider: str = "nvidia",
             model: str = "", api_base: str = "",
             style_refs: list[str] | None = None) -> dict:
    """Send one render to the vision critic; return the parsed verdict."""
    import re as _re  # noqa: E402
    _missing = _re.compile(
        r"render is missing|not provided|no image|only .*reference"
        r"|cannot see|blank image|image not available|not available"
        r" for visual", _re.IGNORECASE)
    cfg = PROVIDERS[provider]
    model = model or cfg["model"]
    api_base = api_base or cfg["api_base"]
    data_url = _thumb_url(image_path, 640, 62)
    if data_url is None:
        raise ValueError(f"cannot read render: {image_path}")

    def _content(with_refs: bool) -> list:
        items: list = [
            {"type": "text", "text": (
                "Prop brief: " + brief + "\n"
                "Review this gallery render against the checklist. "
                "Be strict but fair: flag only defects a client would "
                "notice. If it is clean, return verdict pass with "
                "empty issues.")},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
        refs = (style_refs if style_refs is not None
                else list(DEFAULT_STYLE_REFS))
        if with_refs:
            for num, ref in enumerate(refs[:2], 1):
                ref_url = _thumb_url(ref, 320, 55)
                if ref_url is None:
                    continue
                items.insert(-1, {"type": "text", "text": (
                    f"Style reference {num} (approved house work: "
                    "match its finish and restraint, never its "
                    "content):")})
                items.insert(-1, {"type": "image_url",
                                  "image_url": {"url": ref_url}})
        return items

    content = _content(True)
    body: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": RUBRIC},
            {"role": "user", "content": content},
        ],
        "max_tokens": 4000,
        "temperature": 0.2,
    }
    if not cfg.get("no_json_mode"):
        body["response_format"] = {"type": "json_object"}
    else:
        content[0]["text"] += ("\nReturn ONLY one JSON object with keys "
                               "verdict, score, issues, summary.")
    endpoint = (api_base.rstrip("/")
                + ("/openai" if provider == "pollinations"
                   else "/chat/completions"))
    key = _provider_key(provider)
    def _post(payload_body: dict):
        req = urllib.request.Request(
            endpoint, data=json.dumps(payload_body).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "HTTP-Referer": "reels-maker-gallery"})
        if key:
            req.add_header("Authorization", f"Bearer {key}")
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req,
                                             timeout=180) as response:
                    ans = json.load(response)
                message = ans["choices"][0]["message"]
                text = message.get("content") or ""
                start, end = text.find("{"), text.rfind("}")
                if start < 0 or end <= start:
                    raise ValueError(
                        f"Critic returned no JSON: {text[:300]}")
                return json.loads(text[start:end + 1])
            except Exception as exc:  # noqa: BLE001 - retried below
                last_error = exc
                import time as _time
                _time.sleep(5 * (attempt + 1))
        raise ValueError(f"Critic failed 3 times: {last_error}")

    rep = _post(body)
    if (rep.get("verdict") == "fail"
            and _missing.search(json.dumps(rep, ensure_ascii=False))):
        # Multi-image payload glitch on some routes (direct 2026-11-12:
        # judge sees only the style refs, never the target). One
        # target-only retry before accepting the verdict.
        content = _content(False)
        body["messages"][1]["content"] = content
        if cfg.get("no_json_mode"):
            content[0]["text"] += ("\nReturn ONLY one JSON object with "
                                   "keys verdict, score, issues, summary.")
        rep = _post(body)
    return rep


def merge_verdicts(image: str, reports: list[tuple[str, dict]]) -> dict:
    """Pure merge for the judge ensemble: fail-closed.

    The prop passes only when EVERY judge returns verdict pass.
    A judge error (network, limits, bad JSON) fails the ensemble too,
    so a silent judge can never green-light a broken render.
    """
    merged: dict = {"image": image, "judges": {}, "issues": []}
    worst = 10
    failed_by: list[str] = []
    for provider, report in reports:
        merged["judges"][provider] = report
        if report.get("verdict") != "pass":
            failed_by.append(provider)
        try:
            worst = min(worst, int(report.get("score", 10)))
        except (TypeError, ValueError):
            worst = min(worst, 0)
        for issue in report.get("issues", []) or []:
            item = dict(issue)
            item["judge"] = provider
            merged["issues"].append(item)
    merged["score"] = worst if reports else 0
    if failed_by:
        merged["verdict"] = "fail"
        merged["summary"] = ("Failed by judge(s): " + ", ".join(failed_by)
                             + ".")
    else:
        merged["verdict"] = "pass"
        merged["summary"] = ("All %d judges passed." % len(reports))
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="gallery render PNG to review")
    parser.add_argument("--brief", required=True,
                        help="what the prop should be")
    parser.add_argument("--provider", default="nvidia",
                        choices=sorted(PROVIDERS),
                        help="which registry serves the vision model")
    parser.add_argument("--ensemble", default="",
                        help=("comma-separated extra providers for a second "
                              "opinion, e.g. --ensemble nvidia-direct. "
                              "Pass requires EVERY judge to pass."))
    parser.add_argument("--model", default="",
                        help="override the provider default vision model")
    parser.add_argument("--api-base", default="",
                        help="override the provider endpoint")
    parser.add_argument("--style-ref", action="append", default=None,
                        help=("approved render to set the craft bar "
                              "(repeatable, max 2 used); defaults to two "
                              "in-repo approved gallery frames"))
    parser.add_argument("--no-style-ref", action="store_true",
                        help="judge without style references")
    args = parser.parse_args()
    providers = [args.provider] + [p.strip() for p in args.ensemble.split(",")
                                   if p.strip()] if args.ensemble else [args.provider]
    for extra in providers[1:]:
        if extra not in PROVIDERS:
            print(json.dumps({"verdict": "error",
                              "summary": f"unknown provider: {extra}"},
                             ensure_ascii=False, indent=1))
            return 1
    refs = [] if args.no_style_ref else args.style_ref
    reports: list[tuple[str, dict]] = []
    for provider in providers:
        try:
            reports.append((provider, critique(
                args.image, args.brief, provider=provider,
                model=args.model if provider == args.provider else "",
                api_base=args.api_base if provider == args.provider else "",
                style_refs=refs)))
        except Exception as exc:  # noqa: BLE001 - CLI must report, not crash
            reports.append((provider, {"verdict": "error",
                                       "summary": str(exc)[:300]}))
    report = (merge_verdicts(args.image, reports) if len(reports) > 1
              else reports[0][1])
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report.get("verdict") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
