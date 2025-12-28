"""Pandera schemas for Semantic Scholar entities.

Provides validation schemas for:
- PaperSchema: Scientific publications with citation graph and embeddings
- AuthorSchema: Researcher profiles with metrics
- PaperAuthorSchema: Paper-Author M:N junction
- CitationSchema: Citation graph edges

Entity-Relationship:
    Paper (M) -- (N) Author  (via PaperAuthor)
    Paper (1) -- (N) Citation  (citing or cited)

Example:
    >>> from bioetl.domain.schemas.semantic_scholar import (
    ...     PaperSchema,
    ...     AuthorSchema,
    ...     CitationSchema,
    ... )
    >>> validated_papers = PaperSchema.validate(papers_df)
"""
from bioetl.domain.schemas.semantic_scholar.author import AuthorSchema
from bioetl.domain.schemas.semantic_scholar.citation import CitationSchema
from bioetl.domain.schemas.semantic_scholar.paper import PaperSchema
from bioetl.domain.schemas.semantic_scholar.paper_author import PaperAuthorSchema

__all__ = [
    "AuthorSchema",
    "CitationSchema",
    "PaperAuthorSchema",
    "PaperSchema",
]
