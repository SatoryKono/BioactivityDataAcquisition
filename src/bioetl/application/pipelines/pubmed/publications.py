# src/bioetl/application/pipelines/pubmed/publications.py
"""PubMed Publications Pipeline.

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class PubMedPublicationsPipeline(BasePipeline):
    """Пайплайн для данных о публикациях из PubMed.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
