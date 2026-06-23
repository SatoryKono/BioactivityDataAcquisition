"""Common schemas shared across providers.

Provides:
- PublicationBaseSchema: Base schema for all publication entities
- MoleculeBaseSchema: Base schema for all molecule/compound entities
- LOOKUP_METHODS: Valid lookup method values
"""

from __future__ import annotations

from bioetl.domain.schemas.common.molecule_base import MoleculeBaseSchema
from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
    PublicationBaseSchema,
)

__all__ = ["LOOKUP_METHODS", "MoleculeBaseSchema", "PublicationBaseSchema"]
