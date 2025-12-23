"""UniProt Protein Pipeline Implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer
from bioetl.domain.types import BronzeRecord, SilverRecord

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class UniProtProteinPipeline(BasePipeline):
    """Pipeline for processing UniProt proteins."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._transformer = UniProtProteinTransformer(provider=self.provider)

    async def transform_bronze_to_silver(
        self, context: PipelineContext, record: BronzeRecord
    ) -> SilverRecord | None:
        """Transform raw UniProt record to Silver format."""
        return await self._transformer.transform(context, record)
