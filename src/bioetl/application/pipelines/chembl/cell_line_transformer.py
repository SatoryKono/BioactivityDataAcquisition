"""ChEMBL Cell Line Transformer.

Transforms Bronze records to Silver format (CellLine entity inflation).

Note: Business logic functions are delegated to domain layer per REFACTOR-004.
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = ["CellLineTransformer"]


from typing import TYPE_CHECKING, cast

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import CellLine
from bioetl.domain.value_objects.taxonomy_id import TaxonomyId

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord, PrimaryId


class CellLineTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze cell line records to silver.

    Cell lines are biological objects used for in vitro experiments.
    They have M:N relationship with Assay (via assay.cell_chembl_id FK).
    """

    entity_class = CellLine
    primary_id_field = "cell_id"

    def _prepare_record(
        self,
        record: BronzeRecord,
    ) -> BronzeRecord:
        """Map cell_chembl_id → cell_id for Silver layer.

        ChEMBL API returns both cell_id (numeric internal ID like 449)
        and cell_chembl_id (CHEMBL ID like CHEMBL3308072). Silver uses
        cell_chembl_id as the canonical cell_id.
        """
        if record.get("cell_chembl_id") is not None:
            record = dict(record)
            record["cell_id"] = record["cell_chembl_id"]
        return record

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> JsonDict:  # Any: transformer record has heterogeneous values
        """Extract CellLine business data from bronze record.

        Delegates normalization/validation to domain layer per REFACTOR-004.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated cell_id value.

        Returns:
            Dictionary of CellLine business fields.

        """
        normalizer = self._data_normalizer

        # Get cell_name with strip normalization using DI service
        cell_name = normalizer.normalize_to_string(record.get("cell_name"))

        # Validate taxonomy_id using TaxonomyId Value Object
        raw_tax_id = record.get("cell_source_tax_id")
        taxonomy_id_vo = TaxonomyId.from_raw(
            cast("str | int | None", raw_tax_id) if raw_tax_id is not None else None
        )
        cell_source_taxonomy_id = taxonomy_id_vo.value if taxonomy_id_vo else None

        return {
            # Primary identifier
            "cell_id": str(primary_id),
            # Core metadata
            "cell_name": cell_name,
            "cell_description": record.get("cell_description"),
            # Source information
            "cell_source_tissue": record.get("cell_source_tissue"),
            "cell_source_organism": record.get("cell_source_organism"),
            # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
            "cell_source_taxonomy_id": cell_source_taxonomy_id,
            # Cell type classification
            "cell_type": normalizer.normalize_to_string(record.get("cell_type")),
            # External identifiers (strip, NULL if empty) using DI normalization
            "cellosaurus_id": normalizer.normalize_to_string(
                record.get("cellosaurus_id")
            ),
            "clo_id": normalizer.normalize_to_string(record.get("clo_id")),
            "clo_iri": None,
            "clo_mapping_status": None,
            "clo_ontology_version": None,
            "cl_lincs_id": normalizer.normalize_to_string(record.get("cl_lincs_id")),
            "efo_id": normalizer.normalize_to_string(record.get("efo_id")),
            "efo_iri": None,
            "efo_mapping_status": None,
            "efo_ontology_version": None,
        }
