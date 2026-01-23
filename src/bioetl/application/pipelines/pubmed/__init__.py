"""PubMed pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the PubMed database.

Main Components:
- PubMedPublicationPipeline: Pipeline for publication data
- PubMedPublicationTransformer: Transformer for publication data
"""

from __future__ import annotations

from bioetl.application.pipelines.pubmed.publication import PubMedPublicationPipeline
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer

__all__ = [
    "PubMedPublicationPipeline",
    "PubMedPublicationTransformer",
]
