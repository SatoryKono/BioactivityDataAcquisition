"""UniProt adapter constants.

UniProt REST API (2022+ redesign):
    Endpoints used: /uniprotkb/search, /uniprotkb/stream.
    Pagination: cursor-based via Link header.
    Rate limits: fair-use throttling (no published hard limit).
    Docs: https://www.uniprot.org/help/api
"""

from __future__ import annotations

__all__ = ["UNIPROT_API_BASE"]

UNIPROT_API_BASE = "https://rest.uniprot.org"
