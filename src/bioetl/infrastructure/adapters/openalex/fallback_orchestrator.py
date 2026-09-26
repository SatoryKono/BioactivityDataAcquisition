"""Fallback orchestration component for OpenAlex adapter."""

from __future__ import annotations

__all__ = ["OpenAlexFallbackOrchestrator"]

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common import (
    ComposableFallbackDecorator,
    DefaultFallbackExecution,
    FallbackDecoratorConfig,
    FallbackFetchOrchestrator,
    resolve_fallback_policy,
)
from bioetl.infrastructure.adapters.openalex.fallback import (
    OpenAlexTitleFallbackHandler,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


def _create_default_fallback_strategy(
    *,
    normalize_id: Callable[[str], str | None],
    extract_record_id: Callable[[BronzeRecord], str | None],
    fallback_handler: OpenAlexTitleFallbackHandler | None,
) -> DefaultFallbackExecution:
    """Create default fallback execution strategy for non-DI call sites.

    Args:
        normalize_id: Callable to normalize ID strings for deduplication.
        extract_record_id: Callable to extract the canonical ID from a record.
        fallback_handler: Optional title-based fallback handler; None disables fallback.

    Returns:
        DefaultFallbackExecution configured with the given normalize and extract hooks.
    """
    return DefaultFallbackExecution(
        normalize_id_hook=normalize_id,
        extract_record_id_hook=extract_record_id,
        fallback_handler_hook=fallback_handler,
    )


def _create_default_fallback_decorator(
    *,
    service: FallbackFetchOrchestrator,
    strategy: DefaultFallbackExecution,
    config: FallbackDecoratorConfig,
    logger: LoggerPort,
) -> ComposableFallbackDecorator:
    """Create default fallback decorator for non-DI call sites.

    Args:
        service: Orchestrator service for executing the fallback fetch pipeline.
        strategy: Execution strategy with normalize/extract/fallback hooks.
        config: Configuration controlling fallback policy behavior.
        logger: Logger port for structured logging.

    Returns:
        ComposableFallbackDecorator wired with the given service, strategy, and config.
    """
    return ComposableFallbackDecorator(
        service=service,
        strategy=strategy,
        config=config,
        logger=logger,
    )


@dataclass(slots=True)
class OpenAlexFallbackOrchestrator:
    """Coordinates DOI-first fetch + title fallback flow for OpenAlex."""

    fallback_fetch_service: FallbackFetchOrchestrator
    fallback_handler: OpenAlexTitleFallbackHandler
    normalize_id: Callable[[str], str | None]
    extract_record_id: Callable[[BronzeRecord], str | None]
    logger: LoggerPort
    fallback_enabled: bool = True
    config: FallbackDecoratorConfig = field(
        default_factory=lambda: FallbackDecoratorConfig(
            supported_filter_field="doi",
            unsupported_filter_event="unsupported_filter_field_for_fallback",
            unsupported_filter_message=(
                "OpenAlex fallback only supports 'doi' filtering, skipping"
            ),
            skip_on_unsupported_filter_field=True,
            primary_lookup_method="doi",
            trim_primary_ids_to_limit=False,
            fallback_operation="fetch_filtered_with_fallback",
        )
    )
    _decorator: ComposableFallbackDecorator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Build reusable decorator from provider hooks + policy config."""
        strategy = _create_default_fallback_strategy(
            normalize_id=self.normalize_id,
            extract_record_id=self.extract_record_id,
            fallback_handler=(self.fallback_handler if self.fallback_enabled else None),
        )
        self._decorator = _create_default_fallback_decorator(
            service=self.fallback_fetch_service,
            strategy=strategy,
            config=self.config,
            logger=self.logger,
        )

    def configure_policy(self, policy: object | None) -> None:
        """Reconfigure fallback policy from provider YAML settings.

        Args:
            policy: Provider YAML fallback policy object, or None to use defaults.
        """
        enabled, config = resolve_fallback_policy(
            policy,
            defaults=self.config,
            default_enabled=True,
        )
        self.fallback_enabled = enabled
        self.config = config
        self.__post_init__()

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
        filter_field: str | None = "doi",
    ) -> AsyncIterator[BronzeRecord]:
        """Run fallback request through shared policy service.

        Args:
            filter_ids: List of DOI strings for primary batch resolution.
            fallback_mapping: Mapping of DOI to title for title-based fallback resolution.
            primary_record_fetcher: Callable that fetches primary records given IDs and limit.
            limit: Optional maximum number of records to yield.
            filter_field: Filter field name used for the primary lookup phase.

        Yields:
            BronzeRecord works from primary DOI resolution and title fallback phases.
        """

        def _log_phase1_summary(total: int, found: int) -> None:
            self.logger.info(
                "openalex_doi_lookup_summary",
                total_dois=total,
                found_by_doi=found,
                missing_dois=total - found,
                hit_rate_pct=round(found / total * 100, 1) if total else 0.0,
            )

        async for work in self._decorator.execute(
            filter_ids=filter_ids,
            fallback_mapping=fallback_mapping,
            primary_record_fetcher=primary_record_fetcher,
            limit=limit,
            phase1_summary_logger=_log_phase1_summary,
            filter_field=filter_field,
        ):
            yield work
