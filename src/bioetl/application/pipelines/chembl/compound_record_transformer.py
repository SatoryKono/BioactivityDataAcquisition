"""ChEMBL Compound Record Transformer.

Transforms Bronze records to Silver format (CompoundRecord entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import CompoundRecord
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

    def _normalize_string(self, value: Any) -> str | None:
        """Normalize string by stripping whitespace, NULL if empty.

        Args:
            value: Raw string value from API.

        Returns:
            Stripped string or None if empty/None.

        """
        if value is None:
            return None
        str_value = str(value).strip()
        return str_value if str_value else None

    def _validate_positive_int(self, value: Any) -> int | None:
        """Validate integer is positive (>= 1) or return None.

        Args:
            value: Raw int value from API.

        Returns:
            Valid int (>= 1) or None.

        """
        int_value = safe_int(value)
        if int_value is not None and int_value < 1:
            return None
        return int_value

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract CompoundRecord business data from bronze record.

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
        molecule_chembl_id = self._normalize_string(record.get("molecule_chembl_id"))
        document_chembl_id = self._normalize_string(record.get("document_chembl_id"))

        return {
            # Primary identifier
            "record_id": record_id,
            # Foreign keys
            "molecule_chembl_id": molecule_chembl_id,
            "document_chembl_id": document_chembl_id,
            # Original compound names (strip whitespace, NULL if empty)
            "compound_key": self._normalize_string(record.get("compound_key")),
            "compound_name": self._normalize_string(record.get("compound_name")),
            # Source information
            "src_id": src_id,
            "src_compound_id": self._normalize_string(record.get("src_compound_id")),
        }
