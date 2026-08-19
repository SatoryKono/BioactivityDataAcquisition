"""Canonical column ordering for ETL records.

Defines the standard order of columns across all layers (Silver, Gold).
Per RULES.md §2.4 Metadata Fields and ADR-014 Deterministic Writes.

This module provides:
- SYSTEM_FIELDS_PREFIX: Fields that MUST appear first
- DQ_FIELDS_SUFFIX: DQ flags that MUST appear last (if present)
- canonical_column_order(): Function to reorder any column list
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "ALL_SYSTEM_FIELDS",
    "DQ_FIELDS_SUFFIX",
    "SYSTEM_FIELDS_PREFIX",
    "canonical_column_order",
]


# System fields that MUST appear first (in order)
# These are lineage/metadata fields per RULES.md §2.4
SYSTEM_FIELDS_PREFIX: Final[tuple[str, ...]] = (
    "entity_id",
    "content_hash",
    "_run_id",
    "_run_type",
    "_source_batch_id",
    "_source",
    "_ingestion_ts",
    "_index",
)

LOOKUP_FIELDS_PREFIX: Final[tuple[str, ...]] = (
    "_lookup_method",
    "_original_id",
)

PUBLICATION_METADATA_FIELDS: Final[tuple[str, ...]] = (
    "authors",
    "title",
    "journal",
    "publication_year",  # was: year
    "volume",
    "issue",
    "page_first",  # was: first_page
    "page_last",  # was: last_page
    "language",
)

PUBLICATION_CROSSREF_FIELDS: Final[tuple[str, ...]] = (
    "publication_id",
    "publication_doi",
    "publication_pmid",
    "publication_pmc_id",
)


PUBLICATION_UNIFIED_FIELDS: Final[tuple[str, ...]] = (
    "publication_type",  # was: doc_type
    "is_oa",
    "abstract",
    "citations_received",  # was: citation_count
    "citations_made",  # added: reference_count equivalent
    "publication_date",
)

# DQ flags that MUST appear last (in order), if present
# Not all schemas have these fields
DQ_FIELDS_SUFFIX: Final[tuple[str, ...]] = (
    "_dq_error",
    "_dq_warn",
)


# All system fields (prefix + suffix) for quick membership check
ALL_SYSTEM_FIELDS: Final[frozenset[str]] = frozenset(
    SYSTEM_FIELDS_PREFIX + LOOKUP_FIELDS_PREFIX + DQ_FIELDS_SUFFIX
)


def _filter_present(
    ordered_fields: tuple[str, ...], present: frozenset[str]
) -> list[str]:
    """Filter ordered fields to those present in the column set."""
    return [f for f in ordered_fields if f in present]


def canonical_column_order(columns: list[str] | tuple[str, ...]) -> list[str]:
    """Reorder columns to canonical order.

    Order:
    1. System prefix fields (entity_id, content_hash, _run_id, ...)
    2. Business fields (sorted alphabetically)
    3. DQ suffix fields (_dq_error, _dq_warn) if present

    Args:
        columns: Unordered list/tuple of column names.

    Returns:
        Columns in canonical order.

    Example:
        >>> canonical_column_order(["_dq_warn", "name", "entity_id", "_run_id", "content_hash"])
        ['entity_id', 'content_hash', '_run_id', 'name', '_dq_warn']

        >>> canonical_column_order(["activity_id", "_index", "entity_id", "content_hash"])
        ['entity_id', 'content_hash', '_index', 'activity_id']

        >>> canonical_column_order(["z_field", "a_field", "entity_id", "_run_type"])
        ['entity_id', '_run_type', 'a_field', 'z_field']
    """
    columns_set = frozenset(columns)

    # 1. System prefix fields (preserve defined order, skip missing)
    prefix = _filter_present(SYSTEM_FIELDS_PREFIX, columns_set)

    # 2. Lookup fields (preserve defined order)
    lookup = _filter_present(LOOKUP_FIELDS_PREFIX, columns_set)

    # 2. DQ suffix fields (preserve defined order, skip missing)
    suffix = _filter_present(DQ_FIELDS_SUFFIX, columns_set)

    # 3. Business fields (sorted alphabetically)
    business = sorted(columns_set - ALL_SYSTEM_FIELDS)

    return prefix + lookup + business + suffix
