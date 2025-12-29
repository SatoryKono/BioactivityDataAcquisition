"""ChEMBL Cell Line Transformer.

Transforms Bronze records to Silver format (CellLine entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import CellLine
from bioetl.domain.transformations import safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class CellLineTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze cell line records to silver.

    Cell lines are biological objects used for in vitro experiments.
    They have M:N relationship with Assay (via assay.cell_chembl_id FK).
    """

    entity_class = CellLine
    primary_id_field = "cell_chembl_id"

    def _normalize_external_id(self, value: Any) -> str | None:
        """Normalize external ID by stripping whitespace, NULL if empty.

        Args:
            value: Raw external ID value from API.

        Returns:
            Stripped string or None if empty/None.

        """
        if value is None:
            return None
        str_value = str(value).strip()
        return str_value if str_value else None

    def _validate_tax_id(self, value: Any) -> int | None:
        """Validate taxonomy ID (must be > 0 or NULL).

        Args:
            value: Raw tax_id value from API.

        Returns:
            Valid tax_id (>= 1) or None.

        """
        tax_id = safe_int(value)
        if tax_id is not None and tax_id < 1:
            return None
        return tax_id

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract CellLine business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated cell_chembl_id value.

        Returns:
            Dictionary of CellLine business fields.

        """
        # Get cell_name with strip and lowercase normalization for comparison
        cell_name = record.get("cell_name")
        if cell_name is not None:
            cell_name = str(cell_name).strip()

        return {
            # Primary identifier
            "cell_chembl_id": str(primary_id),
            # Core metadata
            "cell_name": cell_name,
            "cell_description": record.get("cell_description"),
            # Source information
            "cell_source_tissue": record.get("cell_source_tissue"),
            "cell_source_organism": record.get("cell_source_organism"),
            "cell_source_tax_id": self._validate_tax_id(
                record.get("cell_source_tax_id")
            ),
            # External identifiers (strip, NULL if empty)
            "cellosaurus_id": self._normalize_external_id(
                record.get("cellosaurus_id")
            ),
            "cl_lincs_id": self._normalize_external_id(record.get("cl_lincs_id")),
            "efo_id": self._normalize_external_id(record.get("efo_id")),
        }
