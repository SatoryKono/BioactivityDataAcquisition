# Host attrs assigned in CrossRefAdapter.__post_init__ (PD4).
"""Internal fallback-policy hook mixin for the CrossRef adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

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

    # PD3 host attrs: annotations only. Avoid class-level ``None`` defaults —
    # ``hasattr(self, "_fetch_flow")`` would be True before ``__post_init__``
    # assigns the real CrossRefFetchFlow instance.
    _fallback_handler: CrossRefTitleFallbackHandler = cast(
        Any, None
    )  # Any: host attr default (PD6)
    _fallback_decorator: ComposableFallbackDecorator | None = cast(
        Any, None
    )  # Any: host attr default (PD6)
    _fetch_flow: CrossRefFetchFlow | None = cast(
        Any, None
    )  # Any: host attr default (PD6)

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
        """Propagate new decorator to the fetch-flow component.

        ``configure_fallback_policy`` runs during construction *before*
        ``_fetch_flow`` is built. Skip propagation until the flow exists.
        """
        fetch_flow = getattr(self, "_fetch_flow", None)
        if fetch_flow is None:
            return
        fetch_flow.fallback_decorator = self._fallback_decorator
