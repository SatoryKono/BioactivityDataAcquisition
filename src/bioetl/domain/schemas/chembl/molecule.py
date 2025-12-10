"""Pandera schema for normalized ChEMBL molecule table.

.. deprecated::
    This module is deprecated. Import from:
    ``bioetl.infrastructure.validation.schemas.chembl.molecule``
"""

# Re-export from infrastructure for backward compatibility
from bioetl.infrastructure.validation.schemas.chembl.molecule import (
    MoleculeTableSchema,
    OUTPUT_COLUMN_ORDER,
)

__all__ = ["MoleculeTableSchema", "OUTPUT_COLUMN_ORDER"]
