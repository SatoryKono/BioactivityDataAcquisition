"""Typed entity construction helpers for unit tests (PD2-9 / #6959).

basedpyright rejects ``Entity(**mixed_dict)`` when values collapse to
``str | int | datetime`` unions. These helpers keep NewType/enum fields
explicit and funnel overrides through ``cast(Any, ...)`` at the test boundary
only — product entity types stay strict.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid5, NAMESPACE_URL

from bioetl.domain.types import BatchID, ContentHash, EntityID, RunID, RunType

__all__ = [
    "base_lineage_kwargs",
    "entity_kwargs",
    "lineage_kwargs",
]


def _as_run_id(run_id: str | RunID | UUID) -> RunID:
    if isinstance(run_id, UUID):
        return RunID(run_id)
    if isinstance(run_id, str):
        # Deterministic UUID for string run ids used in pure unit tests.
        return RunID(uuid5(NAMESPACE_URL, f"bioetl:test-run:{run_id}"))
    return run_id


def _as_batch_id(source_batch_id: UUID | str | BatchID) -> BatchID:
    if isinstance(source_batch_id, UUID):
        return BatchID(source_batch_id)
    if isinstance(source_batch_id, str):
        try:
            return BatchID(UUID(source_batch_id))
        except ValueError:
            return BatchID(uuid5(NAMESPACE_URL, f"bioetl:test-batch:{source_batch_id}"))
    return source_batch_id


def lineage_kwargs(
    *,
    entity_id: str = "entity:test-1",
    content_hash: str = "sha256hash",
    run_id: str | RunID | UUID = "run-001",
    run_type: RunType | str = RunType.INCREMENTAL,
    ingestion_ts: datetime | None = None,
    index: int = 0,
    source_batch_id: UUID | str | BatchID | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """Return lineage/BaseEntity fields with correct domain NewTypes."""
    kwargs: dict[str, Any] = {
        "entity_id": EntityID(entity_id),
        "content_hash": ContentHash(content_hash),
        "run_id": _as_run_id(run_id),
        "run_type": run_type
        if isinstance(run_type, RunType)
        else RunType(str(run_type)),
        "ingestion_ts": ingestion_ts
        if ingestion_ts is not None
        else datetime(2024, 6, 1, tzinfo=UTC),
        "_index": index,
    }
    if source_batch_id is not None:
        kwargs["source_batch_id"] = _as_batch_id(source_batch_id)
    kwargs.update(overrides)
    return kwargs


# Back-compat alias used by older test modules.
base_lineage_kwargs = lineage_kwargs


def entity_kwargs(**overrides: Any) -> Any:
    """Merge lineage defaults with entity-specific fields for ``Cls(**kwargs)``.

    Returns ``Any`` so basedpyright accepts ``Entity(**entity_kwargs(...))``
    without widening product constructor signatures.
    """
    return cast(Any, lineage_kwargs(**overrides))
