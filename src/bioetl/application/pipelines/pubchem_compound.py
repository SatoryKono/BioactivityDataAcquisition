"""PubChem Compound Pipeline Implementation."""
from __future__ import annotations

from typing import Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_config import PipelineConfig, PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import Watermark


class PubChemCompoundPipeline(BasePipeline):
    """Pipeline for processing PubChem compounds."""

    @classmethod
    def create(
        cls,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
        config: PipelineConfig,
    ) -> "PubChemCompoundPipeline":
        return cls(config=config, runtime=runtime, services=services)

    async def transform_bronze_to_silver(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Transform raw PubChem record to Silver format."""
        # Minimal transformation for initial implementation
        return {
            "cid": record.get("cid"),
            "molecular_formula": record.get("molecular_formula"),
            "molecular_weight": record.get("molecular_weight"),
            "canonical_smiles": record.get("canonical_smiles"),
            "isomeric_smiles": record.get("isomeric_smiles"),
            "inchi": record.get("inchi"),
            "inchikey": record.get("inchikey"),
            "iupac_name": record.get("iupac_name"),
            "updated_at": context.run_id,  # Placeholder for actual update time
        }

    def extract_watermark(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract CID as watermark."""
        # Ensure watermark is int or str compatible
        return int(record.get("cid", 0))
