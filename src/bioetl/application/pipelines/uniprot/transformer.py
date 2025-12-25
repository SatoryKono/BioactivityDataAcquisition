"""UniProt Protein Transformer.

Transforms raw UniProt protein records into Silver-layer format using
the Protein domain entity for validation and invariant checking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    TransformationError,
)
from bioetl.domain.entities import Protein
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class UniProtProteinTransformer(BaseTransformer):
    """Transformer for UniProt protein records.

    Uses Protein domain entity for validation and lineage tracking.
    Records without required fields (accession, entry_name) are skipped.
    protein_name is optional and may be None.
    """

    def __init__(self, provider: str = "uniprot"):
        """Initialize UniProt protein transformer.

        Args:
            provider: Data provider identifier.

        """
        super().__init__(provider)

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw UniProt record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from UniProt.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            TransformationError: If required fields are missing.
            ValueError: If Protein entity validation fails.

        """
        # Step 1: Validate required fields
        accession = self._get_required_field(record, "primaryAccession")
        entry_name = self._get_entry_name(record)

        # Step 2: Build business data dictionary
        # protein_name is optional - may be None
        business_data: dict[str, Any] = {
            "accession": accession,
            "entry_name": entry_name,
            "protein_name": self._extract_protein_name(record),
            "gene_names": self._extract_gene_names(record),
            "organism_id": self._extract_nested(record, "organism.taxonId"),
            "sequence_length": self._extract_nested(record, "sequence.length"),
        }

        # Step 3: Generate entity_id (RULES.md §2.8)
        entity_id = generate_entity_id(
            record={"accession": accession},
            provider=self.provider,
            id_field="accession",
        )

        # Step 4: Compute content_hash (RULES.md §2.8.1)
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Step 5: Create domain entity with lineage metadata
        entity = self._create_entity(
            Protein,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            **business_data,
        )

        # Step 6: Convert to SilverRecord with lineage field renaming
        return cast("SilverRecord", self.entity_to_silver_record(entity))

    def _get_entry_name(self, record: BronzeRecord) -> str:
        """Extract entry name (uniProtkbId) as required field.

        Args:
            record: Bronze record dictionary.

        Returns:
            Entry name string.

        Raises:
            TransformationError: If entry_name is missing.

        """
        entry_name = record.get("uniProtkbId")
        if not entry_name:
            raise TransformationError(
                "Missing required field: uniProtkbId", field="uniProtkbId"
            )
        return str(entry_name)

    def _extract_protein_name(self, record: BronzeRecord) -> str | None:
        """Extract protein name (optional field).

        Args:
            record: Bronze record dictionary.

        Returns:
            Protein name string or None if not found.

        """
        protein_name = self._extract_nested(
            record,
            "proteinDescription.recommendedName.fullName.value",
        )
        return str(protein_name) if protein_name else None

    def _extract_gene_names(self, record: BronzeRecord) -> list[str]:
        """Extract gene names from genes list.

        Args:
            record: Bronze record dictionary.

        Returns:
            List of gene name strings.

        """
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
                    names.append(str(name))
        return names
