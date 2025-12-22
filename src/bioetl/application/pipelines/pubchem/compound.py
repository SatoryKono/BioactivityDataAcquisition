"""PubChem Compound Pipeline Implementation."""

from __future__ import annotations

from typing import Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import BronzeRecord, SilverRecord, Watermark


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
        return self._transformer.transform(record)

    def extract_watermark(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract CID as watermark (обёртка Watermark)."""
        return Watermark.from_offset(int(record.get("cid", 0)))
