"""Common adapter utilities and base classes.

Provides shared functionality for infrastructure adapters.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.common.base_title_fallback import (
    BaseTitleFallbackHandler,
)
from bioetl.infrastructure.adapters.common.composable_fallback import (
    ComposableFallbackDecorator,
    FallbackDecoratorConfig,
    resolve_fallback_policy,
)
from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
    DefaultFallbackExecution,
    FallbackExecutionPort,
    FallbackFetchOrchestratorService,
    FallbackFetchRequest,
)
from bioetl.infrastructure.adapters.common.fallback_policy_mixin import (
    FallbackPolicyMixin,
)
from bioetl.infrastructure.adapters.common.fetch_retry_policy import (
    is_retry_exhausted_error,
    run_fetch_with_fallback_policy,
    split_filter_ids_for_fallback,
)
from bioetl.infrastructure.adapters.common.retry_reduction_policy import (
    run_retry_exhausted_recovery_policy,
)
from bioetl.infrastructure.adapters.common.source_metadata_capability import (
    SourceMetadataCollectorProtocol,
    clear_source_metadata_collector,
    consume_source_metadata,
    get_request_count,
)
from bioetl.infrastructure.adapters.common.title_matching import (
    normalize_title,
    titles_match,
)

__all__ = [
    "APIRequestCollector",
    "BaseTitleFallbackHandler",
    "ComposableFallbackDecorator",
    "DefaultFallbackExecution",
    "FallbackDecoratorConfig",
    "FallbackExecutionPort",
    "FallbackFetchOrchestratorService",
    "FallbackFetchRequest",
    "FallbackPolicyMixin",
    "SourceMetadataCollectorProtocol",
    "clear_source_metadata_collector",
    "consume_source_metadata",
    "get_request_count",
    "is_retry_exhausted_error",
    "normalize_title",
    "resolve_fallback_policy",
    "run_fetch_with_fallback_policy",
    "run_retry_exhausted_recovery_policy",
    "split_filter_ids_for_fallback",
    "titles_match",
]
