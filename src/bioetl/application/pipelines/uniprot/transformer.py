"""UniProt Protein Transformer."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class UniProtProteinTransformer(BaseTransformer):
    """Transformer for UniProt protein records."""

    def __init__(self, provider: str = "uniprot"):
        """Initialize UniProt protein transformer.

        Args:
            provider: Data provider identifier.

        """
        super().__init__(provider)

    async def _transform_impl(
        self,
        _context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw UniProt record to Silver format."""
        # Validate required field
        accession = self._get_required_field(record, "primaryAccession")

        normalized = {
            "accession": accession,
            "entry_name": record.get("uniProtkbId"),
            "protein_name": self._extract_protein_name(record),
            "gene_names": self._extract_gene_names(record),
            "organism_id": self._extract_nested(record, "organism.taxonId"),
            "sequence_length": self._extract_nested(record, "sequence.length"),
        }

        # Генерация entity_id согласно RULES.md §2.8
        entity_id = generate_entity_id(
            record={"accession": accession},
            provider=self.provider,
            id_field="accession",
        )
        normalized["entity_id"] = entity_id

        # Генерация content_hash согласно RULES.md §2.8.1
        content_hash = self.compute_content_hash(normalized, exclude_none=False)
        normalized["content_hash"] = content_hash

        return cast("SilverRecord", normalized)

    def _extract_protein_name(self, record: BronzeRecord) -> str | None:
        """Extract protein name using nested path extraction."""
        result = self._extract_nested(
            record,
            "proteinDescription.recommendedName.fullName.value",
        )
        return str(result) if result is not None else None

    def _extract_gene_names(self, record: BronzeRecord) -> list[str]:
        """Extract gene names from genes list."""
        names: list[str] = []
        genes = record.get("genes")
        if not genes or not isinstance(genes, list):
            return names

        for gene in genes:
            if not isinstance(gene, dict):
                continue
            gene_name = gene.get("geneName", {})
            if isinstance(gene_name, dict):
                name = gene_name.get("value")
                if name:
                    names.append(name)
        return names
