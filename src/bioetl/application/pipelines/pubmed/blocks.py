"""Declarative extraction blocks for PubMed publication pipeline."""

from __future__ import annotations

from bioetl.application.pipelines.pubmed.block_definitions import (
    _PubMedAuthorBlock,
    _PubMedClassificationBlock,
    _PubMedCoreBlock,
    _PubMedDateBlock,
    _PubMedIdentifierBlock,
    _PubMedJournalBlock,
    _PubMedMetricsBlock,
    _PubMedXmlBlock,
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
