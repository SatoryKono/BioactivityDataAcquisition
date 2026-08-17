"""Private helpers for checkpoint metadata serialization and backfill."""

from __future__ import annotations

from bioetl.domain.types import JsonDict


def optional_stripped_text(value: object) -> str | None:
    """Normalize an optional persisted value to stripped text."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def coerce_records_processed(value: object) -> int:
    """Coerce a persisted records-processed value to an integer."""
    if value is None:
        return 0
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return _parse_records_processed_text(value)


def _parse_records_processed_text(value: object) -> int:
    if not isinstance(value, str):
        raise ValueError("records_processed must be an integer")
    text = value.strip()
    if not text or not text.lstrip("-").isdigit():
        raise ValueError("records_processed must be an integer")
    return int(text)


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


def extract_checkpoint_anchor(data: JsonDict, key: str) -> str | None:
    """Extract optional text with a like-named run-context fallback."""
    value = data.get(key)
    if value is not None:
        return optional_stripped_text(value)
    return extract_run_context_anchor(data, key)


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


def coerce_json_dict_sequence(value: object) -> tuple[JsonDict, ...]:
    """Coerce persisted JSON objects into an immutable tuple."""
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def snapshot_fingerprint_inputs(
    refs: tuple[JsonDict, ...],
    ids: tuple[str, ...],
) -> list[object]:
    """Return snapshot refs or identifier-backed fallback inputs."""
    if refs:
        return list(refs)
    return [{"snapshot_id": snapshot_id} for snapshot_id in ids]


__all__ = [
    "coerce_json_dict_sequence",
    "coerce_records_processed",
    "coerce_snapshot_ids",
    "coerce_snapshot_refs",
    "extract_checkpoint_anchor",
    "extract_run_context_anchor",
    "is_empty_checkpoint_metadata_value",
    "optional_stripped_text",
    "snapshot_fingerprint_inputs",
]
