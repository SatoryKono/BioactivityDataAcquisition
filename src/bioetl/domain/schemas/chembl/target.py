"""Pandera schema for ChEMBL target data.

.. deprecated::
    This module is deprecated. Import from:
    ``bioetl.infrastructure.validation.schemas.chembl.target``
"""

# Re-export from infrastructure for backward compatibility
from bioetl.infrastructure.validation.schemas.chembl.target import (
    TargetTableSchema,
    OUTPUT_COLUMN_ORDER,
)

__all__ = ["TargetTableSchema", "OUTPUT_COLUMN_ORDER"]
