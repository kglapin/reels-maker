"""Noninteractive, versioned JSON CLI for ChatGPT, Pi, OpenCode and automation."""
from __future__ import annotations

import argparse
import json
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
            command.add_argument("--strict-quality", action="store_true",
                                 help="Refuse to render when editorial warnings remain")
    kinetic = commands.add_parser("kinetic-render",
        help="Render animated numbers, charts, EU graphics and photo motion from JSON")
    kinetic.add_argument("manifest", type=Path)
    kinetic.add_argument("--root", type=Path)
    kinetic.add_argument("--output", type=Path)
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
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
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
            from .kinetic_video import render_kinetic
            result = render_kinetic(args.manifest, root=args.root, output=args.output)
        elif args.command == "studio-render":
            from .studio import load_studio
            from .renderers.studio import render_studio
            project = load_studio(args.manifest, root=args.root,
                                  profile=args.profile)
            result = render_studio(project, output=args.output,
                                   profile=args.profile,
                                   supersample=args.supersample)
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
                                cache=not args.no_cache, jobs=args.jobs)
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
