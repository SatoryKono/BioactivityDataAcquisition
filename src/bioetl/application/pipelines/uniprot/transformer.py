"""UniProt Protein Transformer."""

from __future__ import annotations

from typing import Any, cast

from bioetl.domain.transformations import generate_content_hash, generate_entity_id
from bioetl.domain.types import BronzeRecord, SilverRecord


class UniProtProteinTransformer:
    """Transformer for UniProt protein records."""

    def __init__(self, provider: str = "uniprot"):
        self.provider = provider

    def transform(self, record: BronzeRecord) -> SilverRecord | None:
        """Transform raw UniProt record to Silver format."""
        accession = record.get("primaryAccession")
        if not accession:
            return None

        # Helper variables for safe access (handle explicit None values)
        organism = record.get("organism") or {}
        sequence = record.get("sequence") or {}

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

        return cast("SilverRecord", normalized)

    def _extract_protein_name(self, record: BronzeRecord) -> str | None:
        try:
            desc = cast("dict[str, Any]", record.get("proteinDescription", {}))
            rec_name = desc.get("recommendedName", {})
            full_name = rec_name.get("fullName", {})
            return cast("str | None", full_name.get("value"))
        except (AttributeError, TypeError):
            return None

    def _extract_gene_names(self, record: BronzeRecord) -> list[str]:
        names = []
        try:
            genes = cast("list[dict[str, Any]]", record.get("genes", []))
            for gene in genes:
                gene_name = gene.get("geneName", {})
                if name := gene_name.get("value"):
                    names.append(name)
        except (AttributeError, TypeError):
            pass
        return names
