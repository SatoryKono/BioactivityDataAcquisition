"""Mixin for configuring fallback policy on provider adapters.

Extracts the common ``configure_fallback_policy()`` pattern shared by
CrossRef, UniProt, and OpenAlex adapters.  Concrete adapters supply
hookpoints (default config, normalize-id, extract-record-id,
fallback-handler) while the mixin owns the orchestration logic.
"""

from __future__ import annotations

__all__ = ["FallbackPolicyMixin"]

from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.common.composable_fallback import (
    ComposableFallbackDecorator,
    FallbackDecoratorConfig,
    resolve_fallback_policy,
)
from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
    DefaultFallbackExecution,
    ExtractRecordIdProtocol,
    FallbackFetchOrchestratorService,
    NormalizeIdProtocol,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.common.base_title_fallback import (
        BaseTitleFallbackHandler,
    )


class FallbackPolicyMixin:
    """Reusable mixin that builds a ``ComposableFallbackDecorator`` from hookpoints.

    Subclasses **MUST** implement the four abstract-style hookpoints listed
    below.  Optionally override ``_on_fallback_decorator_updated`` to
    propagate the new decorator to downstream components (e.g. fetch-flow).

    Required attributes on the host class (set before ``configure_fallback_policy``):
        _fallback_fetch_service: FallbackFetchOrchestratorService
        logger: LoggerPort
    """

    # -- hookpoints (MUST be implemented or set by the concrete adapter) ------

    def _get_default_fallback_config(self) -> FallbackDecoratorConfig:
        """Return provider-specific default ``FallbackDecoratorConfig``.

        Raises:
            NotImplementedError: When subclass does not override this hookpoint.
        """
        raise NotImplementedError  # pragma: no cover

    def _get_normalize_id_hook(self) -> NormalizeIdProtocol:
        """Return a callable that normalises an incoming filter-id string.

        Raises:
            NotImplementedError: When subclass does not override this hookpoint.
        """
        raise NotImplementedError  # pragma: no cover

    def _get_extract_record_id_hook(self) -> ExtractRecordIdProtocol:
        """Return a callable that extracts the record-id from a BronzeRecord.

        Raises:
            NotImplementedError: When subclass does not override this hookpoint.
        """
        raise NotImplementedError  # pragma: no cover

    def _get_fallback_handler(self, enabled: bool) -> BaseTitleFallbackHandler | None:
        """Return the fallback handler when *enabled*, or ``None``.

        The default implementation returns ``None`` (no title-fallback).
        Override in adapters that support title-based fallback.

        Args:
            enabled: Whether fallback is enabled by the resolved policy.

        Returns:
            A fallback handler instance, or None when fallback is disabled or
            unsupported by this provider.
        """
        return None

    def _on_fallback_decorator_updated(self) -> None:
        """Hook called after ``_fallback_decorator`` has been (re-)created.

        Override to propagate the new decorator to downstream components
        such as a fetch-flow object.  The default implementation is a no-op.
        """

    # -- public interface -----------------------------------------------------

    def configure_fallback_policy(self, policy: object | None) -> None:
        """Configure fallback decorator behavior from provider YAML policy.

        This is the single shared entry-point used by all three adapters
        (CrossRef, UniProt, OpenAlex).

        Args:
            policy: Raw policy object from provider YAML, or None for defaults.
        """
        enabled, config = resolve_fallback_policy(
            policy,
            defaults=self._get_default_fallback_config(),
            default_enabled=True,
        )
        strategy = DefaultFallbackExecution(
            normalize_id_hook=self._get_normalize_id_hook(),
            extract_record_id_hook=self._get_extract_record_id_hook(),
            fallback_handler_hook=self._get_fallback_handler(enabled),
        )
        fallback_fetch_service: FallbackFetchOrchestratorService = (
            self._fallback_fetch_service  # type: ignore[attr-defined]
        )
        self._fallback_decorator = ComposableFallbackDecorator(
            service=fallback_fetch_service,
            strategy=strategy,
            config=config,
            logger=self._logger,  # type: ignore[attr-defined]
        )
        self._on_fallback_decorator_updated()
