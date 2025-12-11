"""Schema registration utilities.

Architecture Note:
    - Domain field specifications: ``bioetl.domain.schemas.field_specs``
    - Pandera schemas: ``bioetl.infrastructure.validation.schemas.chembl``
"""

from __future__ import annotations

# Backward compatibility imports from domain definitions
from bioetl.domain.schemas.chembl.output_views import (
    ACTIVITY_OUTPUT_COLUMNS,
    ASSAY_OUTPUT_COLUMNS,
    CELL_OUTPUT_COLUMNS,
    MOLECULE_OUTPUT_COLUMNS,
    PUBLICATION_OUTPUT_COLUMNS,
    TARGET_OUTPUT_COLUMNS,
    TISSUE_OUTPUT_COLUMNS,
)

__all__ = [
    "ACTIVITY_OUTPUT_COLUMNS",
    "ASSAY_OUTPUT_COLUMNS",
    "CELL_OUTPUT_COLUMNS",
    "MOLECULE_OUTPUT_COLUMNS",
    "PUBLICATION_OUTPUT_COLUMNS",
    "TARGET_OUTPUT_COLUMNS",
    "TISSUE_OUTPUT_COLUMNS",
]
