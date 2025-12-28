"""OpenAlex data source adapter package.

Provides adapter for fetching scholarly work data from OpenAlex API.
"""

from bioetl.infrastructure.adapters.openalex.abstract_parser import (
    estimate_abstract_length,
    reconstruct_abstract,
)
from bioetl.infrastructure.adapters.openalex.client import (
    OPENALEX_BASE_URL,
    OPENALEX_DEFAULT_PER_PAGE,
    OPENALEX_MAX_FILTER_IDS,
    OpenAlexAdapter,
)

__all__ = [
    "OPENALEX_BASE_URL",
    "OPENALEX_DEFAULT_PER_PAGE",
    "OPENALEX_MAX_FILTER_IDS",
    "OpenAlexAdapter",
    "estimate_abstract_length",
    "reconstruct_abstract",
]
