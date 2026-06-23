"""Specialized application-core data-source wrappers.

This package groups source wrappers and specialty sources that would otherwise
inflate the top-level ``application.core`` namespace. Legacy flat modules remain
as compatibility facades.
"""

from __future__ import annotations

from bioetl.application.core.data_sources.filtered import FilteredDataSource
from bioetl.application.core.data_sources.idmapping import IDMappingDataSource
from bioetl.application.core.data_sources.publication_term import (
    PublicationTermDataSource,
)
from bioetl.application.core.data_sources.subcellular_fraction import (
    SubcellularFractionDataSource,
)

__all__ = [
    "FilteredDataSource",
    "IDMappingDataSource",
    "PublicationTermDataSource",
    "SubcellularFractionDataSource",
]
