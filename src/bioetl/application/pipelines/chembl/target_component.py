"""ChEMBL Target Component Pipeline.

Fetches target components from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Target Components (protein sequences, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class ChEMBLTargetComponentPipeline(BasePipeline):
    """Pipeline for ChEMBL target component data."""

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
    ) -> None:
        """Initialize pipeline with transformer."""
        super().__init__(config, runtime, services)
        self._transformer = TargetComponentTransformer(provider=self.provider)

    async def transform_bronze_to_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL target component to normalized format using Domain Entity."""
        return await self._transformer.transform(context, record)

    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
