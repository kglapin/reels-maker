"""Helpers for deciding whether tests have actual (non-LFS-pointer) media.

CI intentionally checks out code and synthetic fixtures without downloading
client or licensed source footage. Media-dependent suites use these guards and
still run automatically when real local files are available.
"""
from __future__ import annotations

from pathlib import Path

LFS_POINTER = b"version https://git-lfs.github.com/spec/v1"


def has_real_media(path: str | Path) -> bool:
    candidate = Path(path)
    try:
        if not candidate.is_file():
            return False
        with candidate.open("rb") as handle:
            return not handle.read(len(LFS_POINTER)).startswith(LFS_POINTER)
    except OSError:
        return False
