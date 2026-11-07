"""Batch-generate one Studio manifest per realization (>=4 photos).

Mirrors the human-reviewed rusko-66-test scheme: badge hook with photo,
photo showcase beats, white end card with red CTA panel. Copy uses only
verified index fields (title/location/description); nothing is invented.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "brands/matuszyk-radajak/references/realizacje-index.json"
OUTDIR = ROOT / "brands/matuszyk-radajak/projects/auto"

MUSIC = "imports/audio/bombinsound-happy-advertising-hip-hop-magic-moments.mp3"
WHOOSH = "imports/audio/procedural_whoosh_222fd24bbe829ced0195.wav"
BADGE = "imports/logo/logo-badge-white.png"

HOOK_DUR = 3.0
MID_DUR = 3.5
CTA_DUR = 7.0
MAX_MID = 4


def first_sentence(text, limit=80):
    # Fail closed: a subtitle either fits whole or is dropped entirely.
    # Never ship a mid-sentence cut with an ellipsis on a title card.
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    sent = parts[0] if parts else ""
    return sent if 0 < len(sent) <= limit else ""


def parse_facts(desc):
    """Extract verified insulation facts; None when the text gives none."""
    t = re.sub(r"\s+", " ", (desc or "").lower()).strip()
    tech = None
    if "zamkni" in t:
        tech = "ZAMKNIĘTOKOMÓRKOWA"
    elif "otwarto" in t:
        tech = "OTWARTOKOMÓRKOWA"
    elif "celuloz" in t:
        tech = "WEŁNA CELULOZOWA"
    elif re.search(r"pur\b", t) or "poliuretan" in t \
            or re.search(r"pian[kaąęoiuy]", t):
        tech = "PIANA PUR"
    thick = None
    m = re.search(r"grubo[śs][cć][^\d]{0,30}?(\d+(?:[.,]\d+)?)\s*cm", t)
    if not m:
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*cm\s+pian\w*", t)
    if m:
        thick = m.group(1).replace(",", ".") + " cm"
    area = None
    m2 = re.search(r"(\d+(?:[.,]\d+)?)\s*m\s*(?:2|²|kw)", t)
    if m2:
        area = m2.group(1).replace(",", ".") + " m²"
    return tech, thick, area


def even_indices(n, k):
    if n <= k:
        return list(range(n))
    return sorted({round(i * (n - 1) / (k - 1)) for i in range(k)})


def build_manifest(r):
    folder = r["local_folder"]  # imports/photos/realizacje/<id>-<slug>
    photos = [f for f in r["local_images"]]
    loc = (r.get("location") or "").strip()
    loc_up = loc.upper() if loc else "REALIZACJA"
    title_up = (r.get("title") or "REALIZACJA").strip().upper()
    sub = first_sentence(r.get("description", "")).upper()

    scenes = [
        {
            "id": "hook",
            "composition": "statement",
            "duration": HOOK_DUR,
            "photo": photos[0],
            "background": {
                "scrim": 0.62,
                "tint": "#303030",
                "tint_amount": 0.2,
                "camera": {"direction": "push-in", "intensity": 0.05},
            },
            "editorial_media": [
                {"asset": BADGE, "x": 0.24, "y": 0.10, "w": 0.52, "h": 0.135}
            ],
            "kicker": loc_up,
            "headline": title_up,
            "subtitle": sub,
        }
    ]
    tech, thick, area = parse_facts(r.get("description", ""))
    facts = []
    if tech:
        facts.append(("TECHNOLOGIA", tech))
    if thick:
        facts.append(("GRUBOŚĆ", thick))
    if area:
        facts.append(("POWIERZCHNIA", area))
    tape = photos[1:]
    picks = even_indices(len(tape), min(MAX_MID, len(tape)))
    for i, pos in enumerate(picks):
        scene = {
            "id": f"foto-{pos + 1}",
            "composition": "spotlight",
            "duration": MID_DUR,
            "photo": tape[pos],
            "background": {
                "scrim": 0.55,
                "tint": "#303030",
                "tint_amount": 0.15,
                "camera": {"direction": "push-in", "intensity": 0.06},
            },
        }
        if i < len(facts):
            scene["kicker"], scene["headline"] = facts[i]
        else:
            scene["kicker"] = loc_up
        scenes.append(scene)
    scenes.append(
        {
            "id": "cta",
            "composition": "cta",
            "duration": CTA_DUR,
            "background": {"kind": "solid", "color": "#FFFFFF"},
            "headline": "Masz pytania?",
            "phone": "505 012 600",
            "line_one": "BEZPŁATNA WYCENA",
            "line_two": "",
            "website": "",
            "editorial_media": [
                {"asset": BADGE, "x": 0.19, "y": 0.60, "w": 0.62, "h": 0.162}
            ],
        }
    )

    cuts = []
    t = 0.0
    for s in scenes[:-1]:
        t += s["duration"]
        cuts.append(round(t - 0.3, 2))
    slug = folder.rsplit("/", 1)[-1]
    return slug, {
        "schema_version": 1,
        "name": slug,
        "brand": "matuszyk-radajak",
        "style": "editorial-premium",
        "video": {"width": 1080, "height": 1920, "fps": 30},
        "export": {"profile": "final", "codec": "libx264", "crf": 18,
                   "preset": "veryfast"},
        "design_overrides": {
            "palette": {
                "background": "#303030",
                "surface": "#FFFFFF",
                "ink": "#FFFFFF",
                "muted": "#E9E9E9",
                "accent": "#D41217",
            }
        },
        "audio": {
            "music": {"file": MUSIC, "volume": 0.4},
            "sfx": [
                {"file": WHOOSH, "time": c, "gain_db": -10.0} for c in cuts
            ],
        },
        "scenes": scenes,
    }


OVERRIDES = ROOT / "brands/matuszyk-radajak/projects/auto-overrides.json"
BUILD_REPORT = ROOT / \
    "brands/matuszyk-radajak/references/batch-build-report.json"


def load_overrides():
    if not OVERRIDES.exists():
        return {}
    data = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def collect_warnings(slug, r, manifest):
    """Flag copy/layout risks a human must eyeball before publishing."""
    warnings = []
    hook = manifest["scenes"][0]
    headline = hook.get("headline", "")
    for word in headline.replace("\n", " ").split():
        if len(word.strip("-")) > 11:
            warnings.append({
                "code": "long_word",
                "detail": f"hook word {word!r} may breach the safe zone",
            })
            break
    if not hook.get("subtitle"):
        desc = (r.get("description") or "").strip()
        if desc:
            warnings.append({
                "code": "dropped_subtitle",
                "detail": "first sentence over 80 chars; hook has no subtitle",
            })
    tech, thick, area = parse_facts(r.get("description", ""))
    if not (tech or thick or area):
        warnings.append({
            "code": "no_facts",
            "detail": "no technology/thickness/area parsed; middle slides "
                      "are photo-only beats",
        })
    if not (r.get("location") or "").strip():
        warnings.append({
            "code": "no_location",
            "detail": "no location on file; used generic labels",
        })
    return [{"slug": slug, **w} for w in warnings]


def main():
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    overrides = load_overrides()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    made, warnings = [], []
    for r in idx:
        if len(r["images_full"]) < 4:
            continue
        slug, manifest = build_manifest(r)
        for scene_id, fields in overrides.get(slug, {}).items():
            for scene in manifest["scenes"]:
                if scene.get("id") == scene_id:
                    scene.update(fields)
        (OUTDIR / f"{slug}.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        made.append(slug)
        warnings.extend(collect_warnings(slug, r, manifest))
    BUILD_REPORT.write_text(
        json.dumps({"manifests": len(made), "warnings": warnings},
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"manifests: {len(made)} -> {OUTDIR}")
    print(f"warnings: {len(warnings)} -> {BUILD_REPORT}")
    print("\n".join(made[:5]), "..." if len(made) > 5 else "")


if __name__ == "__main__":
    main()
