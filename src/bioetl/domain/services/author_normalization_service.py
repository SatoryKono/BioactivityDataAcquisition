"""Author and affiliation normalization service.

Pure domain service (no I/O) per RULES.md §1.1.
Provides unified normalization for author names and affiliations across providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.services._author_helpers import (
    collect_affiliations_from_authors,
    deduplicate_case_insensitive,
    extract_affiliation_strings,
    normalize_affiliation_string,
    normalize_to_surname_initial,
    parse_author_names,
)

# Note: hash_author_name import removed - no longer hashing author names


@dataclass(frozen=True, slots=True)
class AuthorNormalizationService:
    """Unified author and affiliation normalization service.

    Handles normalization for all publication providers:
    - ChEMBL: concatenated string ("Author1; Author2")
    - PubMed: structured dicts with affiliations
    - CrossRef: dicts with ORCID and affiliations
    - OpenAlex/SemanticScholar: authorships with institutions
    """

    def normalize_author_list(
        self,
        authors: list[str]
        | list[dict[str, Any]]  # Any: record values are heterogeneous
        | str
        | None,  # Any: raw author data from heterogeneous APIs
    ) -> str | None:
        """Parse and normalize author names to JSON string.

        Args:
            authors: Author data in any supported format.

        Returns:
            JSON string of normalized author names, or None if empty.
        """
        if not authors:
            return None
        author_names = self._parse_author_names(authors)
        if not author_names:
            return None

        return serialize_to_json(author_names, ensure_ascii=True)

    def normalize_affiliations(
        self,
        affiliations: list[str]
        | list[dict[str, Any]]  # Any: record values are heterogeneous
        | None,  # Any: raw author data from heterogeneous APIs
    ) -> str | None:
        """Extract, normalize, deduplicate affiliations to JSON string.

        Args:
            affiliations: Affiliation data as strings or dicts.

        Returns:
            JSON string of unique sorted affiliations, or None if empty.
        """
        if not affiliations:
            return None
        normalized = self._normalize_affiliation_list(affiliations)
        return (
            serialize_to_json(sorted(normalized), ensure_ascii=False)
            if normalized
            else None
        )

    @staticmethod
    def _normalize_affiliation_list(
        affiliations: list[str]
        | list[dict[str, Any]],  # Any: raw author data from heterogeneous APIs
    ) -> list[str]:
        """Extract, normalize, and deduplicate affiliation strings."""
        aff_strings = extract_affiliation_strings(affiliations)
        normalized = [
            c for aff in aff_strings if (c := normalize_affiliation_string(aff))
        ]
        return deduplicate_case_insensitive(normalized)

    def extract_affiliations_from_authors(
        self,
        authors: list[dict[str, Any]],  # Any: raw author data from heterogeneous APIs
    ) -> list[str]:
        """Extract unique affiliations from author objects.

        Args:
            authors: List of author dicts with 'affiliations' key.

        Returns:
            List of unique normalized affiliation strings (sorted).
        """
        all_affiliations = collect_affiliations_from_authors(authors)
        if not all_affiliations:
            return []
        normalized = [
            c for aff in all_affiliations if (c := normalize_affiliation_string(aff))
        ]
        unique = deduplicate_case_insensitive(normalized)
        return sorted(unique)

    def normalize_author_keys(
        self,
        authors: list[str]
        | list[dict[str, Any]]  # Any: record values are heterogeneous
        | str
        | None,  # Any: raw author data from heterogeneous APIs
    ) -> str | None:
        """Normalize author names to short ``Surname_F`` keys.

        Args:
            authors: Author data in any supported format.

        Returns:
            Pipe-delimited string of short keys (e.g. ``"Doe_J|Smith_A"``),
            or None if empty.
        """
        if not authors:
            return None
        author_names = self._parse_author_names(authors)
        keys = [k for name in author_names if (k := normalize_to_surname_initial(name))]
        return "|".join(keys) if keys else None

    def _parse_author_names(
        self,
        authors: list[str]
        | list[dict[str, Any]]  # Any: record values are heterogeneous
        | str,  # Any: raw author data from heterogeneous APIs
    ) -> list[str]:
        """Parse various author formats to list of name strings."""
        return parse_author_names(authors)


__all__ = ["AuthorNormalizationService"]
