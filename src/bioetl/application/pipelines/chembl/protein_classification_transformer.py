"""ChEMBL Protein Classification Transformer.

Transforms Bronze records to Silver format (ProteinClassification entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import ProteinClassification
from bioetl.domain.transformations import safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class ProteinClassificationTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze protein classification records to silver.

    Protein classifications form a hierarchical tree (ChEMBL protein family tree).
    They are reference data used for target classification and filtering.
    Self-referential hierarchy via parent_id FK.
    """

    entity_class = ProteinClassification
    primary_id_field = "protein_class_id"

    def _normalize_text(self, value: Any) -> str | None:
        """Normalize text field by stripping whitespace, NULL if empty.

        Args:
            value: Raw text value from API.

        Returns:
            Stripped string or None if empty/None.

        """
        if value is None:
            return None
        str_value = str(value).strip()
        return str_value if str_value else None

    def _validate_class_level(self, value: Any) -> int | None:
        """Validate class level (must be 1-8 or NULL).

        Args:
            value: Raw class_level value from API.

        Returns:
            Valid class_level (1-8) or None.

        """
        level = safe_int(value)
        if level is not None and not (1 <= level <= 8):
            return None
        return level

    def _validate_parent_id(self, value: Any) -> int | None:
        """Validate parent_id (must be > 0 or NULL).

        Args:
            value: Raw parent_id value from API.

        Returns:
            Valid parent_id (>= 1) or None.

        """
        parent_id = safe_int(value)
        if parent_id is not None and parent_id < 1:
            return None
        return parent_id

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract ProteinClassification business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated protein_class_id value.

        Returns:
            Dictionary of ProteinClassification business fields.

        """
        return {
            # Primary identifier (convert to int)
            "protein_class_id": safe_int(primary_id),
            # Hierarchy information
            "parent_id": self._validate_parent_id(record.get("parent_id")),
            "class_level": self._validate_class_level(record.get("class_level")),
            # Core metadata (with strip normalization)
            "pref_name": self._normalize_text(record.get("pref_name")),
            "short_name": self._normalize_text(record.get("short_name")),
            "protein_class_desc": self._normalize_text(
                record.get("protein_class_desc")
            ),
            "definition": self._normalize_text(record.get("definition")),
        }
