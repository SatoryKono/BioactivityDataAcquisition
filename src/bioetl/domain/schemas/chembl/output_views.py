"""Output column descriptors for ChEMBL schemas."""

from __future__ import annotations

from bioetl.domain.schemas.chembl.activity import (
    OUTPUT_COLUMN_ORDER as ACTIVITY_OUTPUT_ORDER,
)
from bioetl.domain.schemas.chembl.assay import (
    OUTPUT_COLUMN_ORDER as ASSAY_OUTPUT_ORDER,
)
from bioetl.domain.schemas.chembl.cell import (
    OUTPUT_COLUMN_ORDER as CELL_OUTPUT_ORDER,
)
from bioetl.domain.schemas.chembl.molecule import (
    OUTPUT_COLUMN_ORDER as MOLECULE_OUTPUT_ORDER,
)
from bioetl.domain.schemas.chembl.publication import (
    OUTPUT_COLUMN_ORDER as PUBLICATION_OUTPUT_ORDER,
)
from bioetl.domain.schemas.chembl.target import (
    OUTPUT_COLUMN_ORDER as TARGET_OUTPUT_ORDER,
)
from bioetl.domain.schemas.chembl.tissue import (
    OUTPUT_COLUMN_ORDER as TISSUE_OUTPUT_ORDER,
)

ACTIVITY_OUTPUT_COLUMNS: list[str] = list(ACTIVITY_OUTPUT_ORDER)
ASSAY_OUTPUT_COLUMNS: list[str] = list(ASSAY_OUTPUT_ORDER)
CELL_OUTPUT_COLUMNS: list[str] = list(CELL_OUTPUT_ORDER)
MOLECULE_OUTPUT_COLUMNS: list[str] = list(MOLECULE_OUTPUT_ORDER)
PUBLICATION_OUTPUT_COLUMNS: list[str] = list(PUBLICATION_OUTPUT_ORDER)
TARGET_OUTPUT_COLUMNS: list[str] = list(TARGET_OUTPUT_ORDER)
TISSUE_OUTPUT_COLUMNS: list[str] = list(TISSUE_OUTPUT_ORDER)

__all__ = [
    "ACTIVITY_OUTPUT_COLUMNS",
    "ASSAY_OUTPUT_COLUMNS",
    "CELL_OUTPUT_COLUMNS",
    "MOLECULE_OUTPUT_COLUMNS",
    "PUBLICATION_OUTPUT_COLUMNS",
    "TARGET_OUTPUT_COLUMNS",
    "TISSUE_OUTPUT_COLUMNS",
]
