"""Noninteractive, versioned JSON CLI for ChatGPT, Pi, OpenCode and automation."""
from __future__ import annotations

import argparse
from pathlib import Path

from .cli_common import SCHEMA_VERSION, _emit
from .cli_parser import build_parser
from .cli_commands import handle_commands
from .cli_creative import handle_creative
from .cli_doctor import handle_doctor
from .envfile import load_env
from .ffmpeg import RenderError
from .paths import ROOT, AssetError
from .spec import ProjectError


def main(argv: list[str] | None = None) -> int:
    load_env(ROOT / ".env")
    args = build_parser().parse_args(argv)
    try:
        if args.command in ("creative-capabilities", "creative-schema",
                            "creative-validate", "creative-compile",
                            "creative-edit", "creative-render"):
            return handle_creative(args)
        if args.command == "doctor":
            return handle_doctor(args)
        return handle_commands(args)
    except (ProjectError, AssetError, RenderError, OSError, ValueError) as exc:
        _emit({"status": "error", "ok": False,
               "error": {"type": type(exc).__name__, "message": str(exc)}},
              error=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
