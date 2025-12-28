"""Semantic Scholar adapter package.

Provides access to Semantic Scholar Graph API for academic paper data
with ML-enriched metadata including citations, influence, and embeddings.

Example:
    >>> from bioetl.infrastructure.adapters.semantic_scholar import (
    ...     SemanticScholarAdapter,
    ...     BatchResolver,
    ...     IdType,
    ... )
    >>> adapter = SemanticScholarAdapter(
    ...     logger=logger,
    ...     rate_limiter=rate_limiter,
    ...     circuit_breaker=circuit_breaker,
    ...     thread_pool=thread_pool,
    ... )
    >>> resolver = BatchResolver(adapter=adapter)
    >>> async for paper in resolver.resolve_dois(["10.1038/nature12373"]):
    ...     print(paper['title'])

"""

from bioetl.infrastructure.adapters.semantic_scholar.batch import (
    BatchResolver,
    BatchResult,
    IdType,
    create_batch_resolver,
)
from bioetl.infrastructure.adapters.semantic_scholar.client import (
    DEFAULT_PAPER_FIELDS,
    EXTENDED_PAPER_FIELDS,
    SemanticScholarAdapter,
)

__all__ = [
    "DEFAULT_PAPER_FIELDS",
    "EXTENDED_PAPER_FIELDS",
    "BatchResolver",
    "BatchResult",
    "IdType",
    "SemanticScholarAdapter",
    "create_batch_resolver",
]
