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
    """Пайплайн для данных о публикациях из PubMed.

    Transformer is injected via DI from GenericPipelineFactory.
    """

__all__ = [
    "PubMedPublicationPipeline",
    "PubMedPublicationTransformer",
]
