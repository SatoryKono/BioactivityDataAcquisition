"""Shared constants for Semantic Scholar adapters.

Semantic Scholar Academic Graph API v1:
    Key endpoints: papers/batch (max 500/request), paper/search (offset-based).
    Anonymous rate limits are shared; local pacing comes from provider YAML.
    Docs: https://api.semanticscholar.org/api-docs/
"""

from __future__ import annotations

__all__ = ["SEMANTICSCHOLAR_BASE_URL", "SEMANTICSCHOLAR_HEALTH_PAPER"]


SEMANTICSCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"

# Stable DOI resolved by the publication ingestion path; no search query required.
SEMANTICSCHOLAR_HEALTH_PAPER = "DOI:10.1021/jm990412m"
