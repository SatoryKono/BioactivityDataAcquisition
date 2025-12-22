"""ChEMBL Molecule Watermark Extractor.

Extracts watermark from molecule records.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.types import Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class MoleculeWatermarkExtractor:
    """Extracts watermark from ChEMBL molecule records."""

    def __init__(self, watermark_field: str | None = None):
        self.watermark_field = watermark_field

    def extract(self, _context: PipelineContext, record: dict[str, Any]) -> Watermark:
        """Extract watermark from record.

        Uses molecule_chembl_id as primary watermark identifier.
        """
        molecule_id = record.get("molecule_chembl_id")
        if molecule_id is not None:
            return Watermark.from_id(str(molecule_id))

        return Watermark.from_id("")
