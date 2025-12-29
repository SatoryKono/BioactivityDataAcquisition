"""ChEMBL Cell Line Transformer.

Transforms Bronze records to Silver format (CellLine entity inflation).

Note: Business logic functions are delegated to domain layer per REFACTOR-004.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import CellLine
from bioetl.domain.normalization import normalize_to_string
from bioetl.domain.validation import validate_positive_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class CellLineTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze cell line records to silver.

    Cell lines are biological objects used for in vitro experiments.
    They have M:N relationship with Assay (via assay.cell_chembl_id FK).
    """

    entity_class = CellLine
    primary_id_field = "cell_chembl_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract CellLine business data from bronze record.

        Delegates normalization/validation to domain layer per REFACTOR-004.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated cell_chembl_id value.

        Returns:
            Dictionary of CellLine business fields.

        """
        # Get cell_name with strip normalization using domain function
        cell_name = normalize_to_string(record.get("cell_name"))

        return {
            # Primary identifier
            "cell_chembl_id": str(primary_id),
            # Core metadata
            "cell_name": cell_name,
            "cell_description": record.get("cell_description"),
            # Source information
            "cell_source_tissue": record.get("cell_source_tissue"),
            "cell_source_organism": record.get("cell_source_organism"),
            # Use domain validation for tax_id (must be positive)
            "cell_source_tax_id": validate_positive_int(
                record.get("cell_source_tax_id")
            ),
            # External identifiers (strip, NULL if empty) using domain normalization
            "cellosaurus_id": normalize_to_string(record.get("cellosaurus_id")),
            "cl_lincs_id": normalize_to_string(record.get("cl_lincs_id")),
            "efo_id": normalize_to_string(record.get("efo_id")),
        }
