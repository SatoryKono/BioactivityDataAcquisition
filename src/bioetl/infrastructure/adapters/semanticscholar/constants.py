"""Shared constants for Semantic Scholar adapters.

Semantic Scholar Academic Graph API v1:
    Key endpoints: paper/batch (max 500/request), paper/search (offset-based).
    Request pacing and retry policy are owned by configs/providers/semanticscholar.yaml.
    Docs: https://api.semanticscholar.org/api-docs/
"""

from __future__ import annotations

__all__ = ["SEMANTICSCHOLAR_BASE_URL"]


SEMANTICSCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"
