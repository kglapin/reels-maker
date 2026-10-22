"""Stable noninteractive CLI for ChatGPT, Pi, OpenCode and ordinary terminals."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ffmpeg import RenderError, probe
from .paths import ROOT, AssetError
from .renderer import preflight, render
from .spec import ProjectError, load_project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reels-maker",
        description="Render reusable video manifests with cached FFmpeg scenes")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "render"):
        command = commands.add_parser(name)
        command.add_argument("project", type=Path, help="JSON manifest path")
        command.add_argument("--root", type=Path, default=ROOT,
                             help="Asset directory (defaults to repository root)")
        command.add_argument("--json", action="store_true", help="JSON-only stdout")
        if name == "render":
            command.add_argument("--output", type=Path)
            command.add_argument("--cache-dir", type=Path)
            command.add_argument("--no-cache", action="store_true")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("file", type=Path)
    inspect.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = {"ok": True, "file": str(args.file.resolve()),
                      "metadata": probe(args.file)}
        else:
            project = load_project(args.project)
            if args.command == "validate":
                data = preflight(project, args.root)
                result = {"ok": True, "project": project.name,
                          "scenes": len(data["sources"]),
                          "duration": project.duration,
                          "music": bool(data["music"])}
            else:
                result = render(project, root=args.root,
                                output=args.output, cache_dir=args.cache_dir,
                                cache=not args.no_cache)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ProjectError, AssetError, RenderError, OSError, ValueError) as exc:
        error = {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}
        print(json.dumps(error, ensure_ascii=False), file=sys.stdout if args.json else sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
