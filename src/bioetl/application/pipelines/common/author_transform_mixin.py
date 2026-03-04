"""Author normalization mixin for publication transformers.

Extracts the common author processing pipeline shared by CrossRef,
OpenAlex, PubMed, and SemanticScholar transformers:
- Author name normalization (parse + serialize)
- Author search key generation
- Affiliation normalization
- Author PII hashing for GDPR compliance
"""

from __future__ import annotations

__all__ = ["AuthorTransformMixin"]


from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.ports import DataNormalizationPort, PiiHasherPort


class AuthorTransformMixin:
    """Shared author normalization methods for publication transformers.

    Requires host class to provide ``_data_normalizer`` and ``_pii_hasher``
    attributes (injected by ``BaseTransformer.__init__``).

    Naming: ``*Mixin`` suffix per NAME-001.
    """

    _data_normalizer: DataNormalizationPort
    _pii_hasher: PiiHasherPort

    def _normalize_author_block(
        self,
        raw_author_names: list[str],
        raw_affiliations: list[str] | None = None,
    ) -> dict[str, str | None]:
        """Normalize authors and affiliations via DataNormalizationPort.

        Consolidates the 3-call pattern repeated across 4 publication
        transformers (CrossRef, OpenAlex, SemanticScholar, PubMed):

        1. ``normalize_author_list(raw_authors)`` → JSON string
        2. ``normalize_author_keys(raw_authors)`` → JSON string
        3. ``normalize_affiliations(affiliations)`` → JSON string (optional)

        Args:
            raw_author_names: List of author name strings.
            raw_affiliations: Optional list of affiliation strings.

        Returns:
            Dict with ``authors``, ``author_keys``, and optionally
            ``affiliation_list`` keys.

        """
        normalizer = self._data_normalizer
        result: dict[str, str | None] = {
            "authors": normalizer.normalize_author_list(raw_author_names),
            "author_keys": normalizer.normalize_author_keys(raw_author_names),
        }
        if raw_affiliations is not None:
            result["affiliation_list"] = (
                normalizer.normalize_affiliations(raw_affiliations)
                if raw_affiliations
                else None
            )
        return result

    def _hash_author_pii_details(
        self,
        author_details: list[
            dict[str, Any]  # Any: heterogeneous author record values
        ],
        pii_fields: tuple[str, ...] = ("given", "family", "name"),
        preserve_fields: dict[
            str, Any  # Any: default values for preserved fields vary
        ]
        | None = None,
    ) -> list[dict[str, Any]]:  # Any: heterogeneous author record values
        """Hash PII fields in author details while preserving non-PII data.

        Generalises the ``_hash_author_details`` pattern from CrossRef
        transformer. PII fields (names) are hashed via ``PiiHasherPort``;
        non-PII fields (ORCID, sequence, affiliations) are kept intact.

        Args:
            author_details: List of author detail dictionaries.
            pii_fields: Tuple of field names to hash.
            preserve_fields: Mapping of field_name → default_value for
                non-PII fields to preserve. Defaults to ORCID/sequence/affiliations.

        Returns:
            New list of author dicts with hashed PII fields.

        """
        if preserve_fields is None:
            preserve_fields = {
                "orcid": None,
                "authenticated_orcid": None,
                "sequence": None,
                "affiliations": [],
            }

        hashed_details: list[
            dict[str, Any]  # Any: heterogeneous author record values
        ] = []

        for author in author_details:
            hashed_author: dict[
                str, Any  # Any: heterogeneous author record values
            ] = {}

            # Hash PII fields (author names)
            for field in pii_fields:
                value = author.get(field)
                if value and isinstance(value, str):
                    hashed_author[field] = self._pii_hasher.hash_value(value)
                else:
                    hashed_author[field] = None

            # Preserve non-PII fields with defaults
            for field, default in preserve_fields.items():
                hashed_author[field] = author.get(field, default)

            hashed_details.append(hashed_author)

        return hashed_details
