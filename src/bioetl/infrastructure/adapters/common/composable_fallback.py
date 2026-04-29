"""Composable fallback decorator for provider adapters.

Provides one reusable orchestration entrypoint that builds
``FallbackFetchRequest`` using strategy hooks + policy config.
"""

from __future__ import annotations

__all__ = [
    "ComposableFallbackDecorator",
    "FallbackDecoratorConfig",
    "resolve_fallback_policy",
]

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
    ExtractRecordIdProtocol,
    FallbackExecutionProtocol,
    FallbackFetchOrchestratorService,
    FallbackFetchRequest,
    NormalizeIdProtocol,
    Phase1SummaryLoggerProtocol,
    PrimaryRecordFetchProtocol,
)
from bioetl.infrastructure.adapters.common.fetch_retry_policy import (
    FallbackPolicyHandler,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class FallbackDecoratorConfig:
    """Policy knobs for fallback execution wiring."""

    supported_filter_field: str | None = None
    unsupported_filter_event: str = "unsupported_filter_field_for_fallback"
    unsupported_filter_message: str = (
        "Fallback only supports '{expected}' filtering, skipping"
    )
    skip_on_unsupported_filter_field: bool = True
    primary_lookup_method: str | None = None
    trim_primary_ids_to_limit: bool = False
    fallback_operation: str = "fetch_filtered_with_fallback"


class ComposableFallbackDecorator:
    """Single fallback execution decorator reusable across provider adapters."""

    def __init__(
        self,
        *,
        service: FallbackFetchOrchestratorService,
        strategy: FallbackExecutionProtocol,
        config: FallbackDecoratorConfig,
        logger: LoggerPort,
    ) -> None:
        """Initialize ComposableFallbackDecorator.

        Args:
            service: Orchestration service that executes the FallbackFetchRequest.
            strategy: Provider-specific hooks for ID extraction and fallback handling.
            config: Policy configuration for filter field gating and operation naming.
            logger: Structured logger for unsupported filter field warnings.
        """
        self._service = service
        self._strategy = strategy
        self._config = config
        self._logger = logger

    @property
    def config(self) -> FallbackDecoratorConfig:
        """Expose immutable config for diagnostics/tests."""
        return self._config

    async def execute(
        self,
        *,
        filter_ids: list[str],
        fallback_mapping: dict[str, str],
        primary_record_fetcher: PrimaryRecordFetchProtocol,
        limit: int | None,
        filter_field: str | None = None,
        phase1_summary_logger: Phase1SummaryLoggerProtocol | None = None,
        normalize_id: NormalizeIdProtocol | None = None,
        extract_record_id: ExtractRecordIdProtocol | None = None,
        fallback_handler: FallbackPolicyHandler | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Execute fallback orchestration with policy-aware filter gating.

        Args:
            filter_ids: List of raw filter IDs to process across all phases.
            fallback_mapping: Mapping of normalized IDs to fallback values (e.g., titles).
            primary_record_fetcher: Async callable for the phase-1 primary fetch.
            limit: Optional maximum total records to yield across all phases.
            filter_field: Active filter field name checked against supported_filter_field.
            phase1_summary_logger: Optional callable receiving (total, found) counts after phase 1.
            normalize_id: Optional ID normalization hook; falls back to strategy hook.
            extract_record_id: Optional ID extraction hook; falls back to strategy hook.
            fallback_handler: Optional fallback policy port; falls back to strategy hook.

        Yields:
            Bronze records from all phases in order, respecting the global limit.
        """
        if not self._is_supported_filter_field(filter_field):
            self._log_unsupported_filter_field(filter_field)
            if self._config.skip_on_unsupported_filter_field:
                return

        request = FallbackFetchRequest(
            filter_ids=filter_ids,
            fallback_mapping=fallback_mapping,
            primary_record_fetcher=primary_record_fetcher,
            strategy=self._strategy,
            normalize_id=normalize_id or self._strategy.normalize_id,
            extract_record_id=extract_record_id or self._strategy.extract_record_id,
            fallback_handler=fallback_handler or self._strategy.fallback_handler,
            limit=limit,
            primary_lookup_method=self._config.primary_lookup_method,
            phase1_summary_logger=phase1_summary_logger,
            trim_primary_ids_to_limit=self._config.trim_primary_ids_to_limit,
            fallback_operation=self._config.fallback_operation,
        )
        async for record in self._service.execute(request):
            yield record

    def _is_supported_filter_field(self, filter_field: str | None) -> bool:
        """Check whether the given filter field is supported by this fallback decorator.

        Args:
            filter_field: Active filter field name to validate against the configured restriction.

        Returns:
            True if the filter field matches the configured supported field or no restriction is set.
        """
        expected = self._config.supported_filter_field
        if expected is None:
            return True
        return filter_field == expected

    def _log_unsupported_filter_field(self, filter_field: str | None) -> None:
        """Log a warning when the filter field is not supported.

        Args:
            filter_field: Unsupported filter field name to include in the warning log.
        """
        expected = self._config.supported_filter_field
        if expected is None:
            return
        self._logger.warning(
            self._config.unsupported_filter_event,
            field=filter_field,
            expected=expected,
            msg=self._config.unsupported_filter_message.format(expected=expected),
        )


def resolve_fallback_policy(
    policy: object | None,
    *,
    defaults: FallbackDecoratorConfig,
    default_enabled: bool = True,
) -> tuple[bool, FallbackDecoratorConfig]:
    """Resolve runtime fallback enabled flag + config from YAML policy object.

    Args:
        policy: Optional policy config object loaded from YAML; None uses defaults.
        defaults: Default FallbackDecoratorConfig to fall back to for missing attributes.
        default_enabled: Default enabled flag when policy is None or lacks the attribute.

    Returns:
        Tuple of (enabled flag, resolved FallbackDecoratorConfig).
    """
    if policy is None:
        return default_enabled, defaults

    enabled = _get_bool_attr(policy, "enabled", default_enabled)
    resolved = FallbackDecoratorConfig(
        supported_filter_field=_get_optional_str_attr(
            policy,
            "supported_filter_field",
            defaults.supported_filter_field,
        ),
        unsupported_filter_event=_get_str_attr(
            policy,
            "unsupported_filter_event",
            defaults.unsupported_filter_event,
        ),
        unsupported_filter_message=_get_str_attr(
            policy,
            "unsupported_filter_message",
            defaults.unsupported_filter_message,
        ),
        skip_on_unsupported_filter_field=_get_bool_attr(
            policy,
            "skip_on_unsupported_filter_field",
            defaults.skip_on_unsupported_filter_field,
        ),
        primary_lookup_method=_get_optional_str_attr(
            policy,
            "primary_lookup_method",
            defaults.primary_lookup_method,
        ),
        trim_primary_ids_to_limit=_get_bool_attr(
            policy,
            "trim_primary_ids_to_limit",
            defaults.trim_primary_ids_to_limit,
        ),
        fallback_operation=_get_str_attr(
            policy,
            "fallback_operation",
            defaults.fallback_operation,
        ),
    )
    return enabled, resolved


def _get_str_attr(target: object, name: str, fallback: str) -> str:
    value = getattr(target, name, None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _get_optional_str_attr(
    target: object,
    name: str,
    fallback: str | None,
) -> str | None:
    value = getattr(target, name, None)
    if value is None:
        return fallback
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned if cleaned else fallback
    return fallback


def _get_bool_attr(target: object, name: str, fallback: bool) -> bool:
    value = getattr(target, name, None)
    return value if isinstance(value, bool) else fallback
