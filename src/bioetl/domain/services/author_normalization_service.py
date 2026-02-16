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
        authors: list[str] | list[dict[str, Any]] | str | None,
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
        affiliations: list[str] | list[dict[str, Any]] | None,
    ) -> str | None:
        """Extract, normalize, deduplicate affiliations to JSON string.

        Args:
            affiliations: Affiliation data as strings or dicts.

        Returns:
            JSON string of unique sorted affiliations, or None if empty.
        """
        if not affiliations:
            return None
        aff_strings = extract_affiliation_strings(affiliations)
        if not aff_strings:
            return None
        normalized = [
            c for aff in aff_strings if (c := normalize_affiliation_string(aff))
        ]
        if not normalized:
            return None
        unique = deduplicate_case_insensitive(normalized)
        return serialize_to_json(sorted(unique), ensure_ascii=False)

    def extract_affiliations_from_authors(
        self,
        authors: list[dict[str, Any]],
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

    def _parse_author_names(
        self,
        authors: list[str] | list[dict[str, Any]] | str,
    ) -> list[str]:
        """Parse various author formats to list of name strings."""
        return parse_author_names(authors)


__all__ = ["AuthorNormalizationService"]
