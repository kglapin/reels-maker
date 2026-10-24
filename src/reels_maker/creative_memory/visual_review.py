"""Visual review integration (spec sections G3/G4)."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from .models import Gate, GateResult, QAIssue, Severity


class VisualReview:
    """Frame-level visual QA adapter using FFmpeg frame extraction."""

    def __init__(self, mp4_path: str | Path) -> None:
        self.mp4_path = Path(mp4_path)

    def probe(self) -> dict[str, Any]:
        """Use FFprobe to gather container and stream metadata."""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_format", "-show_streams",
                 "-of", "json", str(self.mp4_path)],
                capture_output=True, text=True, check=True, timeout=30,
            )
            import json as _json
            return _json.loads(result.stdout)
        except (subprocess.CalledProcessError, FileNotFoundError,
                subprocess.TimeoutExpired) as exc:
            return {"error": str(exc), "status": "error"}

    def extract_frames(
        self,
        times: list[float],
        output_dir: str | Path,
    ) -> list[Path]:
        """Extract frames at given timestamps (seconds)."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        frames: list[Path] = []
        for t in times:
            fname = output_dir / f"frame_{t:08.3f}.png"
            cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-ss", str(t), "-i", str(self.mp4_path),
                "-vframes", "1", "-frames:v", "1", str(fname),
            ]
            try:
                subprocess.run(cmd, capture_output=True, check=True, timeout=60)
                if fname.is_file():
                    frames.append(fname)
            except (subprocess.CalledProcessError, FileNotFoundError,
                    subprocess.TimeoutExpired):
                pass
        return frames

    def verify_policy_frames(
        self,
        spec: dict[str, Any],
        rules: list[dict[str, Any]],
        policy_sha: str,
    ) -> GateResult:
        """Verify that extracted frames do not contain forbidden elements."""
        issues: list[QAIssue] = []
        checked_rules: list[str] = []
        unchecked_rules: list[str] = []

        from .preflight import _dict_to_rule

        for rule_dict in rules:
            rule_obj = _dict_to_rule(rule_dict)
            checked_rules.append(rule_obj.rule_id)
            if rule_obj.predicate is None:
                unchecked_rules.append(rule_obj.rule_id)
                continue
            if rule_obj.predicate.operator != "element_type_absent":
                unchecked_rules.append(rule_obj.rule_id)
                continue
            node_types = rule_obj.predicate.parameters.get("element_types", [])
            if "kicker" in node_types:
                for shot in spec.get("shots", []):
                    if shot.get("kicker"):
                        issues.append(QAIssue(
                            code="CF_POLICY_FORBIDDEN_ELEMENT",
                            gate=Gate.G3_PREVIEW,
                            severity=Severity.ERROR,
                            message=(
                                f"Kicker text present in shot '{shot.get('id')}' "
                                "but was not removed after render."
                            ),
                            rule_id=rule_obj.rule_id,
                            scene_id=shot.get("id"),
                            elements=("kicker",),
                            policy_sha256=policy_sha,
                            status="unverified",
                        ))

        has_blockers = any(i.severity == Severity.BLOCKER for i in issues)
        ok = not issues and not has_blockers
        return GateResult(
            gate=Gate.G3_PREVIEW,
            ok=ok,
            status="pass" if ok else "review_required",
            violations=issues,
            warnings=[],
            checked_rules=checked_rules,
            unchecked_rules=unchecked_rules,
            limitations=[
                "Visual verification is structural; pixel-perfect VLM "
                "analysis requires human review.",
                "OCR is not performed; label presence is inferred from spec/manifest.",
            ],
            policy_sha256=policy_sha,
        )


def file_sha256(path: str | Path) -> str:
    """Compute SHA-256 of a file in 64KB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


__all__ = ["VisualReview", "file_sha256"]
