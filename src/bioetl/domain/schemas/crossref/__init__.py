"""CrossRef Pandera schemas.

Contains validation schemas for CrossRef data entities.

Terminology:
- Uses "Publication" instead of CrossRef API term "Work" for Ubiquitous Language
- WorkSchema and WORK_TYPES are kept as deprecated aliases for backward compatibility
"""

from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.crossref.work import WORK_TYPES  # Deprecated alias
from bioetl.domain.schemas.crossref.work import WorkSchema  # Deprecated alias
from bioetl.domain.schemas.crossref.work import (
    PUBLICATION_TYPES,
    PublicationSchema,
)

__all__ = [
    "PUBLICATION_TYPES",
    "WORK_TYPES",
    "PublicationEnrichedSchema",
    "PublicationSchema",
    "WorkSchema",
]
