"""Pandera schema definitions for ChEMBL cell dimension.

.. deprecated::
    This module is deprecated. Import from:
    ``bioetl.infrastructure.validation.schemas.chembl.cell``
"""

# Re-export from infrastructure for backward compatibility
from bioetl.infrastructure.validation.schemas.chembl.cell import (
    CellTableSchema,
    OUTPUT_COLUMN_ORDER,
)

__all__ = ["CellTableSchema", "OUTPUT_COLUMN_ORDER"]
