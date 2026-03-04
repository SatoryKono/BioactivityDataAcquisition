"""Fallback orchestration component for OpenAlex adapter."""

from __future__ import annotations

__all__ = ["OpenAlexFallbackOrchestrator"]

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common import (
    FallbackFetchOrchestratorService,
    FallbackFetchRequest,
)
from bioetl.infrastructure.adapters.openalex.fallback import TitleFallbackHandler

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass(slots=True)
class OpenAlexFallbackOrchestrator:
    """Coordinates DOI-first fetch + title fallback flow for OpenAlex."""

    fallback_fetch_service: FallbackFetchOrchestratorService
    fallback_handler: TitleFallbackHandler
    normalize_id: Callable[[str], str | None]
    extract_record_id: Callable[[BronzeRecord], str | None]
    logger: LoggerPort

    async def execute(
        self,
        *,
        filter_ids: list[str],
        fallback_mapping: dict[str, str],
        primary_record_fetcher: Callable[
            [list[str], int | None],
            AsyncIterator[BronzeRecord],
        ],
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Run fallback request through shared policy service."""

        def _log_phase1_summary(total: int, found: int) -> None:
            self.logger.info(
                "openalex_doi_lookup_summary",
                total_dois=total,
                found_by_doi=found,
                missing_dois=total - found,
                hit_rate_pct=round(found / total * 100, 1) if total else 0.0,
            )

        request = FallbackFetchRequest(
            filter_ids=filter_ids,
            fallback_mapping=fallback_mapping,
            primary_record_fetcher=primary_record_fetcher,
            normalize_id=self.normalize_id,
            extract_record_id=self.extract_record_id,
            fallback_handler=self.fallback_handler,
            limit=limit,
            primary_lookup_method="doi",
            phase1_summary_logger=_log_phase1_summary,
        )
        async for work in self.fallback_fetch_service.execute(request):
            yield work
