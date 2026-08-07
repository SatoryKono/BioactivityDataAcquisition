"""Normalize cross-validation comparison-source payloads."""

from __future__ import annotations


def comparison_source_list(comparison_sources: object) -> list[str]:
    """Return only supported source-name strings from one serialized value."""
    if isinstance(comparison_sources, str):
        return [comparison_sources]
    if isinstance(comparison_sources, list):
        return [item for item in comparison_sources if isinstance(item, str)]
    return []
