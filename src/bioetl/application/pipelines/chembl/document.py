"""ChEMBL Document Pipeline.

Fetches scientific documents from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Scientific Documents (publications, patents)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.chembl.document_transformer import DocumentTransformer

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, RunID, SilverRecord


class ChEMBLDocumentPipeline(BasePipeline):
    """Pipeline for ChEMBL document data."""

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
        run_id: RunID,
    ) -> None:
        """Initialize pipeline with transformer."""
        super().__init__(config, runtime, services, run_id)
        self._transformer = DocumentTransformer(provider=self.provider)

    async def transform_bronze_to_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL document to normalized format using Domain Entity."""
        return await self._transformer.transform(context, record)

    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
