"""ChEMBL Assay Watermark Extractor.

Extracts watermark values from assay records for incremental processing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.types import Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class AssayWatermarkExtractor:
    """Extracts watermark from ChEMBL assay records."""

    def __init__(self, watermark_field: str | None = None):
        self.watermark_field = watermark_field

    def extract(self, _context: PipelineContext, record: dict[str, Any]) -> Watermark:
        """Extract watermark value from assay record.

        Args:
            _context: Pipeline context (unused but required by interface)
            record: Assay record dictionary

        Returns:
            Watermark containing the extracted value
        """
        # Primary: use assay_chembl_id
        assay_id = record.get("assay_chembl_id")
        if assay_id is not None:
            return Watermark.from_id(str(assay_id))

        # Fallback to configured watermark field
        fallback_field = self.watermark_field
        fallback_value = record.get(fallback_field) if fallback_field else None

        if fallback_value is None:
            return Watermark.from_id("")

        return Watermark.from_id(str(fallback_value))
