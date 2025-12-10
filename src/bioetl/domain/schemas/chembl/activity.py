"""Pandera schema for normalized ChEMBL activity table.

.. deprecated::
    This module is deprecated. Import from:
    ``bioetl.infrastructure.validation.schemas.chembl.activity``
"""

# Re-export from infrastructure for backward compatibility
from bioetl.infrastructure.validation.schemas.chembl.activity import (
    ActivityTableSchema,
    OUTPUT_COLUMN_ORDER,
)

__all__ = ["ActivityTableSchema", "OUTPUT_COLUMN_ORDER"]
