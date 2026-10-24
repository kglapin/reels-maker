"""Approved positive patterns catalog (spec section 10)."""
from __future__ import annotations

from typing import Any

from .models import ApprovedPattern
from .store import CreativeMemoryStore


class PatternLibrary:
    """In-memory or store-backed catalog of approved positive patterns."""

    def __init__(self, store: CreativeMemoryStore | None = None) -> None:
        self._store = store
        self._cache: dict[str, list[ApprovedPattern]] = {}

    def add(self, pattern: ApprovedPattern) -> str:
        if self._store is not None:
            self._store.add_pattern(pattern)
        if pattern.context not in self._cache:
            self._cache[pattern.context] = []
        self._cache[pattern.context].append(pattern)
        return pattern.pattern_id

    def get(self, context: str | None = None) -> list[ApprovedPattern]:
        if self._store is not None:
            return self._store.get_patterns(context=context)
        if context:
            return list(self._cache.get(context, []))
        all_patterns: list[ApprovedPattern] = []
        for patterns in self._cache.values():
            all_patterns.extend(patterns)
        return all_patterns

    def recommend(
        self,
        context: str,
        *,
        exclude_ids: set[str] | None = None,
    ) -> ApprovedPattern | None:
        """Recommend an approved pattern for context, avoiding recent repeats."""
        exclude_ids = exclude_ids or set()
        candidates = self.get(context)
        rated = [p for p in candidates if p.human_rating is not None
                 and p.pattern_id not in exclude_ids]
        if not rated:
            rated = [p for p in candidates if p.pattern_id not in exclude_ids]
        if not rated:
            return None
        return max(rated, key=lambda p: p.human_rating or 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "patterns": [p.to_dict() for p in self.get()],
        }


__all__ = ["PatternLibrary"]