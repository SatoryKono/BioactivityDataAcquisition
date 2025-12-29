"""CrossRef Pandera schemas for Silver layer validation.

Entity-Relationship:
    CrossRefWork (1) ─┬── (N) CrossRefAuthor
                      ├── (N) CrossRefReference
                      └── (N) CrossRefFunder
"""

from bioetl.domain.schemas.crossref.author import AuthorSchema
from bioetl.domain.schemas.crossref.funder import FunderSchema
from bioetl.domain.schemas.crossref.reference import ReferenceSchema
from bioetl.domain.schemas.crossref.work import WorkSchema

__all__ = [
    "AuthorSchema",
    "FunderSchema",
    "ReferenceSchema",
    "WorkSchema",
]
