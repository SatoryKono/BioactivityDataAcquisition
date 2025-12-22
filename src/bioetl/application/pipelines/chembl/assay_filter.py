"""ChEMBL Assay Gold Filter.

Filters assay records for Gold layer based on quality criteria.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class AssayGoldFilter:
    """Filters ChEMBL assay records for Gold layer.

    Filters by:
    - assay_type: B (Binding), F (Functional), A (ADMET), etc.
    - confidence_score: Minimum confidence threshold

    Args:
        preferred_types: List of assay types to include (e.g., ["B", "F"])
        min_confidence: Minimum confidence score (0-9, default 4)
    """

    def __init__(
        self,
        preferred_types: list[str] | None = None,
        min_confidence: int = 4,
    ):
        self.preferred_types = set(preferred_types) if preferred_types else None
        self.min_confidence = min_confidence

    def should_include(
        self, _context: PipelineContext, record: dict[str, Any]
    ) -> bool:
        """Determine if assay record should be included in Gold layer.

        Args:
            context: Pipeline context (unused but required by interface)
            record: Assay record dictionary

        Returns:
            True if record passes all filter criteria
        """
        # Filter by assay type if specified
        if self.preferred_types:
            assay_type = record.get("assay_type")
            if assay_type not in self.preferred_types:
                return False

        # Filter by confidence score
        confidence_score = record.get("confidence_score")
        if confidence_score is not None:
            try:
                if int(confidence_score) < self.min_confidence:
                    return False
            except (ValueError, TypeError):
                # Invalid confidence score - exclude from Gold
                return False

        return True
