"""PubMed pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the PubMed database.

Main Components:
- PubMedPublicationPipeline: Pipeline for publication data
- PubMedPublicationTransformer: Transformer for publication data
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer


class PubMedPublicationPipeline(BasePipeline):
    """Pipeline for PubMed publication data.

    Transformer is injected via DI from GenericPipelineFactory.
    """


PIPELINES = (PubMedPublicationPipeline,)

__all__ = [
    "PubMedPublicationPipeline",
    "PubMedPublicationTransformer",
]
