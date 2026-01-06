# src/bioetl/domain/schemas/semanticscholar/publication.py
"""Pandera schema for Semantic Scholar Publication entity.

Aligned with RULES.md v5.8.
Includes lookup metadata fields for DOI/title resolution tracking.
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

# Lookup method values for batch DOI resolution
LOOKUP_METHODS = ["doi", "title_fallback", "title_only", "unknown"]

# Open Access status values (from S2 API)
OA_STATUS_VALUES = ["GREEN", "GOLD", "HYBRID", "BRONZE"]


class SemanticScholarPublicationSchema(ETLRecordSchema):
    """Semantic Scholar Publication validation schema for Silver layer.

    Validates publication records from Semantic Scholar Academic Graph API.
    Includes lookup metadata for tracking DOI vs title resolution.
    """

    # === Primary Key ===
    paper_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[a-f0-9]{40}$",
        description="Semantic Scholar Paper ID (40-char hex)",
    )

    # === External Identifiers ===
    doi: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^10\.\d{4,}/.*$",
        description="Digital Object Identifier",
    )

    pmid: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^\d+$",
        description="PubMed ID",
    )

    pmcid: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^PMC\d+$",
        description="PubMed Central ID",
    )

    arxiv_id: Series[str] = pa.Field(
        nullable=True,
        description="ArXiv ID",
    )

    corpus_id: Series[int] = pa.Field(
        nullable=True,
        ge=0,
        description="S2 Corpus ID",
    )

    # === Core Fields ===
    title: Series[str] = pa.Field(
        nullable=True,
        description="Publication title",
    )

    abstract: Series[str] = pa.Field(
        nullable=True,
        description="Abstract text",
    )

    tldr: Series[str] = pa.Field(
        nullable=True,
        description="AI-generated summary (TLDR)",
    )

    year: Series[int] = pa.Field(
        nullable=True,
        ge=1500,
        le=2100,
        description="Publication year",
    )

    publication_date: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{2}-\d{2}$",
        description="Publication date (YYYY-MM-DD)",
    )

    # === Journal/Venue ===
    journal: Series[str] = pa.Field(
        nullable=True,
        description="Journal name",
    )

    volume: Series[str] = pa.Field(
        nullable=True,
        description="Journal volume",
    )

    pages: Series[str] = pa.Field(
        nullable=True,
        description="Page range",
    )

    venue: Series[str] = pa.Field(
        nullable=True,
        description="Publication venue",
    )

    # === Metrics ===
    citation_count: Series[int] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of citations",
    )

    reference_count: Series[int] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of references",
    )

    # === Open Access ===
    is_open_access: Series[bool] = pa.Field(
        nullable=True,
        description="Is Open Access",
    )

    open_access_url: Series[str] = pa.Field(
        nullable=True,
        description="Direct link to OA PDF",
    )

    open_access_status: Series[str] = pa.Field(
        nullable=True,
        isin=OA_STATUS_VALUES,
        description="OA status (GREEN, GOLD, HYBRID, BRONZE)",
    )

    # === Classification ===
    fields_of_study: Series[str] = pa.Field(
        nullable=True,
        description="Fields of study (JSON array)",
    )

    publication_types: Series[str] = pa.Field(
        nullable=True,
        description="Publication types (JSON array)",
    )

    # === Authors (hashed for PII compliance) ===
    authors: Series[str] = pa.Field(
        nullable=True,
        description="Author names (JSON array, optionally hashed)",
    )

    # === Source Tracking ===
    source: Series[str] = pa.Field(
        nullable=False,
        isin=["semanticscholar"],
        description="Data source identifier",
    )

    # === Lookup Metadata (batch DOI resolution) ===
    _lookup_method: Series[str] = pa.Field(
        nullable=False,
        isin=LOOKUP_METHODS,
        description="How record was resolved: doi, title_fallback, title_only",
    )

    _original_doi: Series[str] = pa.Field(
        nullable=True,
        description="Original DOI from input CSV (for fallback records)",
    )

    class Config:
        """Pandera configuration."""

        strict = True  # Disallow extra columns not in schema
        ordered = True  # Enforce column order
        coerce = True  # Coerce data types to match schema
        name = "SemanticScholarPublicationSchema"
        description = "Semantic Scholar Publication Silver layer validation"
