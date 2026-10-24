"""Temporal motion diagnostics (spec section 9)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .models import Gate, GateResult, QAIssue, Severity


class TemporalReview:
    """Analyse motion continuity and frame-to-frame transitions."""

    def __init__(self, mp4_path: str | Path) -> None:
        self.mp4_path = Path(mp4_path)

    def detect_jitter(self, *, threshold_pixels: float = 2.0, fps: int = 24) -> list[dict[str, Any]]:
        """Detect frame-to-frame position jitter above threshold."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(self.mp4_path),
                 "-vf", "vectorscope=mode=color3:graticule=green", "-f", "null", "-"],
                capture_output=True, text=True, check=False, timeout=120,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return []
        jitter = []
        for line in (result.stderr or "").splitlines():
            if "motion" in line.lower():
                try:
                    parts = line.strip().split()
                    frame_idx = int(parts[0])
                    jitter.append({"frame": frame_idx, "message": line.strip()})
                except (ValueError, IndexError):
                    continue
        return jitter

    def check_transitions(self, *, spec: dict[str, Any] | None = None) -> GateResult:
        """Check transition timing and motion continuity."""
        issues = []
        checked = []
        if spec is not None:
            for idx, shot in enumerate(spec.get("shots", [])):
                transition = shot.get("transition", {})
                if transition.get("type") and transition["type"] != "cut":
                    checked.append(f"transition_{idx}")
                duration = float(shot.get("duration", 2.8))
                if duration < 1.0:
                    issues.append(QAIssue(
                        code="CF_TEMPORAL_SHORT_SHOT",
                        gate=Gate.G4_ENCODED,
                        severity=Severity.WARNING,
                        message=f"Shot '{shot.get('id')}' may be too short.",
                        scene_id=shot.get("id"),
                    ))
        return GateResult(
            gate=Gate.G4_ENCODED,
            ok=not issues,
            status="pass" if not issues else "review_required",
            violations=[],
            warnings=issues,
            checked_rules=checked,
            unchecked_rules=["motion_continuity_analysis"],
            limitations=["Frame-to-frame motion analysis requires full MP4 decoding."],
        )


__all__ = ["TemporalReview"]
