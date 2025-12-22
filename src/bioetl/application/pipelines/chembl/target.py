"""ChEMBL Target Pipeline.

Fetches biological targets from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Biological Targets (proteins, complexes, organisms)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.application.pipelines.chembl.target_watermark import (
    TargetWatermarkExtractor,
)
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.types import BronzeRecord, SilverRecord, Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class ChEMBLTargetPipeline(BasePipeline):
    """Pipeline for ChEMBL target data."""

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
    ) -> None:
        """Initialize pipeline with transformer and watermark extractor."""
        super().__init__(config, runtime, services)
        self._transformer = TargetTransformer(provider=self.provider)
        self._watermark_extractor = TargetWatermarkExtractor(
            watermark_field=self.config.watermark_field
        )

    async def transform_bronze_to_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL target to normalized format using Domain Entity."""
        return await self._transformer.transform(context, record)

    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)

    def extract_watermark(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract watermark and return Watermark wrapper."""
        return self._watermark_extractor.extract(context, record)
