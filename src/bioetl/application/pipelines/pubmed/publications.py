# src/bioetl/application/pipelines/pubmed/publications.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.domain.types import Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class PubMedPublicationsPipeline(BasePipeline):
    """Пайплайн для данных о публикациях из PubMed."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._transformer = PubMedPublicationTransformer(provider=self.provider)

    async def transform_bronze_to_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Трансформирует сырую XML-запись в формат Silver."""
        return await self._transformer.transform(context, record)

    def extract_watermark(
        self, _context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract PMID as watermark."""
        pmid = record.get("pmid", "")
        return Watermark.from_id(str(pmid))
