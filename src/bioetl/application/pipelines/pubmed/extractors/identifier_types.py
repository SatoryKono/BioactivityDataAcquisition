"""Type definitions for PubMed identifier extraction.

Separated from extractors to reduce file size and circular imports.
"""

from __future__ import annotations

from typing import TypedDict


class ArticleIdentifiers(TypedDict):
    """Identifier data container (raw or normalized)."""

    doi: str | None
    pmc_id: str | None


class CombinedIdentifiers(TypedDict):
    """Container for multiple identifiers extracted in a single pass."""

    doi: str | None
    pmc_id: str | None
    pii: str | None
    mid: str | None
    publisher_id: str | None


# Aliases for clarity in extractor API
RawIdentifiers = ArticleIdentifiers
NormalizedIdentifiers = ArticleIdentifiers


class AllArticleIds(TypedDict, total=False):
    """Complete set of article identifiers from PubMed.

    ArticleIdList can contain various ID types:
    - pubmed: PubMed ID
    - doi: Digital Object Identifier
    - pmc: PubMed Central ID
    - pii: Publisher Item Identifier
    - mid: Manuscript ID (PMC submission)
    - publisher-id: Publisher-specific identifier
    - pmcid: Alternative PMC ID format
    - medline: MEDLINE unique ID
    """

    pubmed: str | None
    doi: str | None
    pmc: str | None
    pii: str | None
    mid: str | None
    publisher_id: str | None
    pmcid: str | None
    medline: str | None
    other_ids: dict[str, str]  # Any other ID types encountered


class ELocationIds(TypedDict, total=False):
    """Electronic location identifiers from ELocationID elements.

    ELocationID provides additional identifiers like:
    - doi: Digital Object Identifier
    - pii: Publisher Item Identifier
    """

    doi: str | None
    pii: str | None
