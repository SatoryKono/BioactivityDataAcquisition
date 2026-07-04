"""Composition-owned occurrence identity factories.

These IDs are operational correlation identifiers, not replay identity anchors.
They intentionally avoid random UUID generation while preserving low collision
risk for local runtime occurrences.
"""

from __future__ import annotations

from itertools import count
from os import getpid
from time import monotonic_ns, time_ns
from uuid import UUID

from bioetl.domain.deterministic_identity import deterministic_uuid
from bioetl.domain.types import BatchID, RunID

_PROCESS_OCCURRENCE_SEED = {
    "monotonic_ns": monotonic_ns(),
    "pid": getpid(),
    "wall_time_ns": time_ns(),
}
_SCOPE_COUNTERS: dict[str, count[int]] = {}


def _next_scope_sequence(scope: str) -> int:
    counter = _SCOPE_COUNTERS.get(scope)
    if counter is None:
        counter = count(1)
        _SCOPE_COUNTERS[scope] = counter
    return next(counter)


def create_runtime_occurrence_uuid(scope: str) -> UUID:
    """Return a UUIDv5 occurrence ID for one composition-owned runtime scope."""
    return deterministic_uuid(
        "composition.runtime_occurrence",
        {
            "process_seed": _PROCESS_OCCURRENCE_SEED,
            "scope": scope,
            "sequence": _next_scope_sequence(scope),
        },
    )


def create_runtime_occurrence_id(scope: str) -> str:
    """Return a string occurrence ID for one composition-owned runtime scope."""
    return str(create_runtime_occurrence_uuid(scope))


def create_runtime_occurrence_run_id(scope: str) -> RunID:
    """Return a RunID occurrence identifier for runtime assembly."""
    return RunID(create_runtime_occurrence_uuid(scope))


def create_runtime_occurrence_batch_id(scope: str) -> BatchID:
    """Return a BatchID occurrence identifier for runtime assembly."""
    return BatchID(create_runtime_occurrence_uuid(scope))


__all__ = [
    "create_runtime_occurrence_batch_id",
    "create_runtime_occurrence_id",
    "create_runtime_occurrence_run_id",
    "create_runtime_occurrence_uuid",
]
