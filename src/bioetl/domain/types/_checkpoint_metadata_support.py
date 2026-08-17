"""Private helpers for checkpoint metadata serialization and backfill."""

from __future__ import annotations

from bioetl.domain.types import JsonDict


def coerce_snapshot_refs(value: object | None) -> tuple[JsonDict, ...]:
    """Normalize persisted snapshot refs into an immutable tuple of mappings."""
    if not isinstance(value, (list, tuple)):
        return ()
    normalized: list[JsonDict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        normalized.append({str(key): field for key, field in item.items()})
    return tuple(normalized)


def extract_run_context_anchor(data: JsonDict, key: str) -> str | None:
    """Backfill an optional checkpoint anchor from legacy run_context payloads."""
    run_context = data.get("run_context")
    if not isinstance(run_context, dict):
        return None
    value = run_context.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def coerce_snapshot_ids(value: object | None) -> tuple[str, ...]:
    """Normalize persisted snapshot identifiers into a stable tuple."""
    if not isinstance(value, (list, tuple)):
        return ()
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _snapshot_id_text(item)
        if text is None or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return tuple(normalized)


def _snapshot_id_text(item: object) -> str | None:
    if not isinstance(item, str):
        return None
    text = item.strip()
    return text or None


def is_empty_checkpoint_metadata_value(value: object | None) -> bool:
    """Return whether optional checkpoint metadata should be omitted from serialization."""
    if value is None or value == "":
        return True
    if isinstance(value, (tuple, list, dict)):
        return len(value) == 0
    return False


__all__ = [
    "coerce_snapshot_ids",
    "coerce_snapshot_refs",
    "extract_run_context_anchor",
    "is_empty_checkpoint_metadata_value",
]
