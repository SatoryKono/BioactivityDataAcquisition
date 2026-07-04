"""Shared constants for Semantic Scholar adapters.

Semantic Scholar Academic Graph API v1:
    Key endpoints: papers/batch (max 500/request), paper/search (offset-based).
    Rate limits: 1 req/sec (no key), 10 req/sec (with API key).
    Docs: https://api.semanticscholar.org/api-docs/
"""

from __future__ import annotations

__all__ = ["SEMANTICSCHOLAR_BASE_URL"]


SEMANTICSCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"
