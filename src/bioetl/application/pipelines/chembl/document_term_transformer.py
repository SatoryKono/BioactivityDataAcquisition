"""ChEMBL Document Term Transformer.

Transforms Bronze records to Silver format (DocumentTerm entity inflation).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import DocumentTerm
from bioetl.domain.transformations import safe_float, safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class DocumentTermTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze document term records to silver.

    Document terms are keywords extracted from documents for text search.
    They have a composite key of (document_chembl_id, term).
    """

    entity_class = DocumentTerm
    primary_id_field = "document_chembl_id"

    def _normalize_term(self, value: Any) -> str | None:
        """Normalize term by stripping, lowercasing, and removing special chars.

        Args:
            value: Raw term value from API.

        Returns:
            Normalized term string or None if empty/None.

        """
        if value is None:
            return None
        str_value = str(value).strip().lower()
        # Remove leading/trailing special characters but keep internal ones
        str_value = re.sub(r"^[^\w]+|[^\w]+$", "", str_value)
        return str_value if str_value else None

    def _validate_frequency(self, value: Any) -> int | None:
        """Validate frequency (must be >= 1 or NULL).

        Args:
            value: Raw frequency value from API.

        Returns:
            Valid frequency (>= 1) or None.

        """
        freq = safe_int(value)
        if freq is not None and freq < 1:
            return None
        return freq

    def _validate_score(self, value: Any) -> float | None:
        """Validate score (must be >= 0 or NULL), round to 10 decimal places.

        Args:
            value: Raw score value from API.

        Returns:
            Valid score (>= 0) or None.

        """
        score = safe_float(value)
        if score is not None:
            if score < 0:
                return None
            # Round to 10 decimal places as per content hash normalization
            return round(score, 10)
        return None

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract DocumentTerm business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated document_chembl_id value.

        Returns:
            Dictionary of DocumentTerm business fields.

        """
        # Get and normalize term
        term = self._normalize_term(record.get("term"))

        # If term is None after normalization, this record is invalid
        # The entity will fail validation, which is the expected behavior
        if term is None:
            term = ""  # Will fail entity validation

        return {
            # Composite key fields
            "document_chembl_id": str(primary_id),
            "term": term,
            # Frequency metrics
            "term_frequency": self._validate_frequency(record.get("term_frequency")),
            "doc_frequency": self._validate_frequency(record.get("doc_frequency")),
            "score": self._validate_score(record.get("score")),
        }
