"""Noninteractive, versioned JSON CLI for ChatGPT, Pi, OpenCode and automation."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from .brand import brand_directory
from .asset_reviews import load_media_reviews
from .catalog import catalog
from .ffmpeg import RenderError, probe, require_tool
from .paths import ROOT, AssetError
from .renderer import preflight, render
from .spec import ProjectError, load_project
from .quality import review_project

SCHEMA_VERSION = 1


def _emit(payload: dict, error: bool = False) -> None:
    print(json.dumps({"schema_version": SCHEMA_VERSION, **payload},
                     ensure_ascii=False), file=sys.stderr if error else sys.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reels-maker",
        description="Render manifest-driven videos in project-defined formats")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "render"):
        command = commands.add_parser(name)
        command.add_argument("project", type=Path, help="JSON manifest path")
        command.add_argument("--root", type=Path, default=ROOT, help="Asset root")
        command.add_argument("--json", action="store_true", help="Versioned JSON output")
        if name == "validate":
            command.add_argument("--syntax-only", action="store_true",
                                 help="Validate JSON schema without media or FFmpeg")
            command.add_argument("--strict-quality", action="store_true",
                                 help="Return error when editorial warnings are detected")
        else:
            command.add_argument("--output", type=Path)
            command.add_argument("--cache-dir", type=Path)
            command.add_argument("--no-cache", action="store_true")
            command.add_argument("--jobs", type=int, default=2,
                                 help="Concurrent scene encodes (default: 2)")
            command.add_argument("--title-engine", choices=("legacy", "studio"),
                                 default="legacy",
                                 help="Render title overlays with legacy cards or the shared studio scene graph")
            command.add_argument("--strict-quality", action="store_true",
                                 help="Refuse to render when editorial warnings remain")
    kinetic = commands.add_parser("kinetic-render",
        help="Render animated numbers, charts, EU graphics and photo motion from JSON")
    kinetic.add_argument("manifest", type=Path)
    kinetic.add_argument("--root", type=Path)
    kinetic.add_argument("--output", type=Path)
    kinetic.add_argument("--engine", choices=("legacy", "studio"),
                         default="legacy",
                         help="Use shared studio primitives (legacy Cairo remains default)")
    kinetic.add_argument("--json", action="store_true")

    studio = commands.add_parser(
        "studio-render",
        help="Render a complete motion-design film with the shared scene engine")
    studio.add_argument("manifest", type=Path)
    studio.add_argument("--root", type=Path)
    studio.add_argument("--output", type=Path)
    studio.add_argument("--profile", choices=("preview", "review", "final",
                                              "high-motion"))
    studio.add_argument("--supersample", type=int, choices=(1, 2))
    studio.add_argument("--cache-dir", type=Path,
                        help="Opt-in per-scene segment cache directory")
    studio.add_argument("--json", action="store_true")

    studio_qa = commands.add_parser(
        "studio-qa",
        help="Audit collisions, safe areas, typography, contrast, timing and data")
    studio_qa.add_argument("manifest", type=Path)
    studio_qa.add_argument("--root", type=Path)
    studio_qa.add_argument("--profile", choices=("preview", "review", "final",
                                                 "high-motion"))
    studio_qa.add_argument("--samples", type=int, default=6,
                           help="Geometry samples per scene (default: 6)")
    studio_qa.add_argument("--output-dir", type=Path)
    studio_qa.add_argument("--no-contact-sheet", action="store_true")
    studio_qa.add_argument("--strict", action="store_true",
                           help="Return exit code 2 when any error is reported")
    studio_qa.add_argument("--json", action="store_true")

    studio_info = commands.add_parser(
        "studio-inspect",
        help="Print resolved tokens, layouts, choreography and cue timings")
    studio_info.add_argument("manifest", type=Path)
    studio_info.add_argument("--root", type=Path)
    studio_info.add_argument("--profile", choices=("preview", "review", "final",
                                                   "high-motion"))
    studio_info.add_argument("--json", action="store_true")
    cues = commands.add_parser("cue-sheet",
        help="List exact local/global cue times including transition overlaps")
    cues.add_argument("project", type=Path)
    cues.add_argument("--output", type=Path, help="Optional JSON report destination")
    cues.add_argument("--json", action="store_true")

    audio_qc = commands.add_parser("audio-qc",
        help="Measure integrated LUFS and true peak without modifying the audio")
    audio_qc.add_argument("file", type=Path)
    audio_qc.add_argument("--reference-lufs", type=float,
                          help="Optional editorial loudness reference, not a platform standard")
    audio_qc.add_argument("--json", action="store_true")

    inspect = commands.add_parser("inspect")
    inspect.add_argument("file", type=Path)
    inspect.add_argument("--json", action="store_true")
    verify = commands.add_parser("verify",
        help="Reject incorrect exported MP4 dimensions, frames, codecs or audio")
    verify.add_argument("project", type=Path)
    verify.add_argument("--video", type=Path, required=True)
    verify.add_argument("--json", action="store_true")
    storyboard = commands.add_parser("storyboard",
        help="Extract a contact sheet from real MP4 scene frames for visual QC")
    storyboard.add_argument("project", type=Path)
    storyboard.add_argument("--video", type=Path, required=True)
    storyboard.add_argument("--output", type=Path, required=True)
    storyboard.add_argument("--columns", type=int, default=4)
    storyboard.add_argument("--root", type=Path)
    storyboard.add_argument("--profile", choices=("preview", "review", "final",
                                                    "high-motion"))
    storyboard.add_argument("--motion-strip", action="store_true",
        help="Show entry/settled/exit frames for every shot")
    storyboard.add_argument("--json", action="store_true")
    discover = commands.add_parser("catalog")
    discover.add_argument("--root", type=Path, default=ROOT)
    discover.add_argument("--brand", help="Limit media catalog to a brand slug")
    discover.add_argument("--probe", action="store_true",
                          help="Inspect each available media file (slower)")
    discover.add_argument("--limit", type=int, default=500)
    discover.add_argument("--json", action="store_true")
    site = commands.add_parser("brand-scan",
        help="Create CSS/font/logo proposal and brandbook PDF from a public website")
    site.add_argument("url", help="Public HTTP(S) website address")
    site.add_argument("--brand", required=True, help="Brand slug")
    site.add_argument("--root", type=Path, default=ROOT)
    site.add_argument("--output", type=Path, help="JSON audit destination")
    site.add_argument("--no-logo-download", action="store_true")
    site.add_argument("--no-pdf", action="store_true")
    site.add_argument("--json", action="store_true")

    brandbook = commands.add_parser("brandbook")
    brandbook.add_argument("--brand", required=True)
    brandbook.add_argument("--root", type=Path, default=ROOT)
    brandbook.add_argument("--output", type=Path)
    brandbook.add_argument("--json", action="store_true")
    plan = commands.add_parser("plan",
        help="Convert a reviewed brief into an explainable studio manifest draft; "
             "VALIDATE WITH studio-qa (studio manifests are file-optional)")
    plan.add_argument("brief", type=Path, help="Brief JSON path")
    plan.add_argument("--root", type=Path, default=ROOT,
                      help="Repository root containing brands/")
    plan.add_argument("--brand", help="Brand slug; overrides brief['brand']")
    plan.add_argument("--write-manifest", action="store_true",
                      help="Save the manifest into brands/<slug>/projects/")
    plan.add_argument("--force", action="store_true",
                      help="Overwrite an existing draft manifest")
    plan.add_argument("--json", action="store_true")
    library = commands.add_parser("library",
        help="Validate a reviewed asset-library manifest (license metadata is "
             "mandatory)")
    library.add_argument("manifest", type=Path, help="asset-library.json path")
    library.add_argument("--json", action="store_true")
    brand_init = commands.add_parser("brand-init",
        help="Scaffold a new brand directory with placeholder identity "
             "(no media, no invented content)")
    brand_init.add_argument("slug", help="lowercase brand slug")
    brand_init.add_argument("--name", required=True, help="Readable brand name")
    brand_init.add_argument("--accent", required=True,
                            help="Verified brand accent colour, #RRGGBB")
    brand_init.add_argument("--root", type=Path, default=ROOT,
                            help="Repository root containing brands/")
    brand_init.add_argument("--force", action="store_true",
                            help="Replace an existing brand directory")
    brand_init.add_argument("--json", action="store_true")
    pixabay = commands.add_parser("pixabay",
        help="Search Pixabay music/sound-effects; download only explicitly "
             "picked candidates into the brand imports/ quarantine area")
    pixabay.add_argument("query", help="Search words or a pixabay.com URL")
    pixabay.add_argument("--kind", choices=("music", "sound-effects"),
                         default="music")
    pixabay.add_argument("--root", type=Path, default=ROOT,
                         help="Repository root containing brands/")
    pixabay.add_argument("--brand", help="Brand slug for imports/ staging")
    pixabay.add_argument("--page-file", type=Path,
                         help="Parse a page saved from the browser instead of "
                              "fetching (needed when Cloudflare blocks us)")
    pixabay.add_argument("--tracks-file", type=Path,
                         help="Plain text file with cdn.pixabay.com MP3 urls "
                              "(one per line, from the browser network tab); "
                              "always works because the CDN is not blocked")
    pixabay.add_argument("--cookies", help="Cookie header, e.g. "
                                           "'cf_clearance=...; ...'")
    pixabay.add_argument("--limit", type=int, default=10,
                         help="Candidates to list before picking")
    pixabay.add_argument("--pick", help="Comma-separated candidate numbers to "
                                        "download, e.g. --pick 2,3")
    pixabay.add_argument("--all", action="store_true",
                         help="Download every listed candidate")
    pixabay.add_argument("--json", action="store_true")
    media_search = commands.add_parser(
        "media-search",
        help="Search public stock-media APIs and save ranked, unapproved candidates")
    media_search.add_argument("query", help="Search terms")
    media_search.add_argument("--provider", choices=("all", "pexels", "pixabay",
        "unsplash", "wikimedia_commons", "openverse"), default="all")
    media_search.add_argument("--kind", choices=("image", "video"), default="image")
    media_search.add_argument("--limit", type=int, default=12,
                              help="Candidates requested from each provider (1..50)")
    media_search.add_argument("--aspect", type=float, default=9/16,
                              help="Target width/height used for ranking")
    media_search.add_argument("--output", type=Path,
                              help="Optional candidate report JSON path")
    media_search.add_argument("--json", action="store_true")
    media_download = commands.add_parser(
        "media-download",
        help="Download one exact-item reviewed candidate into brand imports quarantine")
    media_download.add_argument("candidate_file", type=Path,
                                help="Candidate record or media-search report JSON")
    media_download.add_argument("--provider", required=True,
        choices=("pexels", "pixabay", "unsplash", "wikimedia_commons", "openverse"))
    media_download.add_argument("--asset-id", required=True,
                                help="Exact provider asset ID from search result")
    media_download.add_argument("--rights-decision", type=Path, required=True,
                                help="Human-reviewed exact-item rights decision JSON")
    media_download.add_argument("--brand", required=True)
    media_download.add_argument("--root", type=Path, default=ROOT)
    media_download.add_argument("--target-platform", required=True)
    media_download.add_argument("--transcode", choices=("h264_mp4",))
    media_download.add_argument("--json", action="store_true")
    sfx = commands.add_parser(
        "sfx-generate",
        help="Generate deterministic procedural SFX into imports/audio quarantine")
    sfx.add_argument("--brand", required=True, help="Existing brand slug")
    sfx.add_argument("--root", type=Path, default=ROOT,
                     help="Repository root containing brands/")
    sfx.add_argument("--kind", choices=("click", "whoosh", "riser", "hit"),
                     required=True)
    sfx.add_argument("--duration", type=float, default=0.45,
                     help="Duration in seconds (0.03..3.0)")
    sfx.add_argument("--sample-rate", type=int, choices=(22050, 44100, 48000),
                     default=48000)
    sfx.add_argument("--seed", type=int, default=0)
    sfx.add_argument("--peak", type=float, default=0.20,
                     help="Linear peak amplitude (0.01..0.50)")
    sfx.add_argument("--json", action="store_true")
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")
    creative_caps = commands.add_parser(
        "creative-capabilities", help="Versioned capability registry for LLM callers")
    creative_caps.add_argument("--json", action="store_true")
    creative_schema = commands.add_parser(
        "creative-schema", help="Export JSON Schema for LLM structured outputs")
    creative_schema.add_argument("--json", action="store_true")

    creative_val = commands.add_parser(
        "creative-validate", help="Validate Creative Spec v1 and perform asset/geometry QA")
    creative_val.add_argument("spec", type=Path)
    creative_val.add_argument("--root", type=Path)
    creative_val.add_argument("--semantic-only", action="store_true")
    creative_val.add_argument("--json", action="store_true")

    creative_compile = commands.add_parser(
        "creative-compile", help="Compile LLM-authored Creative Spec to executable Studio JSON")
    creative_compile.add_argument("spec", type=Path)
    creative_compile.add_argument("--root", type=Path)
    creative_compile.add_argument("--output", type=Path)
    creative_compile.add_argument("--force", action="store_true")
    creative_compile.add_argument("--strict", action="store_true",
                                  help="Reject warnings in addition to errors")
    creative_compile.add_argument("--json", action="store_true")

    creative_edit = commands.add_parser(
        "creative-edit", help="Apply JSON Patch edits to a Creative Spec without overwriting original")
    creative_edit.add_argument("spec", type=Path)
    creative_edit.add_argument("patch", type=Path)
    creative_edit.add_argument("--output", type=Path, required=True)
    creative_edit.add_argument("--force", action="store_true")
    creative_edit.add_argument("--json", action="store_true")

    creative_render = commands.add_parser(
        "creative-render", help="Compile, preflight and render Creative Spec via actual Studio engine")
    creative_render.add_argument("spec", type=Path)
    creative_render.add_argument("--root", type=Path)
    creative_render.add_argument("--output", type=Path, required=True)
    creative_render.add_argument("--storyboard", type=Path)
    creative_render.add_argument("--strict", action="store_true")
    creative_render.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command in ("creative-capabilities", "creative-schema", "creative-validate",
                            "creative-compile", "creative-edit", "creative-render"):
            import tempfile
            from .creative.registry import capabilities
            from .creative.spec import validate_creative_spec
            from .creative.compiler import compile_creative_spec
            from .creative.quality import audit_creative_spec
            from .creative.edit import edit_creative_spec
            if args.command=="creative-capabilities":
                result=capabilities()
            elif args.command=="creative-schema":
                from .creative.schema import creative_json_schema
                result={"json_schema":creative_json_schema()}
            else:
                spec=json.loads(args.spec.read_text(encoding="utf-8"))
                if args.command=="creative-edit":
                    patches=json.loads(args.patch.read_text(encoding="utf-8"))
                    revised,changes=edit_creative_spec(spec,patches)
                    destination=args.output.resolve()
                    if destination==args.spec.resolve():
                        raise ProjectError("creative-edit must write a new versioned file")
                    if not spec.get("brand") and destination.parent!=args.spec.parent.resolve():
                        raise ProjectError(
                            "Unbranded Creative Spec revisions must stay beside source assets")
                    if destination.exists() and not args.force:
                        raise ProjectError(f"Output exists: {destination} (use --force)")
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    destination.write_text(
                        json.dumps(revised,ensure_ascii=False,indent=2)+"\n",
                        encoding="utf-8")
                    result={"spec":str(destination),"changes":changes}
                elif args.command=="creative-validate" and args.semantic_only:
                    result={"validation":validate_creative_spec(spec),
                            "assets_checked":False}
                else:
                    manifest,plan=compile_creative_spec(
                        spec,source_dir=args.spec.parent,root=args.root,
                        check_assets=True)
                    qa=audit_creative_spec(spec,manifest,
                        source_dir=args.spec.parent,root=args.root)
                    if not qa["ok"] or (getattr(args,"strict",False)
                                         and qa["warnings"]):
                        _emit({"status":"error","ok":False,"qa":qa,"plan":plan,
                               "error":{"type":"CreativeQualityError",
                                        "message":"Creative Spec has unresolved QA issues"}},
                              error=True)
                        return 2
                    if args.command=="creative-validate":
                        result={"validation":validate_creative_spec(spec),
                                "qa":qa,"plan":plan,"assets_checked":True}
                    elif args.command=="creative-compile":
                        destination=(args.output or args.spec.with_suffix(".studio.json")).resolve()
                        if destination==args.spec.resolve():
                            raise ProjectError("Compiler output must not overwrite Creative Spec")
                        if not spec.get("brand") and destination.parent!=args.spec.parent.resolve():
                            raise ProjectError(
                                "Unbranded Studio manifests must stay beside source assets")
                        if destination.exists() and not args.force:
                            raise ProjectError(f"Output exists: {destination} (use --force)")
                        report_path=destination.with_suffix(".creative-report.json")
                        if report_path.exists() and not args.force:
                            raise ProjectError(f"Report exists: {report_path} (use --force)")
                        destination.parent.mkdir(parents=True,exist_ok=True)
                        destination.write_text(
                            json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",
                            encoding="utf-8")
                        report_path.write_text(
                            json.dumps({"plan":plan,"qa":qa},ensure_ascii=False,indent=2)+"\n",
                            encoding="utf-8")
                        result={"manifest":str(destination),"report":str(report_path),
                                "plan":plan,"qa":qa}
                    else:
                        from .studio import load_studio
                        from .renderers.studio import render_studio
                        from .storyboard import make_studio_storyboard
                        # Keep temporary manifest beside spec, because the Studio
                        # asset resolver intentionally scopes local assets to it.
                        with tempfile.NamedTemporaryFile(
                                mode="w",suffix=".json",prefix=".creative-studio-",
                                dir=args.spec.parent,delete=False,encoding="utf-8") as tmp:
                            path=Path(tmp.name)
                            tmp.write(json.dumps(manifest,ensure_ascii=False)+"\n")
                        try:
                            project=load_studio(path,root=args.root)
                            rendered=render_studio(project,output=args.output,supersample=1)
                            sheet=None
                            if args.storyboard:
                                sheet=make_studio_storyboard(
                                    project,Path(rendered["output"]),
                                    args.storyboard,columns=4,motion_strip=True)
                            result={"render":rendered,"plan":plan,"qa":qa,
                                    "storyboard":sheet}
                        finally:
                            path.unlink(missing_ok=True)
            _emit({"status":"ok","ok":True,**result})
            return 0
        if args.command == "doctor":
            import subprocess
            report = {}
            for name in ("ffmpeg", "ffprobe"):
                try:
                    exe = require_tool(name)
                    report[name] = subprocess.run(
                        [exe, "-version"], capture_output=True, text=True,
                        check=True).stdout.splitlines()[0]
                except (OSError, RenderError, subprocess.CalledProcessError):
                    report[name] = None
            import PIL
            report["pillow"] = PIL.__version__
            valid = all(report.get(name) for name in ("ffmpeg", "ffprobe"))
            _emit({"status": "ok" if valid else "error",
                   "ok": valid, "tools": report}, error=not valid)
            return 0 if valid else 3
        if args.command == "brand-scan":
            try:
                from .brand_scan import analyze_site, download_logo_candidates, suggested_brand
                from .brandbook import make_brandbook
            except ImportError as exc:
                raise ProjectError(
                    'Website brand scan requires: pip install -e ".[brand]"'
                ) from exc
            brand_dir = brand_directory(args.brand, args.root)
            imports = brand_dir / "imports"
            imports.mkdir(parents=True, exist_ok=True)
            audit = analyze_site(args.url)
            if not args.no_logo_download:
                audit["downloaded_logos"] = download_logo_candidates(
                    audit, imports / "assets")
            audit["suggested_brand"] = suggested_brand(audit, args.brand)
            report = (args.output or imports / "website-report.json").resolve()
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
            pdf = None
            if not args.no_pdf:
                pdf = make_brandbook(
                    audit, Path(args.root).resolve() / "renders" /
                    args.brand / "brandbook-proposal.pdf", draft=True)
            result = {
                "brand": args.brand, "source_url": audit["source_url"],
                "report": str(report), "brandbook_pdf": str(pdf) if pdf else None,
                "palette": audit["palette"],
                "font": audit["typography"]["primary"],
                "logo_candidates": len(audit["logos"]),
                "downloaded_logos": audit.get("downloaded_logos", []),
                "warnings": audit["warnings"], "applied": False,
            }
        elif args.command == "kinetic-render":
            if args.engine == "studio":
                from .studio import load_kinetic_studio
                from .renderers.studio import render_studio
                project, default_output = load_kinetic_studio(
                    args.manifest, root=args.root)
                result = render_studio(
                    project, output=args.output or default_output)
                result["engine"] = "studio"
            else:
                from .kinetic_video import render_kinetic
                result = render_kinetic(args.manifest, root=args.root,
                                        output=args.output)
        elif args.command == "studio-render":
            from .studio import load_studio
            from .renderers.studio import render_studio
            project = load_studio(args.manifest, root=args.root,
                                  profile=args.profile)
            result = render_studio(project, output=args.output,
                                   profile=args.profile,
                                   supersample=args.supersample,
                                   cache_dir=args.cache_dir)
        elif args.command == "studio-inspect":
            from .studio import load_studio
            project = load_studio(args.manifest, root=args.root,
                                  profile=args.profile)
            timeline = project.timeline()
            result = {**project.to_dict(),
                      "timeline": timeline.to_dict(),
                      "scenes": [scene.to_dict()
                                 for scene in project.build(timeline)]}
        elif args.command == "studio-qa":
            from .studio import load_studio
            from .renderers.scene import RenderOptions, SceneRenderer
            from .qa.report import audit, contact_sheet, write_report
            project = load_studio(args.manifest, root=args.root,
                                  profile=args.profile)
            timeline = project.timeline()
            built = project.build(timeline)
            renderer = SceneRenderer(project.width, project.height,
                                     project.tokens, project.fonts,
                                     options=RenderOptions(supersample=1))
            report = audit(project, built, timeline, renderer=renderer,
                           samples_per_scene=args.samples,
                           strict=args.strict)
            out_dir = (args.output_dir or (project.root / "renders" /
                       (project.brand or "studio") / "qa" /
                       project.name)).resolve()
            written = write_report(report, out_dir)
            sheet = None
            if not args.no_contact_sheet:
                sheet = contact_sheet(report, built, renderer, timeline,
                                      out_dir / "qa-contact-sheet.png")
            result = {"project": project.name, "report": written["report"],
                      "contact_sheet": str(sheet) if sheet else None,
                      "qa": report}
            if args.strict and not report["ok"]:
                _emit({"status": "error", "ok": False, **result,
                       "error": {"type": "QualityReviewRequired",
                                 "message": "studio-qa reported blocking errors"}},
                      error=True)
                return 2
        elif args.command == "plan":
            from .planning import PlanningError, plan_brief
            try:
                brief = json.loads(args.brief.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ProjectError(
                    f"Cannot read brief {args.brief}: {exc}") from exc
            manifest, report = plan_brief(brief, root=args.root,
                                          brand=args.brand)
            result = {"status": "ok", "manifest": manifest, "report": report}
            if args.write_manifest:
                brand = manifest["brand"]
                projects = brand_directory(brand, args.root) / "projects"
                projects.mkdir(parents=True, exist_ok=True)
                destination = projects / f"{manifest['name']}.json"
                if destination.exists() and not args.force:
                    raise ProjectError(
                        f"Draft manifest already exists: {destination} "
                        "(use --force to replace it)")
                destination.write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
                report_path = projects / f"{manifest['name']}.plan-report.json"
                report_path.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
                result["manifest_path"] = str(destination)
                result["report_path"] = str(report_path)
        elif args.command == "brandbook":
            try:
                from .brandbook import generate_brandbook
            except ImportError as exc:
                raise ProjectError("PDF support requires: pip install -e \".[pdf]\"") from exc
            result = generate_brandbook(args.brand, args.root, args.output)
        elif args.command == "catalog":
            media_root = brand_directory(args.brand, args.root) if args.brand else args.root
            reviews = (load_media_reviews(args.brand, args.root)
                       if args.brand else None)
            result = catalog(media_root, include_metadata=args.probe,
                             limit=args.limit, reviewed_assets=reviews)
            if args.brand:
                result["brand"] = args.brand
        elif args.command == "cue-sheet":
            from .cue_sheet import make_cue_sheet
            result = make_cue_sheet(load_project(args.project))
            if args.output is not None:
                location = args.output.resolve()
                location.parent.mkdir(parents=True, exist_ok=True)
                location.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
                result["report"] = str(location)
        elif args.command == "audio-qc":
            from .audio_qc import analyze_audio_loudness
            result = analyze_audio_loudness(
                args.file, reference_lufs=args.reference_lufs)
        elif args.command == "inspect":
            result = {"file": str(args.file.resolve()), "metadata": probe(args.file)}
        elif args.command == "verify":
            from .export_quality import verify_export
            result = verify_export(load_project(args.project), args.video)
        elif args.command == "storyboard":
            from .storyboard import make_storyboard, make_studio_storyboard
            manifest = json.loads(args.project.read_text(encoding="utf-8"))
            is_studio = bool(manifest.get("style")) or any(
                isinstance(scene, dict) and "composition" in scene
                for scene in manifest.get("scenes", []))
            if is_studio:
                from .studio import load_studio
                project = load_studio(args.project, root=args.root,
                                      profile=args.profile)
                result = make_studio_storyboard(
                    project, args.video, args.output, columns=args.columns,
                    motion_strip=args.motion_strip)
            else:
                result = make_storyboard(load_project(args.project), args.video,
                                         args.output, columns=args.columns,
                                         motion_strip=args.motion_strip)
        elif args.command == "library":
            from .library import check_library
            result = {"library": check_library(args.manifest)}
        elif args.command == "brand-init":
            from .brand import init_brand
            result = {"brand_init": init_brand(
                args.slug, name=args.name, accent=args.accent,
                root=args.root, force=args.force)}
        elif args.command == "pixabay":
            from .pixabay import (fetch_search_page, download_candidates,
                                  parse_tracks, parse_track_list,
                                  search_page_url)
            if args.tracks_file:
                try:
                    source = args.tracks_file.read_text(encoding="utf-8")
                except OSError as exc:
                    raise ProjectError(
                        f"Cannot read track list {args.tracks_file}: {exc}"
                    ) from exc
                tracks = parse_track_list(source)
            elif args.page_file:
                try:
                    source = args.page_file.read_text(encoding="utf-8")
                except OSError as exc:
                    raise ProjectError(
                        f"Cannot read saved page {args.page_file}: {exc}"
                    ) from exc
                tracks = parse_tracks(source, "")[:max(1, args.limit)]
            else:
                source = fetch_search_page(args.query, args.kind,
                                           cookies=args.cookies)
                tracks = parse_tracks(
                    source, search_page_url(args.query, args.kind)
                )[:max(1, args.limit)]
            result = {"query": args.query, "candidates": tracks}
            if args.all and not args.pick:
                args.pick = ",".join(str(i) for i in range(1, len(tracks) + 1))
            if args.pick:
                if not args.brand:
                    raise ProjectError(
                        "Downloading requires --brand (quarantine staging "
                        "lives in brands/<slug>/imports/audio/)")
                destination = brand_directory(args.brand, args.root) / \
                    "imports" / "audio"
                report = download_candidates(tracks, destination, args.pick,
                                             kind=args.kind,
                                             cookies=args.cookies)
                result["download"] = report
        elif args.command == "media-search":
            from .assets.stock_acquisition import candidate_record, search_with_fallback
            from .assets.stock_media import (
                search_openverse, search_pexels, search_pexels_videos,
                search_pixabay, search_pixabay_videos, search_unsplash,
                search_wikimedia_commons,
            )
            if not 1 <= args.limit <= 50:
                raise ValueError("--limit must be between 1 and 50")
            if not isinstance(args.query, str) or not args.query.strip():
                raise ValueError("Search query must contain non-whitespace text")
            if not math.isfinite(args.aspect) or args.aspect <= 0:
                raise ValueError("--aspect must be a finite positive number")
            if args.provider == "all":
                providers = (("pexels", "pixabay") if args.kind == "video" else
                             ("pexels", "pixabay", "unsplash",
                              "wikimedia_commons", "openverse"))
            else:
                providers = (args.provider,)
                if args.kind == "video" and args.provider not in ("pexels", "pixabay"):
                    raise ValueError(
                        "Video search is currently supported only by Pexels/Pixabay")
            orientation = ("landscape" if args.aspect > 1.2 else
                           "portrait" if args.aspect < 0.85 else "square")
            provider_limits = {"unsplash": 30, "openverse": 20}
            searches = []
            for provider in providers:
                per_page = min(args.limit, provider_limits.get(provider, 50))
                if provider == "pexels":
                    fn = (lambda query, limit=per_page, orientation=orientation:
                          search_pexels_videos(query, per_page=limit,
                                               orientation=orientation)
                          if args.kind == "video" else
                          search_pexels(query, per_page=limit))
                elif provider == "pixabay":
                    fn = (lambda query, limit=per_page:
                          search_pixabay_videos(query, per_page=limit)
                          if args.kind == "video" else
                          search_pixabay(query, per_page=limit))
                elif provider == "unsplash":
                    fn = lambda query, limit=per_page: search_unsplash(query, per_page=limit)
                elif provider == "wikimedia_commons":
                    fn = lambda query, limit=per_page: search_wikimedia_commons(query, per_page=limit)
                else:
                    fn = lambda query, limit=per_page: search_openverse(query, per_page=limit)
                fn.__name__ = provider
                searches.append(fn)
            candidates, outcomes = search_with_fallback(
                args.query, searches, aspect=args.aspect)
            records = [candidate_record(asset) for asset in candidates]
            successes = sum(item["status"] == "ok" for item in outcomes)
            search_status = ("unavailable" if successes == 0 else
                             "partial" if successes < len(outcomes) else "ok")
            result = {"query": args.query, "kind": args.kind,
                      "target_aspect": args.aspect, "providers": outcomes,
                      "candidate_count": len(records), "candidates": records,
                      "search_status": search_status,
                      "rights_status": "unknown",
                      "note": "Search results are candidates, not licensed or approved assets."}
            if args.output is not None:
                location = args.output.expanduser().resolve()
                location.parent.mkdir(parents=True, exist_ok=True)
                location.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
                result["report"] = str(location)
        elif args.command == "media-download":
            from .assets.stock_acquisition import candidate_asset, download_cleared_asset
            from .assets.stock_media import apply_reviewed_rights_decision
            try:
                candidate_doc = json.loads(args.candidate_file.read_text(encoding="utf-8"))
                decision = json.loads(args.rights_decision.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ProjectError(f"Cannot read candidate or rights decision JSON: {exc}") from exc
            records = (candidate_doc.get("candidates") if isinstance(candidate_doc, dict)
                       and isinstance(candidate_doc.get("candidates"), list)
                       else [candidate_doc])
            matches = [record for record in records
                       if isinstance(record, dict)
                       and record.get("provider") == args.provider
                       and str(record.get("asset_id")) == args.asset_id]
            if len(matches) != 1:
                raise ProjectError("Candidate file must contain exactly one matching provider/asset ID")
            asset = candidate_asset(matches[0])
            asset = apply_reviewed_rights_decision(asset, decision)
            report = download_cleared_asset(
                asset, brand=args.brand, root=args.root,
                target_platform=args.target_platform,
                transcode_format=args.transcode)
            result = {"download": report,
                      "note": "Downloaded files remain unapproved in brands/<slug>/imports/."}
        elif args.command == "sfx-generate":
            from .audio_synthesis import SFXSpec, write_procedural_sfx
            result = {"audio": write_procedural_sfx(
                SFXSpec(args.kind, args.duration, args.sample_rate, args.seed, args.peak),
                brand=args.brand, root=args.root)}
        else:
            project = load_project(args.project)
            if args.command == "validate":
                if args.syntax_only:
                    result = {"project": project.name, "scenes": len(project.scenes),
                              "duration": project.duration, "media_checked": False}
                else:
                    data = preflight(project, args.root)
                    result = {"project": project.name, "scenes": len(data["sources"]),
                              "duration": project.duration, "music": bool(data["music"]),
                              "voiceover": bool(data["voiceover"]),
                              "media_checked": True}
            else:
                if args.strict_quality:
                    check = review_project(project, root=args.root)
                    if check["warning_count"]:
                        _emit({"status": "error", "ok": False,
                               "quality": check,
                               "error": {"type": "QualityReviewRequired",
                                         "message": "Resolve design warnings before rendering"}},
                              error=True)
                        return 2
                result = render(project, root=args.root, output=args.output,
                                cache_dir=args.cache_dir,
                                cache=not args.no_cache, jobs=args.jobs,
                                title_engine=args.title_engine)
        if args.command == "validate":
            quality = review_project(project, root=args.root)
            result["quality"] = quality
            if args.strict_quality and quality["warning_count"]:
                _emit({"status": "error", "ok": False, **result,
                       "error": {"type": "QualityReviewRequired",
                                 "message": "Editorial warnings require review"}},
                      error=True)
                return 2
        _emit({"status": "ok", "ok": True, **result})
        return 0
    except (ProjectError, AssetError, RenderError, OSError, ValueError) as exc:
        _emit({"status": "error", "ok": False,
               "error": {"type": type(exc).__name__, "message": str(exc)}}, error=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
