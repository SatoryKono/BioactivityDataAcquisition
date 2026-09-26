"""OpenAlex data source adapter package.

Implements FilterableDataSourcePort for batch DOI resolution with title fallback.
"""

# pyright: reportImportCycles=false
from __future__ import annotations

from bioetl.infrastructure.adapters.openalex.client import OpenAlexAdapter

__all__ = ["OpenAlexAdapter"]
