"""PubMed pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the PubMed database.

Main Components:
- PubMedPublicationsPipeline: Pipeline for publication data
- PubMedPublicationTransformer: Transformer for publication data
"""

from __future__ import annotations

from bioetl.application.pipelines.pubmed.publications import PubMedPublicationsPipeline
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer

__all__ = [
    "PubMedPublicationTransformer",
    "PubMedPublicationsPipeline",
]
