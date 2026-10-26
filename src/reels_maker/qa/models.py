"""Stable issue record shared by QA checks and report serializers."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Issue:
    code: str
    severity: str
    message: str
    scene: int | None = None
    time: float | None = None
    elements: list[str] = field(default_factory=list)
    suggestion: str = ""
    frame: int | None = None

    def to_dict(self) -> dict:
        return {
            "code": self.code, "severity": self.severity,
            "message": self.message, "scene": self.scene,
            "time": self.time, "elements": list(self.elements),
            "suggestion": self.suggestion, "frame": self.frame,
        }
