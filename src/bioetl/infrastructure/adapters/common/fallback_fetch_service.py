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
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder


class PrimaryRecordFetchProtocol(Protocol):
    """Provider hook that yields phase-1 primary lookup records."""

    def __call__(
        self, primary_ids: list[str], limit: int | None, /
    ) -> AsyncIterator[BronzeRecord]: ...


class NormalizeIdProtocol(Protocol):
    """Provider hook for ID normalization used in fallback matching."""

    def __call__(self, value: str, /) -> str | None: ...


class ExtractRecordIdProtocol(Protocol):
    """Provider hook extracting the record ID tracked as resolved."""

    def __call__(self, record: BronzeRecord, /) -> str | None: ...


class Phase1SummaryLoggerProtocol(Protocol):
    """Optional provider hook for phase-1 summary logging."""

    def __call__(self, total: int, found: int, /) -> None: ...


class FallbackExecutionProtocol(Protocol):
    """Generic strategy interface for fallback execution hooks."""

    def normalize_id(self, value: str, /) -> str | None:
        """Normalize a raw identifier for lookup consistency."""
        ...

    def extract_record_id(self, record: BronzeRecord, /) -> str | None:
        """Extract the primary identifier from a fetched record."""
        ...

    @property
    def fallback_handler(self) -> FallbackPolicyHandler | None:
        """Return the fallback policy handler, if configured."""
        ...


@dataclass(frozen=True, slots=True)
class DefaultFallbackExecution:
    """Concrete strategy wrapper for fallback hook callables."""

    normalize_id_hook: NormalizeIdProtocol
    extract_record_id_hook: ExtractRecordIdProtocol
    fallback_handler_hook: FallbackPolicyHandler | None = None

    def normalize_id(self, value: str, /) -> str | None:
        """Normalize a raw identifier by delegating to the hook."""
        return self.normalize_id_hook(value)

    def extract_record_id(self, record: BronzeRecord, /) -> str | None:
        """Extract the primary identifier by delegating to the hook."""
        return self.extract_record_id_hook(record)

    @property
    def fallback_handler(self) -> FallbackPolicyHandler | None:
        """Return the fallback policy handler, if configured."""
        return self.fallback_handler_hook


@dataclass(slots=True)
class FallbackFetchRequest:
    """Input contract for fallback fetch orchestration."""

    filter_ids: list[str]
    fallback_mapping: dict[str, str]
    primary_record_fetcher: PrimaryRecordFetchProtocol
    normalize_id: NormalizeIdProtocol | None = None
    extract_record_id: ExtractRecordIdProtocol | None = None
    fallback_handler: FallbackPolicyHandler | None = None
    strategy: FallbackExecutionProtocol | None = None
    limit: int | None = None
    primary_lookup_method: str | None = None
    phase1_summary_logger: Phase1SummaryLoggerProtocol | None = None
    trim_primary_ids_to_limit: bool = False
    fallback_operation: str = "fetch_filtered_with_fallback"

    def resolve_normalize_id(self) -> NormalizeIdProtocol:
        """Return normalize-id hook from explicit request or strategy.

        Returns:
            NormalizeIdProtocol callable from the request or strategy.
        """
        if self.normalize_id is not None:
            return self.normalize_id
        if self.strategy is not None:
            return self.strategy.normalize_id
        raise ValueError(
            "FallbackFetchRequest must define normalize_id or strategy.normalize_id"
        )

    def resolve_extract_record_id(self) -> ExtractRecordIdProtocol:
        """Return record-id extractor from explicit request or strategy.

        Returns:
            ExtractRecordIdProtocol callable from the request or strategy.
        """
        if self.extract_record_id is not None:
            return self.extract_record_id
        if self.strategy is not None:
            return self.strategy.extract_record_id
        raise ValueError(
            "FallbackFetchRequest must define extract_record_id or "
            "strategy.extract_record_id"
        )

    def resolve_fallback_handler(self) -> FallbackPolicyHandler | None:
        """Return fallback handler from request override or strategy.

        Returns:
            FallbackPolicyHandler if configured on request or strategy, None otherwise.
        """
        if self.fallback_handler is not None:
            return self.fallback_handler
        if self.strategy is not None:
            return self.strategy.fallback_handler
        return None


class FallbackFetchOrchestrator:
    """Shared orchestrator for fallback-enabled filtered fetch flows."""

    def __init__(self, adapter_metrics: AdapterMetricsRecorder | None = None) -> None:
        """Initialize the fallback fetch orchestrator.

        Args:
            adapter_metrics: Optional metrics recorder for tracking fallback
                outcomes; disables metrics emission when None.
        """
        self._adapter_metrics = adapter_metrics

    async def execute(
        self, request: FallbackFetchRequest
    ) -> AsyncIterator[BronzeRecord]:
        """Run common 3-phase fetch/fallback flow with provider hooks.

        Args:
            request: Fully configured fallback fetch request containing filter
                IDs, the primary fetcher hook, fallback handler, and limits.

        Returns:
            Async iterator of BronzeRecord dicts from primary fetch and fallback phases.
        """
        primary_ids, title_only_entries = split_filter_ids_for_fallback(
            request.filter_ids
        )
        if request.trim_primary_ids_to_limit and request.limit is not None:
            safe_limit = max(request.limit, 0)
            primary_ids = primary_ids[:safe_limit]

        normalize_id = request.resolve_normalize_id()
        extract_record_id = request.resolve_extract_record_id()
        fallback_handler = request.resolve_fallback_handler()

        primary_resolved = 0
        fallback_hits = 0
        async for record in run_fetch_with_fallback_policy(
            primary_records=request.primary_record_fetcher(primary_ids, request.limit),
            primary_ids=primary_ids,
            title_only_entries=title_only_entries,
            fallback_mapping=request.fallback_mapping,
            normalize_id=normalize_id,
            extract_record_id=extract_record_id,
            fallback_handler=fallback_handler,
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
            fallback_handler=fallback_handler,
        )

    def _record_fallback_metrics(
        self,
        *,
        request: FallbackFetchRequest,
        primary_ids: list[str],
        title_only_entries: list[str],
        primary_resolved: int,
        fallback_hits: int,
        fallback_handler: FallbackPolicyHandler | None,
    ) -> None:
        """Record unified fallback metrics when adapter metrics are configured."""
        if self._adapter_metrics is None or fallback_handler is None:
            return

        unresolved_primary = max(0, len(primary_ids) - primary_resolved)
        candidates = unresolved_primary + len(title_only_entries)
        self._adapter_metrics.record_fallback_outcome(
            request.fallback_operation,
            candidates=candidates,
            hits=fallback_hits,
        )


FallbackFetchOrchestratorService = FallbackFetchOrchestrator
