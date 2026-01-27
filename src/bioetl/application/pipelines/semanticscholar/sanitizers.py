# src/bioetl/application/pipelines/semanticscholar/sanitizers.py
"""Identifier sanitization functions for Semantic Scholar pipeline.

Provides validation functions for external identifiers (ArXiv, DBLP)
that don't have domain-level Value Objects.
"""

from __future__ import annotations

import re

# ArXiv ID patterns (validated based on arXiv documentation)
# Old format (before 2007): category/YYMMNNN (e.g., hep-ph/9912271, cs.AI/0001007)
# New format (since 2007): YYMM.NNNNN[vN] (e.g., 0704.0001, 2301.12345v2)
_ARXIV_OLD_PATTERN = re.compile(r"^[a-z-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$", re.IGNORECASE)
_ARXIV_NEW_PATTERN = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")


def sanitize_arxiv_id(arxiv_id: str | None) -> str | None:
    """Sanitize and validate ArXiv ID.

    Validates against known ArXiv ID formats:
    - Old format (pre-2007): category/YYMMNNN (e.g., "hep-ph/9912271")
    - New format (post-2007): YYMM.NNNNN[vN] (e.g., "2301.12345v2")

    Args:
        arxiv_id: Raw ArXiv ID from S2 response.

    Returns:
        Sanitized ArXiv ID if valid, None otherwise.

    Example:
        >>> sanitize_arxiv_id("2301.12345")
        '2301.12345'
        >>> sanitize_arxiv_id("hep-ph/9912271")
        'hep-ph/9912271'
        >>> sanitize_arxiv_id("invalid-id")
        None

    """
    if not arxiv_id or not isinstance(arxiv_id, str):
        return None

    cleaned = arxiv_id.strip()
    if not cleaned:
        return None

    # Match against known patterns
    if _ARXIV_NEW_PATTERN.match(cleaned) or _ARXIV_OLD_PATTERN.match(cleaned):
        return cleaned

    return None


# DBLP ID pattern: paths with components separated by "/"
# Examples: "conf/nips/SmithJ21", "journals/jmlr/SmithJ21", "books/daglib/0028988"
_DBLP_PATTERN = re.compile(r"^[a-z]+(/[a-zA-Z0-9_-]+)+$")


def sanitize_dblp_id(dblp_id: str | None) -> str | None:
    """Sanitize and validate DBLP ID.

    Validates DBLP IDs which follow a path-like format:
    - Conference: "conf/venue/AuthorYear" (e.g., "conf/nips/SmithJ21")
    - Journal: "journals/journal/AuthorYear" (e.g., "journals/jmlr/SmithJ21")
    - Book: "books/publisher/id" (e.g., "books/daglib/0028988")

    Args:
        dblp_id: Raw DBLP ID from S2 response.

    Returns:
        Sanitized DBLP ID if valid, None otherwise.

    Example:
        >>> sanitize_dblp_id("conf/nips/SmithJ21")
        'conf/nips/SmithJ21'
        >>> sanitize_dblp_id("journals/jmlr/SmithJ21")
        'journals/jmlr/SmithJ21'
        >>> sanitize_dblp_id("invalid")
        None

    """
    if not dblp_id or not isinstance(dblp_id, str):
        return None

    cleaned = dblp_id.strip()
    if not cleaned:
        return None

    # Match against DBLP path pattern
    if _DBLP_PATTERN.match(cleaned):
        return cleaned

    return None
