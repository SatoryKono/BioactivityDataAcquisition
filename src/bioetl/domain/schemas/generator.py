"""Helpers for generating Pandera schemas from column descriptors.

.. deprecated::
    This module is deprecated. Import from:
    ``bioetl.infrastructure.validation.schemas.generator``
"""

# Re-export from infrastructure for backward compatibility
from bioetl.infrastructure.validation.schemas.generator import (
    generate_schema_from_column_order,
    load_column_order_from_yaml,
)

__all__ = [
    "generate_schema_from_column_order",
    "load_column_order_from_yaml",
]
