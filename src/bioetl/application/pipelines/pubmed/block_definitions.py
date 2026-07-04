"""Declarative block implementations for PubMed publication pipeline."""

from __future__ import annotations

from bioetl.application.pipelines.pubmed._block_definitions_analytics import (
    _PubMedClassificationBlock,
    _PubMedDateBlock,
    _PubMedMetricsBlock,
)
from bioetl.application.pipelines.pubmed._block_definitions_base import _PubMedXmlBlock
from bioetl.application.pipelines.pubmed._block_definitions_edition import (
    _PubMedAuthorBlock,
    _PubMedJournalBlock,
)
from bioetl.application.pipelines.pubmed._block_definitions_identifiers import (
    _PubMedCoreBlock,
    _PubMedIdentifierBlock,
)

__all__ = [
    "_PubMedAuthorBlock",
    "_PubMedClassificationBlock",
    "_PubMedCoreBlock",
    "_PubMedDateBlock",
    "_PubMedIdentifierBlock",
    "_PubMedJournalBlock",
    "_PubMedMetricsBlock",
    "_PubMedXmlBlock",
]
