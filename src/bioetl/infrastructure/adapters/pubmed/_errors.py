"""Shared PubMed adapter exception groups."""

from __future__ import annotations

from bioetl.infrastructure.adapters.common.error_bundles import (
    build_common_network_error_bundle,
)

__all__ = ["PUBMED_COMMON_ERRORS", "PUBMED_RECORD_ERRORS"]

PUBMED_COMMON_ERRORS = build_common_network_error_bundle()

PUBMED_RECORD_ERRORS = (*PUBMED_COMMON_ERRORS, KeyError)
