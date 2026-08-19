"""Metadata-writer candidate collection for ledger collaborator attach."""

from __future__ import annotations

from typing import cast

def _metadata_from_layer_writer(writer: object) -> object | None:
    """Resolve a metadata writer from one layer storage writer."""
    writer_metadata = None
    for accessor_name in (
        "metadata_writer",
        "get_metadata_writer",
        "metadata",
    ):
        accessor = getattr(writer, accessor_name, None)
        if callable(accessor) and accessor_name.startswith("get_"):
            try:
                writer_metadata = accessor()
            except (AttributeError, RuntimeError, TypeError, ValueError):
                writer_metadata = None
        elif accessor is not None and not callable(accessor):
            writer_metadata = accessor
        if writer_metadata is not None:
            return cast("object | None", writer_metadata)
    return cast(object | None, getattr(writer, "_metadata_writer", None))


def _collect_metadata_writer_candidates(services: object) -> list[object]:
    candidates: list[object] = []
    metadata_writer = getattr(services, "metadata_writer", None)
    if metadata_writer is not None:
        candidates.append(metadata_writer)

    storage = getattr(services, "storage", None)
    if storage is None:
        return candidates

    for writer_name in ("bronze", "silver", "gold"):
        writer = getattr(storage, writer_name, None)
        if writer is None:
            continue
        # Prefer public contract accessors; fall back to legacy private field.
        writer_metadata = _metadata_from_layer_writer(writer)
        if writer_metadata is not None:
            candidates.append(writer_metadata)
    return candidates


def _iter_unique_candidates(candidates: list[object]) -> list[object]:
    unique_candidates: list[object] = []
    seen: set[int] = set()
    for candidate in candidates:
        candidate_id = id(candidate)
        if candidate_id in seen:
            continue
        seen.add(candidate_id)
        unique_candidates.append(candidate)
    return unique_candidates


