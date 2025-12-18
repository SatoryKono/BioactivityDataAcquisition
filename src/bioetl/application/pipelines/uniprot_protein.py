"""UniProt Protein Pipeline Implementation."""
from __future__ import annotations

from typing import Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.domain.pipeline_config import PipelineConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import Watermark
from bioetl.domain.transformations import generate_entity_id, generate_content_hash


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
        accession = record.get("primaryAccession")
        if not accession:
            return None

        normalized = {
            "accession": accession,
            "entry_name": record.get("uniProtkbId"),
            "protein_name": self._extract_protein_name(record),
            "gene_names": self._extract_gene_names(record),
            "organism_id": record.get("organism", {}).get("taxonId"),
            "sequence_length": record.get("sequence", {}).get("length"),
        }

        # Генерация entity_id согласно RULES.md §2.8
        entity_id = generate_entity_id(
            record={"accession": accession},
            provider=self.provider,
            id_field="accession",
        )
        normalized["entity_id"] = entity_id

        # Генерация content_hash согласно RULES.md §2.8.1
        content_hash = generate_content_hash(normalized, self.provider)
        normalized["content_hash"] = content_hash

        return normalized

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
        return str(record.get("primaryAccession", ""))
