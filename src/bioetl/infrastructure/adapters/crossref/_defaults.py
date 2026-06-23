"""CrossRef adapter default wiring helpers."""

from __future__ import annotations

from bioetl.infrastructure.adapters.common import FallbackDecoratorConfig
from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_error_handler as create_default_crossref_error_handler,
)
from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_fallback_service as create_default_crossref_fallback_service,
)

__all__ = [
    "CROSSREF_DEFAULT_FALLBACK_CONFIG",
    "create_default_crossref_error_handler",
    "create_default_crossref_fallback_service",
]

CROSSREF_DEFAULT_FALLBACK_CONFIG = FallbackDecoratorConfig(
    supported_filter_field="doi",
    unsupported_filter_event="unsupported_filter_field_for_fallback",
    unsupported_filter_message=(
        "CrossRef fallback only supports 'doi' filtering, proceeding with DOI semantics"
    ),
    skip_on_unsupported_filter_field=False,
    primary_lookup_method="doi",
    trim_primary_ids_to_limit=True,
    fallback_operation="fetch_filtered_with_fallback",
)
