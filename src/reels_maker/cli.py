"""Noninteractive, versioned JSON CLI for ChatGPT, Pi, OpenCode and automation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .brand import brand_directory
from .catalog import catalog
from .ffmpeg import RenderError, probe, require_tool
from .paths import ROOT, AssetError
from .renderer import preflight, render
from .spec import ProjectError, load_project

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
        else:
            command.add_argument("--output", type=Path)
            command.add_argument("--cache-dir", type=Path)
            command.add_argument("--no-cache", action="store_true")
            command.add_argument("--jobs", type=int, default=2,
                                 help="Concurrent scene encodes (default: 2)")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("file", type=Path)
    inspect.add_argument("--json", action="store_true")
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
            valid = all(report.values())
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
        elif args.command == "brandbook":
            try:
                from .brandbook import generate_brandbook
            except ImportError as exc:
                raise ProjectError("PDF support requires: pip install -e \".[pdf]\"") from exc
            result = generate_brandbook(args.brand, args.root, args.output)
        elif args.command == "catalog":
            media_root = brand_directory(args.brand, args.root) if args.brand else args.root
            result = catalog(media_root, include_metadata=args.probe, limit=args.limit)
            if args.brand:
                result["brand"] = args.brand
        elif args.command == "inspect":
            result = {"file": str(args.file.resolve()), "metadata": probe(args.file)}
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
                              "media_checked": True}
            else:
                result = render(project, root=args.root, output=args.output,
                                cache_dir=args.cache_dir,
                                cache=not args.no_cache, jobs=args.jobs)
        _emit({"status": "ok", "ok": True, **result})
        return 0
    except (ProjectError, AssetError, RenderError, OSError, ValueError) as exc:
        _emit({"status": "error", "ok": False,
               "error": {"type": type(exc).__name__, "message": str(exc)}}, error=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
