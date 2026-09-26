# Host attrs/methods provided by concrete composition.
"""Internal fallback-policy hook mixin for the PubMed adapter."""

from __future__ import annotations

from typing import Any, cast

from bioetl.infrastructure.adapters.common import FallbackDecoratorConfig
from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
    ExtractRecordIdProtocol,
    NormalizeIdProtocol,
)
from bioetl.infrastructure.adapters.pubmed.fallback import PubMedTitleFallbackHandler

__all__ = ["_PubMedFallbackPolicyMixin"]

_PUBMED_DEFAULT_FALLBACK_CONFIG = FallbackDecoratorConfig(
    supported_filter_field=None,
    unsupported_filter_event="unsupported_filter_field_for_fallback",
    unsupported_filter_message=(
        "PubMed fallback accepts any field and resolves via PMID/title phases"
    ),
    skip_on_unsupported_filter_field=False,
    primary_lookup_method="pmid",
    trim_primary_ids_to_limit=False,
    fallback_operation="fetch_filtered_with_fallback",
)


class _PubMedFallbackPolicyMixin:
    """Provider-specific hookpoints consumed by ``FallbackPolicyMixin``."""

    _fallback_handler: PubMedTitleFallbackHandler = cast(
        Any, None
    )  # Any: host attr default (PD3)

    def _get_default_fallback_config(self) -> FallbackDecoratorConfig:
        """Return PubMed-specific default fallback config."""
        return _PUBMED_DEFAULT_FALLBACK_CONFIG

    def _get_normalize_id_hook(self) -> NormalizeIdProtocol:
        """Return PubMed ID normalization hook."""
        return lambda value: value.lower().strip()

    def _get_extract_record_id_hook(self) -> ExtractRecordIdProtocol:
        """Return hook extracting PMID from a PubMed record."""
        return lambda rec: str(rec.get("pmid", ""))

    def _get_fallback_handler(self, enabled: bool) -> PubMedTitleFallbackHandler | None:
        """Return title fallback handler when enabled."""
        return self._fallback_handler if enabled else None
