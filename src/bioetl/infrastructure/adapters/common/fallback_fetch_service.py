"""Reusable fallback-fetch orchestration service for adapters.

Keeps the shared skeleton (split IDs + three-phase policy execution) in one place
while provider adapters pass only narrow hooks via protocols.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.fetch_retry_policy import (
    FallbackPolicyHandler,
    run_fetch_with_fallback_policy,
    split_filter_ids_for_fallback,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics


class PrimaryRecordFetchHook(Protocol):
    """Provider hook that yields phase-1 primary lookup records."""

    def __call__(
        self, primary_ids: list[str], limit: int | None, /
    ) -> AsyncIterator[BronzeRecord]: ...


class NormalizeIdHook(Protocol):
    """Provider hook for ID normalization used in fallback matching."""

    def __call__(self, value: str, /) -> str | None: ...


class ExtractRecordIdHook(Protocol):
    """Provider hook extracting the record ID tracked as resolved."""

    def __call__(self, record: BronzeRecord, /) -> str | None: ...


class Phase1SummaryLoggerHook(Protocol):
    """Optional provider hook for phase-1 summary logging."""

    def __call__(self, total: int, found: int, /) -> None: ...


@dataclass(slots=True)
class FallbackFetchRequest:
    """Input contract for fallback fetch orchestration."""

    filter_ids: list[str]
    fallback_mapping: dict[str, str]
    primary_record_fetcher: PrimaryRecordFetchHook
    normalize_id: NormalizeIdHook
    extract_record_id: ExtractRecordIdHook
    fallback_handler: FallbackPolicyHandler | None
    limit: int | None = None
    primary_lookup_method: str | None = None
    phase1_summary_logger: Phase1SummaryLoggerHook | None = None
    trim_primary_ids_to_limit: bool = False
    fallback_operation: str = "fetch_filtered_with_fallback"


class FallbackFetchOrchestratorService:
    """Shared service for fallback-enabled filtered fetch flows."""

    def __init__(self, adapter_metrics: AdapterMetrics | None = None) -> None:
        self._adapter_metrics = adapter_metrics

    async def execute(
        self, request: FallbackFetchRequest
    ) -> AsyncIterator[BronzeRecord]:
        """Run common 3-phase fetch/fallback flow with provider hooks."""
        primary_ids, title_only_entries = split_filter_ids_for_fallback(
            request.filter_ids
        )
        if request.trim_primary_ids_to_limit and request.limit is not None:
            safe_limit = max(request.limit, 0)
            primary_ids = primary_ids[:safe_limit]

        primary_resolved = 0
        fallback_hits = 0
        async for record in run_fetch_with_fallback_policy(
            primary_records=request.primary_record_fetcher(primary_ids, request.limit),
            primary_ids=primary_ids,
            title_only_entries=title_only_entries,
            fallback_mapping=request.fallback_mapping,
            normalize_id=request.normalize_id,
            extract_record_id=request.extract_record_id,
            fallback_handler=request.fallback_handler,
            limit=request.limit,
            primary_lookup_method=request.primary_lookup_method,
            phase1_summary_logger=request.phase1_summary_logger,
        ):
            lookup_method = str(record.get("_lookup_method", ""))
            if (
                request.primary_lookup_method
                and lookup_method == request.primary_lookup_method
            ):
                primary_resolved += 1
            elif lookup_method in {"title_fallback", "title_only", "title"}:
                fallback_hits += 1
            yield record

        self._record_fallback_metrics(
            request=request,
            primary_ids=primary_ids,
            title_only_entries=title_only_entries,
            primary_resolved=primary_resolved,
            fallback_hits=fallback_hits,
        )

    def _record_fallback_metrics(
        self,
        *,
        request: FallbackFetchRequest,
        primary_ids: list[str],
        title_only_entries: list[str],
        primary_resolved: int,
        fallback_hits: int,
    ) -> None:
        """Record unified fallback metrics when adapter metrics are configured."""
        if self._adapter_metrics is None or request.fallback_handler is None:
            return

        unresolved_primary = max(0, len(primary_ids) - primary_resolved)
        candidates = unresolved_primary + len(title_only_entries)
        self._adapter_metrics.record_fallback_outcome(
            request.fallback_operation,
            candidates=candidates,
            hits=fallback_hits,
        )
