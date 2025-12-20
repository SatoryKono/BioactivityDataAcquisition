"""ChEMBL Activity Pipeline.

Fetches bioactivity data from ChEMBL database and processes it through
Bronze → Silver → Gold layers.

Entity: Bioactivity measurements (IC50, Ki, EC50, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.pipelines.chembl.activity_filter import ActivityGoldFilter
from bioetl.application.pipelines.chembl.activity_transformer import ActivityTransformer
from bioetl.application.pipelines.chembl.activity_watermark import (
    ActivityWatermarkExtractor,
)
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.types import BronzeRecord, SilverRecord, Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class ChEMBLActivityPipeline(BasePipeline):
    """Pipeline for ChEMBL bioactivity data."""

    def __init__(
        self,
        config: PipelineConfig,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
    ) -> None:
        """Initialize pipeline and pre-compute filter sets."""
        super().__init__(config, runtime, services)
        self._transformer = ActivityTransformer(provider=self.provider)
        self._gold_filter = ActivityGoldFilter(preferred_types=self.config.gold_filter_types)
        self._watermark_extractor = ActivityWatermarkExtractor(watermark_field=self.config.watermark_field)

    async def transform_bronze_to_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL activity to normalized format using Domain Entity."""
        return await self._transformer.transform(context, record)

    def should_write_gold(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> bool:
        """Filter records for Gold layer."""
        return self._gold_filter.should_include(context, record)

    def extract_watermark(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract watermark and return Watermark wrapper."""
        return self._watermark_extractor.extract(context, record)
