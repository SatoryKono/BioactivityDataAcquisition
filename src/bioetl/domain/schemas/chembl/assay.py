"""Pandera schema for normalized ChEMBL assay table.

.. deprecated::
    This module is deprecated. Import from:
    ``bioetl.infrastructure.validation.schemas.chembl.assay``
"""

# Re-export from infrastructure for backward compatibility
from bioetl.infrastructure.validation.schemas.chembl.assay import (
    AssayTableSchema,
    OUTPUT_COLUMN_ORDER,
)

__all__ = ["AssayTableSchema", "OUTPUT_COLUMN_ORDER"]
