"""Shared PubMed adapter exception groups."""

from __future__ import annotations

from httpx import RequestError

from bioetl.domain.exceptions import BioETLError, NetworkError

__all__ = ["PUBMED_COMMON_ERRORS", "PUBMED_RECORD_ERRORS"]

PUBMED_COMMON_ERRORS = (
    BioETLError,
    NetworkError,
    RequestError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
)

PUBMED_RECORD_ERRORS = (*PUBMED_COMMON_ERRORS, KeyError)
