"""OpenAlex data source adapter package.

Implements FilterableDataSourcePort for batch DOI resolution with title fallback.
"""

from bioetl.infrastructure.adapters.openalex.client import (
    OpenAlexAdapter,
    _create_openalex_adapter,
)

__all__ = ["OpenAlexAdapter", "_create_openalex_adapter"]
