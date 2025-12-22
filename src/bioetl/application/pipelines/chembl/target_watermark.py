"""ChEMBL Target Watermark Extractor.

Extracts watermark from target records.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.types import Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class TargetWatermarkExtractor:
    """Extracts watermark from ChEMBL target records."""

    def __init__(self, watermark_field: str | None = None):
        self.watermark_field = watermark_field

    def extract(self, _context: PipelineContext, record: dict[str, Any]) -> Watermark:
        """Extract watermark from record.

        Uses target_chembl_id as primary watermark identifier.
        """
        target_id = record.get("target_chembl_id")
        if target_id is not None:
            return Watermark.from_id(str(target_id))

        return Watermark.from_id("")
