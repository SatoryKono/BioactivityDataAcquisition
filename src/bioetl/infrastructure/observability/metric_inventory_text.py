"""Shared inventory helpers with a single runtime owner."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from bioetl.infrastructure.observability.metric_inventory_shared import (
    _RUNTIME_CANDIDATE_TEXT_CACHE,
    _RUNTIME_EVENT_SCAN_MARKERS,
    _RUNTIME_SCAN_MARKERS,
    _SOURCE_TEXT_CACHE,
)

REGISTERED_PROMETHEUS_METRIC_LABELS: dict[str, frozenset[str]] = {}


def _normalize_mapping_lists(
    mapping: dict[str, list[str]] | defaultdict[str, list[str]],
) -> dict[str, list[str]]:
    """Return a mapping with deterministically sorted unique list values."""
    return {key: sorted(set(values)) for key, values in sorted(mapping.items())}


def _read_cached_text(path: Path) -> str | None:
    cache_key = path.as_posix()
    cached = _SOURCE_TEXT_CACHE.get(cache_key)
    if cache_key in _SOURCE_TEXT_CACHE:
        return cached
    try:
        text = path.read_text(encoding="utf-8")  # NOSONAR - path confined
    except (OSError, UnicodeDecodeError):
        _SOURCE_TEXT_CACHE[cache_key] = None
        return None
    _SOURCE_TEXT_CACHE[cache_key] = text
    return text


def _read_runtime_candidate_text(path: Path) -> str | None:
    cache_key = f"{path.as_posix()}::runtime"
    cached = _RUNTIME_CANDIDATE_TEXT_CACHE.get(cache_key)
    if cache_key in _RUNTIME_CANDIDATE_TEXT_CACHE:
        return cached
    text = _read_cached_text(path)
    if text is None or not any(marker in text for marker in _RUNTIME_SCAN_MARKERS):
        _RUNTIME_CANDIDATE_TEXT_CACHE[cache_key] = None
        return None
    _RUNTIME_CANDIDATE_TEXT_CACHE[cache_key] = text
    return text


def _read_runtime_event_candidate_text(path: Path) -> str | None:
    cache_key = f"{path.as_posix()}::runtime-event"
    cached = _RUNTIME_CANDIDATE_TEXT_CACHE.get(cache_key)
    if cache_key in _RUNTIME_CANDIDATE_TEXT_CACHE:
        return cached
    text = _read_cached_text(path)
    if text is None or not any(
        marker in text for marker in _RUNTIME_EVENT_SCAN_MARKERS
    ):
        _RUNTIME_CANDIDATE_TEXT_CACHE[cache_key] = None
        return None
    _RUNTIME_CANDIDATE_TEXT_CACHE[cache_key] = text
    return text
