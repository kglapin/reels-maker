"""Stable non-interactive interface for humans, ChatGPT, Pi and OpenCode."""
import argparse
import json
import shutil
import sys
from pathlib import Path

from . import __version__
from .ffmpeg import RenderError, probe
from .media import preflight
from .paths import AssetError
from .renderer import render
from .spec import ProjectError, load_project

FORMAT_VERSION = 1


def _emit(payload: dict, *, error: bool = False):
    print(json.dumps({"schema_version": FORMAT_VERSION, **payload},
                     ensure_ascii=False, sort_keys=True),
          file=sys.stderr if error else sys.stdout)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="reels-maker",
                                     description="Deterministic 9:16 video rendering CLI")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    for command in ("validate", "render"):
        sub = commands.add_parser(command)
        sub.add_argument("project", help="Path to JSON project manifest")
        sub.add_argument("--root", type=Path, default=Path.cwd(),
                         help="Media root, defaults to current working directory")
        sub.add_argument("--json", action="store_true", help="Machine-readable JSON output")
        if command == "validate":
            sub.add_argument("--syntax-only", action="store_true",
                             help="Validate manifest without probing any media")
        else:
            sub.add_argument("--output", type=Path, help="Override output path")
            sub.add_argument("--cache-dir", type=Path, help="Override persistent scene cache")
            sub.add_argument("--no-cache", action="store_true")

    doctor = commands.add_parser("doctor", help="Check required executable availability")
    doctor.add_argument("--json", action="store_true")
    inspect = commands.add_parser("inspect", help="Read media metadata with ffprobe")
    inspect.add_argument("file", type=Path)
    inspect.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.command == "doctor":
            tools = {name: bool(shutil.which(name)) for name in ("ffmpeg", "ffprobe")}
            result = {"status": "ok" if all(tools.values()) else "missing_tools",
                      "version": __version__, "tools": tools}
            _emit(result)
            return 0 if all(tools.values()) else 3

        if args.command == "inspect":
            result = {"status": "ok", "media": probe(args.file.resolve())}
        else:
            project = load_project(args.project)
            if args.command == "validate":
                if not args.syntax_only:
                    inputs = preflight(project, args.root.resolve())
                    result = {"status": "ok", "name": project.name,
                              "scenes": len(inputs.shots), "duration": project.duration,
                              "media_checked": True}
                else:
                    result = {"status": "ok", "name": project.name,
                              "scenes": len(project.scenes), "duration": project.duration,
                              "media_checked": False}
            else:
                result = render(project, root=args.root, output=args.output,
                                cache_dir=args.cache_dir, use_cache=not args.no_cache)
        _emit(result)
        return 0
    except (ProjectError, AssetError, RenderError, OSError, ValueError) as exc:
        _emit({"status": "error", "type": type(exc).__name__, "message": str(exc)}, error=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
