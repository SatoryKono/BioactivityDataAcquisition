# src/bioetl/application/pipelines/pubmed/publications.py
"""PubMed Publications Pipeline.

Refactored: Uses default_transformer_class for fallback (eliminates __init__ boilerplate).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer


class PubMedPublicationsPipeline(BasePipeline):
    """Пайплайн для данных о публикациях из PubMed.

    Transformer is injected via DI from GenericPipelineFactory.
    Falls back to PubMedPublicationTransformer if not injected.
    """

    default_transformer_class = PubMedPublicationTransformer

    # transform_bronze_to_silver() is inherited from BasePipeline
