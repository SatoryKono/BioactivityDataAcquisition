"""Common publication schemas shared across providers.

Provides:
- PublicationBaseSchema: Base schema for all publication entities
- LOOKUP_METHODS: Valid lookup method values
"""

from __future__ import annotations

from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
    PublicationBaseSchema,
)

__all__ = ["LOOKUP_METHODS", "PublicationBaseSchema"]
