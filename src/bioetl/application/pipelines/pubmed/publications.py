# src/bioetl/application/pipelines/pubmed/publications.py
from __future__ import annotations

from typing import TYPE_CHECKING, Type

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer

if TYPE_CHECKING:
    pass


class PubMedPublicationsPipeline(BasePipeline[PubMedPublicationTransformer]):
    """Пайплайн для данных о публикациях из PubMed."""

    @property
    def transformer_class(self) -> Type[PubMedPublicationTransformer]:
        return PubMedPublicationTransformer
