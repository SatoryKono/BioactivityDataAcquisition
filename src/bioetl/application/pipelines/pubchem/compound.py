"""PubChem Compound Pipeline Implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.domain.types import BronzeRecord, SilverRecord, Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class PubChemCompoundPipeline(BasePipeline):
    """Pipeline for processing PubChem compounds."""

    # create method removed (DRY)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._transformer = PubChemCompoundTransformer(provider=self.provider)

    async def transform_bronze_to_silver(
        self, context: PipelineContext, record: BronzeRecord
    ) -> SilverRecord | None:
        """Transform raw PubChem record to Silver format."""
        return await self._transformer.transform(context, record)

    def extract_watermark(
        self, _context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract CID as watermark (обёртка Watermark)."""
        return Watermark.from_offset(int(record.get("cid", 0)))
