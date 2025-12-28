"""CrossRef Pandera validation schemas.

Schemas for validating CrossRef API data in Silver layer.

Entity Relationships:
    CrossRefWork (1) ─┬── (N) CrossRefAuthor
                      ├── (N) CrossRefReference
                      └── (N) CrossRefFunder

Usage:
    from bioetl.domain.schemas.crossref import (
        CrossRefWorkSchema,
        CrossRefAuthorSchema,
        CrossRefReferenceSchema,
        CrossRefFunderSchema,
    )

    # Validate DataFrame
    validated_works = CrossRefWorkSchema.validate(works_df)
"""

from bioetl.domain.schemas.crossref.author import CrossRefAuthorSchema
from bioetl.domain.schemas.crossref.funder import CrossRefFunderSchema
from bioetl.domain.schemas.crossref.reference import CrossRefReferenceSchema
from bioetl.domain.schemas.crossref.work import CrossRefWorkSchema

__all__ = [
    "CrossRefAuthorSchema",
    "CrossRefFunderSchema",
    "CrossRefReferenceSchema",
    "CrossRefWorkSchema",
]
