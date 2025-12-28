"""Batch resolver for Semantic Scholar API.

Handles efficient batch lookups using S2 batch API endpoint.
Supports paper IDs, DOIs, arXiv IDs, and PubMed IDs.

API Reference: https://api.semanticscholar.org/api-docs/graph#tag/Paper-Data/operation/post_graph_get_papers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.infrastructure.adapters.semantic_scholar.client import (
        SemanticScholarAdapter,
    )


class IdType(str, Enum):
    """Supported identifier types for Semantic Scholar batch lookup.

    Each type requires specific formatting for the API:
    - PAPER_ID: Native S2 ID (no prefix)
    - DOI: Requires 'DOI:' prefix
    - ARXIV: Requires 'ARXIV:' prefix
    - PMID: Requires 'PMID:' prefix
    - MAG: Microsoft Academic Graph ID (requires 'MAG:' prefix)
    - CORPUS_ID: S2 Corpus ID (requires 'CorpusId:' prefix)
    """

    PAPER_ID = "paperId"
    DOI = "DOI"
    ARXIV = "ArXiv"
    PMID = "PubMed"
    MAG = "MAG"
    CORPUS_ID = "CorpusId"


# Maximum IDs per batch request (S2 API limit)
MAX_BATCH_SIZE = 500


@dataclass
class BatchResult:
    """Result of a batch lookup operation.

    Attributes:
        papers: Successfully resolved papers.
        not_found: IDs that were not found.
        errors: IDs that caused errors.

    """

    papers: list[dict[str, Any]] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class BatchResolver:
    """Resolves paper IDs to full paper records using batch API.

    Handles chunking of large ID lists into batches of up to 500 IDs,
    formatting IDs with appropriate prefixes, and aggregating results.

    Example:
        >>> resolver = BatchResolver(adapter=s2_adapter, batch_size=500)
        >>> dois = ["10.1038/nature12373", "10.1126/science.1234567"]
        >>> async for paper in resolver.resolve(dois, id_type=IdType.DOI):
        ...     print(paper['title'])

    Attributes:
        adapter: SemanticScholarAdapter instance for API calls.
        batch_size: Maximum IDs per batch request (default: 500).

    """

    adapter: SemanticScholarAdapter
    batch_size: int = MAX_BATCH_SIZE

    def __post_init__(self) -> None:
        """Validate batch size."""
        if self.batch_size > MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch size {self.batch_size} exceeds maximum {MAX_BATCH_SIZE}"
            )
        if self.batch_size < 1:
            raise ValueError("Batch size must be positive")

    def _format_id(self, identifier: str, id_type: IdType) -> str:
        """Format identifier with appropriate prefix for S2 API.

        Args:
            identifier: Raw identifier value.
            id_type: Type of identifier.

        Returns:
            Formatted identifier with prefix if needed.

        """
        if id_type == IdType.PAPER_ID:
            # Native S2 ID, no prefix needed
            return identifier

        # Add prefix if not already present
        prefix = f"{id_type.value}:"
        if identifier.upper().startswith(prefix.upper()):
            return identifier
        return f"{prefix}{identifier}"

    def _chunk_ids(self, ids: list[str]) -> list[list[str]]:
        """Split ID list into chunks of batch_size.

        Args:
            ids: List of identifiers to chunk.

        Returns:
            List of ID chunks.

        """
        return [
            ids[i : i + self.batch_size]
            for i in range(0, len(ids), self.batch_size)
        ]

    async def resolve(
        self,
        ids: list[str],
        id_type: IdType = IdType.PAPER_ID,
    ) -> AsyncIterator[dict[str, Any]]:
        """Resolve paper IDs to full records.

        Chunks IDs into batches of up to 500 and yields papers as found.

        Args:
            ids: List of paper identifiers.
            id_type: Type of identifiers (DOI, ARXIV, PMID, etc.).

        Yields:
            Paper records as dictionaries.

        """
        if not ids:
            return

        # Format IDs with appropriate prefix
        formatted_ids = [self._format_id(pid, id_type) for pid in ids]

        # Process in batches
        for chunk in self._chunk_ids(formatted_ids):
            async for paper in self.adapter._fetch_by_ids(chunk, id_type.value):
                yield paper

    async def resolve_all(
        self,
        ids: list[str],
        id_type: IdType = IdType.PAPER_ID,
    ) -> BatchResult:
        """Resolve all IDs and return aggregated result.

        Unlike resolve(), this collects all results before returning,
        tracking not-found IDs and errors.

        Args:
            ids: List of paper identifiers.
            id_type: Type of identifiers.

        Returns:
            BatchResult with papers, not_found, and errors.

        """
        result = BatchResult()
        found_ids: set[str] = set()

        async for paper in self.resolve(ids, id_type):
            result.papers.append(paper)
            found_ids.add(paper.get("semantic_scholar_id", ""))

            # Also track by DOI if present
            if paper.get("doi"):
                found_ids.add(paper["doi"].lower())

        # Determine not found IDs
        for pid in ids:
            normalized = pid.lower() if id_type == IdType.DOI else pid
            if normalized not in found_ids:
                result.not_found.append(pid)

        return result

    async def resolve_dois(
        self,
        dois: list[str],
    ) -> AsyncIterator[dict[str, Any]]:
        """Convenience method for resolving DOIs.

        Args:
            dois: List of DOIs (with or without 'DOI:' prefix).

        Yields:
            Paper records as dictionaries.

        """
        async for paper in self.resolve(dois, IdType.DOI):
            yield paper

    async def resolve_pmids(
        self,
        pmids: list[str | int],
    ) -> AsyncIterator[dict[str, Any]]:
        """Convenience method for resolving PubMed IDs.

        Args:
            pmids: List of PubMed IDs (can be strings or integers).

        Yields:
            Paper records as dictionaries.

        """
        str_pmids = [str(pmid) for pmid in pmids]
        async for paper in self.resolve(str_pmids, IdType.PMID):
            yield paper

    async def resolve_arxiv(
        self,
        arxiv_ids: list[str],
    ) -> AsyncIterator[dict[str, Any]]:
        """Convenience method for resolving arXiv IDs.

        Args:
            arxiv_ids: List of arXiv IDs (e.g., '2103.15348').

        Yields:
            Paper records as dictionaries.

        """
        async for paper in self.resolve(arxiv_ids, IdType.ARXIV):
            yield paper


def create_batch_resolver(
    adapter: SemanticScholarAdapter,
    batch_size: int = MAX_BATCH_SIZE,
) -> BatchResolver:
    """Factory function to create BatchResolver.

    Args:
        adapter: Configured SemanticScholarAdapter.
        batch_size: Maximum IDs per batch (default: 500).

    Returns:
        Configured BatchResolver instance.

    """
    return BatchResolver(adapter=adapter, batch_size=batch_size)
