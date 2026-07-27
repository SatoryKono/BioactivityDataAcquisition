"""Internal fallback-policy hook mixin for the Semantic Scholar adapter."""

from __future__ import annotations

from typing import Protocol, cast

from bioetl.infrastructure.adapters.common import FallbackDecoratorConfig
from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
    ExtractRecordIdProtocol,
    NormalizeIdProtocol,
)
from bioetl.infrastructure.adapters.semanticscholar.fallback import (
    SemanticScholarTitleFallbackHandler,
)

__all__ = ["_SemanticScholarFallbackPolicyMixin"]


class _SupportsNormalizeDoi(Protocol):
    """Host contract for adapters exposing DOI normalization."""

    def _normalize_doi(self, value: str) -> str:
        """Normalize a DOI string for provider lookup consistency."""
        ...


_SEMANTICSCHOLAR_DEFAULT_FALLBACK_CONFIG = FallbackDecoratorConfig(
    supported_filter_field="doi",
    unsupported_filter_event="unsupported_filter_field_for_fallback",
    unsupported_filter_message=(
        "SemanticScholar fallback only supports 'doi' filtering, skipping"
    ),
    skip_on_unsupported_filter_field=True,
    primary_lookup_method="doi",
    trim_primary_ids_to_limit=False,
    fallback_operation="fetch_filtered_with_fallback",
)


class _SemanticScholarFallbackPolicyMixin:
    """Provider-specific hookpoints consumed by ``FallbackPolicyMixin``."""

    _fallback_handler: SemanticScholarTitleFallbackHandler

    def _get_default_fallback_config(self) -> FallbackDecoratorConfig:
        """Return Semantic Scholar-specific default fallback config."""
        return _SEMANTICSCHOLAR_DEFAULT_FALLBACK_CONFIG

    def _get_normalize_id_hook(self) -> NormalizeIdProtocol:
        """Return DOI normalization hook."""
        host = cast(_SupportsNormalizeDoi, self)
        return host._normalize_doi

    def _get_extract_record_id_hook(self) -> ExtractRecordIdProtocol:
        """Return hook extracting DOI from a Semantic Scholar record."""
        return lambda rec: str(rec.get("doi", ""))

    def _get_fallback_handler(
        self, enabled: bool
    ) -> SemanticScholarTitleFallbackHandler | None:
        """Return title fallback handler when enabled."""
        return self._fallback_handler if enabled else None
