"""ChEMBL Document Watermark Extractor.

Extracts watermark from document records.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.types import Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class DocumentWatermarkExtractor:
    """Extracts watermark from ChEMBL document records."""

    def __init__(self, watermark_field: str | None = None):
        self.watermark_field = watermark_field

    def extract(self, _context: PipelineContext, record: dict[str, Any]) -> Watermark:
        """Extract watermark from record.

        Uses document_chembl_id as primary watermark identifier.
        """
        document_id = record.get("document_chembl_id")
        if document_id is not None:
            return Watermark.from_id(str(document_id))

        return Watermark.from_id("")
