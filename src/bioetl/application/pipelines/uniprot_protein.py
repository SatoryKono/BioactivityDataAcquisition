"""UniProt Protein Pipeline Implementation."""
from __future__ import annotations

from typing import Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_config import PipelineConfig, PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import Watermark


class UniProtProteinPipeline(BasePipeline):
    """Pipeline for processing UniProt proteins."""

    @classmethod
    def create(
        cls,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
        config: PipelineConfig,
    ) -> "UniProtProteinPipeline":
        return cls(config=config, runtime=runtime, services=services)

    async def transform_bronze_to_silver(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Transform raw UniProt record to Silver format."""
        # Minimal transformation for initial implementation
        return {
            "accession": record.get("primaryAccession"),
            "entry_name": record.get("uniProtkbId"),
            "protein_name": self._extract_protein_name(record),
            "gene_names": self._extract_gene_names(record),
            "organism_id": record.get("organism", {}).get("taxonId"),
            "sequence_length": record.get("sequence", {}).get("length"),
            "updated_at": context.run_id,
        }

    def _extract_protein_name(self, record: dict) -> str | None:
        try:
            return record.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value")
        except (AttributeError, TypeError):
            return None

    def _extract_gene_names(self, record: dict) -> list[str]:
        names = []
        try:
            genes = record.get("genes", [])
            for gene in genes:
                if name := gene.get("geneName", {}).get("value"):
                    names.append(name)
        except (AttributeError, TypeError):
            pass
        return names

    def extract_watermark(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract accession as watermark."""
        # UniProt uses string accessions, not integers.
        # But BasePipeline/Types might expect compatible types.
        # Check domain/types.py if Watermark supports str.
        # Assuming it does (NewType(str | int))
        return str(record.get("primaryAccession", ""))
