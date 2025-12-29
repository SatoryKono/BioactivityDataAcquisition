"""ChEMBL Compound Record Transformer.

Transforms Bronze records to Silver format (CompoundRecord entity inflation).

Note: Business logic functions are delegated to domain layer per REFACTOR-004.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import CompoundRecord
from bioetl.domain.normalization import normalize_to_string
from bioetl.domain.transformations import safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class CompoundRecordTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze compound record data to silver.

    Compound records link molecules to documents and contain the original
    compound name as it appears in the publication.
    """

    entity_class = CompoundRecord
    primary_id_field = "record_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract CompoundRecord business data from bronze record.

        Delegates normalization to domain layer per REFACTOR-004.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated record_id value.

        Returns:
            Dictionary of CompoundRecord business fields.

        """
        # Get record_id as int
        record_id = safe_int(primary_id)

        # Get src_id - required field
        src_id = safe_int(record.get("src_id"))

        # Get molecule_chembl_id and document_chembl_id - required fields
        # Use domain normalization function
        molecule_chembl_id = normalize_to_string(record.get("molecule_chembl_id"))
        document_chembl_id = normalize_to_string(record.get("document_chembl_id"))

        return {
            # Primary identifier
            "record_id": record_id,
            # Foreign keys
            "molecule_chembl_id": molecule_chembl_id,
            "document_chembl_id": document_chembl_id,
            # Original compound names (strip whitespace, NULL if empty)
            "compound_key": normalize_to_string(record.get("compound_key")),
            "compound_name": normalize_to_string(record.get("compound_name")),
            # Source information
            "src_id": src_id,
            "src_compound_id": normalize_to_string(record.get("src_compound_id")),
        }
