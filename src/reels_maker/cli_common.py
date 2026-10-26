"""Shared output contract for command-line handlers."""
from __future__ import annotations

import json
import sys

SCHEMA_VERSION = 1


def _emit(payload: dict, error: bool = False) -> None:
    print(json.dumps({"schema_version": SCHEMA_VERSION, **payload},
                     ensure_ascii=False), file=sys.stderr if error else sys.stdout)
