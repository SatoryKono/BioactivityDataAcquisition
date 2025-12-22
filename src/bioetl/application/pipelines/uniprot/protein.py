"""UniProt Protein Pipeline Implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer
from bioetl.domain.types import BronzeRecord, SilverRecord, Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class UniProtProteinPipeline(BasePipeline):
    """Pipeline for processing UniProt proteins."""

    # create method removed (DRY)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._transformer = UniProtProteinTransformer(provider=self.provider)

    async def transform_bronze_to_silver(
        self, context: PipelineContext, record: BronzeRecord
    ) -> SilverRecord | None:
        """Transform raw UniProt record to Silver format."""
        return await self._transformer.transform(context, record)

    def extract_watermark(
        self, _context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract watermark as accession string wrapped in Watermark."""
        accession = str(record.get("primaryAccession", ""))
        return Watermark.from_id(accession)
