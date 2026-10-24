"""Minimal .env loader for provider credentials.

The repository root may carry a git-ignored ``.env`` file with one
``NAME=value`` entry per line. Existing process environment variables always
win; values are never logged or reported. This deliberately avoids a third
party dotenv dependency: only simple assignments, ``export`` prefixes,
optional single/double quotes and ``#`` comments are understood.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

_ASSIGNMENT = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _ASSIGNMENT.match(line)
        if not match:
            continue
        name, value = match.group(1), match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values[name] = value
    return values


def load_env(path: Path, *, environ: dict | None = None) -> list[str]:
    """Apply assignments from ``path`` for names not already set.

    Returns the names (never values) that were applied. Missing or unreadable
    files are ignored so the CLI stays usable without a ``.env``.
    """
    target = os.environ if environ is None else environ
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return []
    applied = []
    for name, value in parse_env(text).items():
        if name in target:
            continue
        target[name] = value
        applied.append(name)
    return applied
