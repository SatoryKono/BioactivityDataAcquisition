"""UniProt Protein Pipeline Implementation."""
from __future__ import annotations

from typing import Any, cast

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.domain.pipeline_config import PipelineConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import BronzeRecord, SilverRecord, Watermark
from bioetl.domain.transformations import generate_entity_id, generate_content_hash


class UniProtProteinPipeline(BasePipeline):
    """Pipeline for processing UniProt proteins."""

    # create method removed (DRY)

    async def transform_bronze_to_silver(
        self, context: PipelineContext, record: BronzeRecord
    ) -> SilverRecord | None:
        """Transform raw UniProt record to Silver format."""
        accession = record.get("primaryAccession")
        if not accession:
            return None

        # Helper variables for safe access
        organism = cast(dict[str, Any], record.get("organism", {}))
        sequence = cast(dict[str, Any], record.get("sequence", {}))

        normalized = {
            "accession": accession,
            "entry_name": record.get("uniProtkbId"),
            "protein_name": self._extract_protein_name(record),
            "gene_names": self._extract_gene_names(record),
            "organism_id": organism.get("taxonId"),
            "sequence_length": sequence.get("length"),
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

        return cast(SilverRecord, normalized)

    def _extract_protein_name(self, record: BronzeRecord) -> str | None:
        try:
            desc = cast(dict[str, Any], record.get("proteinDescription", {}))
            rec_name = desc.get("recommendedName", {})
            full_name = rec_name.get("fullName", {})
            return cast(str | None, full_name.get("value"))
        except (AttributeError, TypeError):
            return None

    def _extract_gene_names(self, record: BronzeRecord) -> list[str]:
        names = []
        try:
            genes = cast(list[dict[str, Any]], record.get("genes", []))
            for gene in genes:
                gene_name = gene.get("geneName", {})
                if name := gene_name.get("value"):
                    names.append(name)
        except (AttributeError, TypeError):
            pass
        return names

    def extract_watermark(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract accession as watermark."""
        return Watermark.from_id(str(record.get("primaryAccession", "")))
