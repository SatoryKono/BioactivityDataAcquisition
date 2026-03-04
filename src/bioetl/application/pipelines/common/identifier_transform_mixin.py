"""Identifier validation mixin for publication transformers.

Extracts the common identifier handling patterns shared by CrossRef,
OpenAlex, PubMed, and SemanticScholar transformers:
- DOI validation via Value Object
- PMID validation via Value Object
- Common metadata block construction (_source, _dq_warn, etc.)
"""

from __future__ import annotations

__all__ = ["IdentifierTransformMixin"]


from typing import Any

from bioetl.domain.value_objects import DOI, PubMedId


class IdentifierTransformMixin:
    """Shared identifier validation and metadata methods.

    Provides convenience wrappers around ``validate_value_object`` for
    the most common publication identifiers (DOI, PMID), and a builder
    for the metadata block that all publication transformers append.

    Requires host class to provide ``validate_value_object`` static method
    (from ``BaseTransformer``).

    Naming: ``*Mixin`` suffix per NAME-001.
    """

    def _validate_doi(
        self,
        raw_doi: Any,  # Any: raw API value (str | None)
    ) -> str | None:
        """Validate and normalize DOI using Value Object.

        Consolidates the repeated ``validate_value_object(DOI, ...)``
        and ``DOI.from_raw(...)`` patterns across all publication
        transformers.

        Args:
            raw_doi: Raw DOI string from provider API.

        Returns:
            Normalized lowercase DOI, or None if invalid.

        """
        from bioetl.application.core.base_transformer import BaseTransformer

        return BaseTransformer.validate_value_object(DOI, raw_doi)

    def _validate_pmid(
        self,
        raw_pmid: Any,  # Any: raw API value (str | int | None)
    ) -> str | None:
        """Validate and normalize PubMed ID using Value Object.

        Consolidates the repeated ``PubMedId.from_raw(...)`` patterns
        in PubMed and SemanticScholar transformers.

        Args:
            raw_pmid: Raw PMID from provider API.

        Returns:
            Normalized PMID string, or None if invalid.

        """
        from bioetl.application.core.base_transformer import BaseTransformer

        return BaseTransformer.validate_value_object(PubMedId, raw_pmid)

    @staticmethod
    def _build_metadata_block(
        source: str,
        record: dict[str, Any],  # Any: raw API record values
        default_lookup: str = "unknown",
    ) -> dict[str, Any]:  # Any: metadata values (str | bool | None)
        """Build common metadata fields for silver records.

        Consolidates the 5-field metadata block repeated at the end
        of every publication transformer's ``_extract_business_data``:
        ``_source``, ``_lookup_method``, ``_original_id``,
        ``_dq_warn``, ``_dq_error``.

        Args:
            source: Provider name (e.g., "crossref", "openalex").
            record: Raw Bronze record for extracting lookup metadata.
            default_lookup: Default value for ``_lookup_method``.

        Returns:
            Dict with the 5 standard metadata fields.

        """
        return {
            "_source": source,
            "_lookup_method": record.get("_lookup_method", default_lookup),
            "_original_id": record.get("_original_id"),
            "_dq_warn": False,
            "_dq_error": False,
        }
