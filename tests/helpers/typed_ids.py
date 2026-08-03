"""Typed domain ID factories for unit tests (PD5-1 / #6996).

basedpyright rejects bare ``UUID`` / ``str`` where product APIs require
``RunID``, ``BatchID``, ``EntityID``, or ``ContentHash`` NewTypes.
"""

from __future__ import annotations

from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from bioetl.domain.types import BatchID, ContentHash, EntityID, RunID, RunType

__all__ = [
    "as_batch_id",
    "as_content_hash",
    "as_entity_id",
    "as_run_id",
    "as_run_type",
    "new_batch_id",
    "new_run_id",
]


def as_run_id(value: str | UUID | RunID | None = None) -> RunID:
    """Coerce test inputs to ``RunID`` (deterministic for stable strings)."""
    if value is None:
        return RunID(uuid4())
    if isinstance(value, UUID):
        return RunID(value)
    if isinstance(value, str):
        try:
            return RunID(UUID(value))
        except ValueError:
            return RunID(uuid5(NAMESPACE_URL, f"bioetl:test-run:{value}"))
    return value


def as_batch_id(value: str | UUID | BatchID | None = None) -> BatchID:
    """Coerce test inputs to ``BatchID``."""
    if value is None:
        return BatchID(uuid4())
    if isinstance(value, UUID):
        return BatchID(value)
    if isinstance(value, str):
        try:
            return BatchID(UUID(value))
        except ValueError:
            return BatchID(uuid5(NAMESPACE_URL, f"bioetl:test-batch:{value}"))
    return value


def as_entity_id(value: str = "entity:test-1") -> EntityID:
    """Coerce a string business key to ``EntityID``."""
    return EntityID(value)


def as_content_hash(value: str = "0" * 64) -> ContentHash:
    """Coerce a hash string to ``ContentHash``."""
    return ContentHash(value)


def as_run_type(value: str | RunType = RunType.INCREMENTAL) -> RunType:
    """Coerce run type enums / strings."""
    if isinstance(value, RunType):
        return value
    return RunType(str(value))


def new_run_id() -> RunID:
    """Random run id for isolation-oriented tests."""
    return RunID(uuid4())


def new_batch_id() -> BatchID:
    """Random batch id for isolation-oriented tests."""
    return BatchID(uuid4())
