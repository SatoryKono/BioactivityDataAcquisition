# src/bioetl/infrastructure/adapters/pubmed/constants.py
"""Constants for the PubMed adapter.

NCBI Entrez E-utilities API:
    Base URL covers esearch.fcgi, efetch.fcgi, einfo.fcgi, epost.fcgi.
    Rate limits: 3 req/sec (no API key), 10 req/sec (with API key).
    Email required by NCBI Terms of Service for all requests.
    Docs: https://www.ncbi.nlm.nih.gov/books/NBK25497/
"""

from __future__ import annotations

__all__ = ["ENTREZ_API_BASE"]


ENTREZ_API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
