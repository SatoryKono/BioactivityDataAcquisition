"""Shared fetch/retry policy helpers for infrastructure adapters."""

from __future__ import annotations

__all__ = [
    "TITLE_ONLY_MARKER_PREFIX",
    "FallbackPolicyHandler",
    "is_retry_exhausted_error",
    "run_fetch_with_fallback_policy",
    "split_filter_ids_for_fallback",
]


from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import cast

from bioetl.domain.exceptions import RetryExhaustedError
from bioetl.domain.ports import FallbackPolicyPort
from bioetl.domain.types import BronzeRecord

TITLE_ONLY_MARKER_PREFIX = "__title_only_"
type FallbackPolicyHandler = FallbackPolicyPort


@dataclass(slots=True)
class _FetchState:
    """Mutable state shared across fallback phases."""

    fetched: int = 0
    limit: int | None = None

    def limit_reached(self) -> bool:
        """Check whether the fetch count has reached the configured limit."""
        return self.limit is not None and self.fetched >= self.limit


def split_filter_ids_for_fallback(
    filter_ids: list[str],
    *,
    title_only_marker_prefix: str = TITLE_ONLY_MARKER_PREFIX,
) -> tuple[list[str], list[str]]:
    """Split input IDs into primary IDs and title-only fallback entries.

    Empty/whitespace values and ``__title_only_*`` markers are treated as
    title-only entries for phase-3 fallback.

    Args:
        filter_ids: List of raw filter IDs to split.
        title_only_marker_prefix: Prefix string that marks title-only fallback entries.

    Returns:
        Tuple of (primary_ids, title_only_entries) lists.
    """
    primary_ids: list[str] = []
    title_only_entries: list[str] = []
    for raw_id in filter_ids:
        stripped = raw_id.strip()
        if not stripped or stripped.startswith(title_only_marker_prefix):
            title_only_entries.append(raw_id)
            continue
        primary_ids.append(raw_id)
    return primary_ids, title_only_entries


def is_retry_exhausted_error(error: Exception) -> bool:
    """Return True when ``error`` or its cause/context chain is retry-exhausted.

    Args:
        error: Exception to check for RetryExhaustedError in the chain.
    """
    seen: set[int] = set()
    current: Exception | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, RetryExhaustedError):
            return True

        next_exc: Exception | None = None
        if isinstance(current.__cause__, Exception):
            next_exc = current.__cause__
        elif isinstance(current.__context__, Exception):
            next_exc = current.__context__
        current = next_exc
    return False


def _track_primary_record(
    record: BronzeRecord,
    *,
    primary_lookup_method: str | None,
    extract_record_id: Callable[[BronzeRecord], str | None],
    found_ids: set[str],
) -> None:
    """Apply phase-1 record bookkeeping (lookup method + resolved IDs).

    Args:
        record: Bronze record to annotate and track.
        primary_lookup_method: Lookup method label to inject into record if not already set.
        extract_record_id: Callable to extract the primary ID from a record.
        found_ids: Mutable set to add the resolved record ID to.
    """
    if primary_lookup_method and "_lookup_method" not in record:
        record["_lookup_method"] = primary_lookup_method

    record_id = extract_record_id(record)
    if record_id:
        found_ids.add(record_id.strip().lower())


def _log_phase1_summary(
    *,
    phase1_summary_logger: Callable[[int, int], None] | None,
    primary_ids: list[str],
    found_ids: set[str],
) -> None:
    """Log phase-1 completion summary when logger and input IDs are available.

    Args:
        phase1_summary_logger: Optional callable receiving (total_ids, found_ids) counts.
        primary_ids: Full list of primary IDs requested in phase 1.
        found_ids: Set of IDs successfully resolved during phase 1.
    """
    if phase1_summary_logger is None or not primary_ids:
        return
    phase1_summary_logger(len(primary_ids), len(found_ids))


async def _yield_phase_records(
    *,
    records: AsyncIterator[BronzeRecord],
    state: _FetchState,
    on_record: Callable[[BronzeRecord], None] | None = None,
) -> AsyncIterator[BronzeRecord]:
    """Yield records for one phase with shared limit handling.

    Args:
        records: Async iterator of Bronze records for this phase.
        state: Mutable fetch state tracking total count and limit.
        on_record: Optional callback invoked on each record before yielding.

    Yields:
        Bronze records until the configured limit is reached or the iterator is exhausted.
    """
    if state.limit_reached():
        return

    try:
        async for record in records:
            if on_record:
                on_record(record)
            yield record
            state.fetched += 1
            if state.limit_reached():
                return
    finally:
        aclose = getattr(records, "aclose", None)
        if callable(aclose):
            aclose_fn = cast(Callable[[], Awaitable[object]], aclose)
            await aclose_fn()


async def run_fetch_with_fallback_policy(
    *,
    primary_records: AsyncIterator[BronzeRecord],
    primary_ids: list[str],
    title_only_entries: list[str],
    fallback_mapping: dict[str, str],
    normalize_id: Callable[[str], str | None],
    extract_record_id: Callable[[BronzeRecord], str | None],
    fallback_handler: FallbackPolicyPort | None,
    limit: int | None = None,
    primary_lookup_method: str | None = None,
    phase1_summary_logger: Callable[[int, int], None] | None = None,
) -> AsyncIterator[BronzeRecord]:
    """Execute shared 3-phase fetch strategy with title fallback.

    Phase 1: consume ``primary_records``, track resolved IDs.
    Phase 2: ``process_missing_dois`` for unresolved primary IDs.
    Phase 3: ``process_title_only_entries`` for empty/marker entries.

    Args:
        primary_records: Async iterator of records from the primary fetch phase.
        primary_ids: List of primary IDs requested in phase 1.
        title_only_entries: List of title-only marker entries for phase 3.
        fallback_mapping: Mapping of normalized IDs to fallback values (e.g., titles).
        normalize_id: Callable to normalize a raw ID for lookup.
        extract_record_id: Callable to extract the primary ID from a fetched record.
        fallback_handler: Optional fallback policy port for phase 2 and phase 3.
        limit: Optional maximum total records to yield across all phases.
        primary_lookup_method: Optional label injected into phase-1 records as _lookup_method.
        phase1_summary_logger: Optional callable receiving (total, found) counts after phase 1.

    Yields:
        Bronze records from all phases in order, respecting the global limit.
    """
    state = _FetchState(limit=limit)
    found_ids: set[str] = set()

    async for record in _yield_phase_records(
        records=primary_records,
        state=state,
        on_record=lambda rec: _track_primary_record(
            rec,
            primary_lookup_method=primary_lookup_method,
            extract_record_id=extract_record_id,
            found_ids=found_ids,
        ),
    ):
        yield record

    _log_phase1_summary(
        phase1_summary_logger=phase1_summary_logger,
        primary_ids=primary_ids,
        found_ids=found_ids,
    )
    if state.limit_reached():
        return

    if fallback_handler is None:
        return

    async for record in _yield_phase_records(
        records=fallback_handler.process_missing_dois(
            dois=primary_ids,
            found_dois=found_ids,
            fallback_mapping=fallback_mapping,
            normalize_fn=normalize_id,
            limit=limit,
            fetched=state.fetched,
        ),
        state=state,
    ):
        yield record
    if state.limit_reached():
        return

    async for record in _yield_phase_records(
        records=fallback_handler.process_title_only_entries(
            entries=title_only_entries,
            fallback_mapping=fallback_mapping,
            limit=limit,
            fetched=state.fetched,
        ),
        state=state,
    ):
        yield record
