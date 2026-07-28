# Host attrs/methods provided by concrete composition.
"""Internal fallback-policy hook mixin for the CrossRef adapter."""

from __future__ import annotations

from typing import Any, cast, TYPE_CHECKING

from bioetl.domain.normalization import normalize_doi
from bioetl.infrastructure.adapters.common import FallbackDecoratorConfig
from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
    ExtractRecordIdProtocol,
    NormalizeIdProtocol,
)
from bioetl.infrastructure.adapters.crossref._defaults import (
    CROSSREF_DEFAULT_FALLBACK_CONFIG as _CROSSREF_DEFAULT_FALLBACK_CONFIG,
)
from bioetl.infrastructure.adapters.crossref.fallback import (
    CrossRefTitleFallbackHandler,
)

__all__ = ["_CrossRefFallbackPolicyMixin"]

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.common import ComposableFallbackDecorator
    from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow


class _CrossRefFallbackPolicyMixin:
    """Provider-specific hookpoints consumed by ``FallbackPolicyMixin``."""

    _fallback_handler: CrossRefTitleFallbackHandler = cast(Any, None)  # Any: host attr default (PD3)
    _fallback_decorator: ComposableFallbackDecorator = cast(Any, None)  # Any: host attr default (PD3)
    _fetch_flow: CrossRefFetchFlow = cast(Any, None)  # Any: host attr default (PD3)

    def _get_default_fallback_config(self) -> FallbackDecoratorConfig:
        """Return CrossRef-specific default fallback config."""
        return _CROSSREF_DEFAULT_FALLBACK_CONFIG

    def _get_normalize_id_hook(self) -> NormalizeIdProtocol:
        """Return DOI normalization hook."""
        return lambda value: normalize_doi(value)

    def _get_extract_record_id_hook(self) -> ExtractRecordIdProtocol:
        """Return hook extracting DOI from a CrossRef record."""
        return lambda rec: str(rec.get("DOI", ""))

    def _get_fallback_handler(
        self, enabled: bool
    ) -> CrossRefTitleFallbackHandler | None:
        """Return title fallback handler when enabled."""
        return self._fallback_handler if enabled else None

    def _on_fallback_decorator_updated(self) -> None:
        """Propagate new decorator to the fetch-flow component."""
        if hasattr(self, "_fetch_flow"):
            self._fetch_flow.fallback_decorator = self._fallback_decorator
