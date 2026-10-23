"""Repository-root and Unicode-safe media resolution."""
from pathlib import Path
import unicodedata

ROOT = Path(__file__).resolve().parents[2]

class AssetError(ValueError):
    pass


def resolve_asset(name: str, root: Path = ROOT) -> Path:
    """Resolve a project-relative asset, tolerating macOS decomposed accents.

    Reject absolute paths and attempts to escape the repository.
    Returns an NFC-normalized path so callers receive a stable, canonical
    representation regardless of the underlying filesystem's storage form.
    """
    if not isinstance(name, str) or not name.strip():
        raise AssetError("Asset path must be a nonempty string")
    candidate = Path(name)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise AssetError(f"Asset path must be repository-relative: {name!r}")
    base = Path(root).resolve()
    cursor = base
    for component in candidate.parts:
        if component in (".", ""):
            continue
        exact = cursor / component
        if exact.exists():
            cursor = exact
            continue
        canonical = unicodedata.normalize("NFC", component)
        if not cursor.is_dir():
            raise AssetError(f"Missing directory for asset: {name}")
        matches = [p for p in cursor.iterdir()
                   if unicodedata.normalize("NFC", p.name) == canonical]
        if len(matches) != 1:
            raise AssetError(f"Asset not found or ambiguous: {name}")
        cursor = matches[0]
    if not cursor.resolve().is_relative_to(base):
        raise AssetError(f"Asset escapes project directory: {name}")
    if not cursor.is_file():
        raise AssetError(f"Asset is not a file: {name}")
    # git-lfs pointers are text placeholders, not playable media.
    if cursor.suffix.lower() in {".webm", ".mp4", ".mov", ".mp3", ".wav"}:
        with cursor.open("rb") as handle:
            if handle.read(64).startswith(b"version https://git-lfs.github.com/spec/v1"):
                raise AssetError(f"Git LFS content missing; run git lfs pull: {name}")
    # Normalize returned path to NFC so callers receive a canonical form
    # independent of whether the filesystem stored components in NFD (macOS).
    return Path(unicodedata.normalize("NFC", str(cursor)))
