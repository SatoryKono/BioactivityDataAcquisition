"""Common adapter utilities and base classes.

Provides shared functionality for infrastructure adapters.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.common.base_alternate_id_fallback import (
    BaseAlternateIdFallbackHandler,
)
from bioetl.infrastructure.adapters.common.base_title_fallback import (
    BaseTitleFallbackHandler,
)
from bioetl.infrastructure.adapters.common.title_matching import (
    normalize_title,
    titles_match,
)

__all__ = [
    "APIRequestCollector",
    "BaseAlternateIdFallbackHandler",
    "BaseTitleFallbackHandler",
    "normalize_title",
    "titles_match",
]
