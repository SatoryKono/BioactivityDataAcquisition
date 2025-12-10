"""Pandera schema for ChEMBL publication data.

.. deprecated::
    This module is deprecated. Import from:
    ``bioetl.infrastructure.validation.schemas.chembl.publication``
"""

# Re-export from infrastructure for backward compatibility
from bioetl.infrastructure.validation.schemas.chembl.publication import (
    PublicationTableSchema,
    OUTPUT_COLUMN_ORDER,
)

__all__ = ["PublicationTableSchema", "OUTPUT_COLUMN_ORDER"]
