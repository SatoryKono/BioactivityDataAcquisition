"""PubMed pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the PubMed database.

Main Components:
- PubMedPublicationTransformer: Transformer for publication data
- PubMedPublicationsPipeline: Deprecated alias (use GenericPipeline)
"""

from __future__ import annotations

from bioetl.application.pipelines.compat import PubMedPublicationsPipeline
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer

__all__ = [
    "PubMedPublicationTransformer",
    # Deprecated
    "PubMedPublicationsPipeline",
]
