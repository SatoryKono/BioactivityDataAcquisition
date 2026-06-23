"""CrossRef Pandera schemas.

Contains validation schemas for CrossRef data entities.

Terminology:
- Uses "Publication" instead of CrossRef API term "Work" for Ubiquitous Language
"""

from __future__ import annotations

from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.crossref.work import (
    PUBLICATION_TYPES,
    PublicationSchema,
)

__all__ = [
    "PUBLICATION_TYPES",
    "PublicationEnrichedSchema",
    "PublicationSchema",
]
