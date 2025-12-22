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

    def __init__(self, watermark_field: str = "assay_chembl_id"):
        self.watermark_field = watermark_field

    def extract(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract watermark value from assay record.

        Args:
            context: Pipeline context (unused but required by interface)
            record: Assay record dictionary

        Returns:
            Watermark containing the extracted value
        """
        value = record.get(self.watermark_field)
        return Watermark(value=value)
