"""Pandera schema definitions for ChEMBL tissue dimension.

.. deprecated::
    This module is deprecated. Import from:
    ``bioetl.infrastructure.validation.schemas.chembl.tissue``
"""

# Re-export from infrastructure for backward compatibility
from bioetl.infrastructure.validation.schemas.chembl.tissue import (
    TissueTableSchema,
    OUTPUT_COLUMN_ORDER,
)

__all__ = ["TissueTableSchema", "OUTPUT_COLUMN_ORDER"]
