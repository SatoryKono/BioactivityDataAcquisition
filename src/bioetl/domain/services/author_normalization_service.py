"""Author and affiliation normalization service.

Pure domain service (no I/O) per RULES.md §1.1.
Provides unified normalization for author names and affiliations across providers.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from html import unescape
from typing import Any

from bioetl.domain.serialization import deserialize_from_json, serialize_to_json

# Regex patterns
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


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
        salt: str,
    ) -> str | None:
        """Parse, normalize, and hash author names to JSON string.

        Accepts multiple input formats:
        - list[str]: ["John Doe", "Jane Smith"]
        - list[dict]: [{"name": "John Doe", "orcid": "..."}]
        - str: "John Doe; Jane Smith" or JSON array
        - None

        Args:
            authors: Author data in any supported format.
            salt: Salt for PII hashing (RULES.md §5.4).

        Returns:
            JSON string of hashed author names: ["hash1", "hash2"]
            None if input is None/empty.

        Examples:
            >>> service = AuthorNormalizationService()
            >>> service.normalize_author_list(["John Doe"], "salt")
            '["abc123..."]'
        """
        if not authors:
            return None

        # Parse to list of name strings
        author_names = self._parse_author_names(authors)
        if not author_names:
            return None

        # Hash each name
        hashed = [self._hash_author_name(name, salt) for name in author_names]

        return serialize_to_json(hashed, ensure_ascii=True)

    def normalize_affiliations(
        self,
        affiliations: list[str] | list[dict[str, Any]] | None,
    ) -> str | None:
        """Extract, normalize, and deduplicate affiliations to JSON string.

        Normalization steps:
        1. Strip HTML tags and decode entities
        2. Collapse whitespace
        3. Unicode NFC normalization
        4. Trim leading/trailing whitespace
        5. Case-insensitive deduplication
        6. Sort alphabetically

        Args:
            affiliations: Affiliation data as strings or dicts.

        Returns:
            JSON string of unique normalized affiliations: ["University A", "University B"]
            None if input is None/empty.

        Examples:
            >>> service.normalize_affiliations(["MIT", "  mit ", "Harvard"])
            '["Harvard","MIT"]'  # Deduplicated, sorted
        """
        if not affiliations:
            return None

        # Extract affiliation strings
        aff_strings = self._extract_affiliation_strings(affiliations)
        if not aff_strings:
            return None

        # Normalize each affiliation
        normalized = []
        for aff in aff_strings:
            clean = self._normalize_affiliation_string(aff)
            if clean:
                normalized.append(clean)

        if not normalized:
            return None

        # Case-insensitive deduplication (preserve original case)
        unique = self._deduplicate_case_insensitive(normalized)

        # Sort alphabetically
        sorted_unique = sorted(unique)

        return serialize_to_json(sorted_unique, ensure_ascii=False)

    def extract_affiliations_from_authors(
        self,
        authors: list[dict[str, Any]],
    ) -> list[str]:
        """Extract unique affiliations from author objects.

        Args:
            authors: List of author dicts with 'affiliations' key.
                Format: [{"name": "...", "affiliations": ["Univ A", "Univ B"]}]

        Returns:
            List of unique normalized affiliation strings (sorted).

        Examples:
            >>> authors = [
            ...     {"name": "John", "affiliations": ["MIT", "Harvard"]},
            ...     {"name": "Jane", "affiliations": ["MIT"]}
            ... ]
            >>> service.extract_affiliations_from_authors(authors)
            ['Harvard', 'MIT']
        """
        all_affiliations: list[str] = []

        for author in authors:
            if not isinstance(author, dict):
                continue

            aff_data = author.get("affiliations")
            if not aff_data:
                continue

            # Handle list of strings or single string
            if isinstance(aff_data, list):
                all_affiliations.extend(str(a) for a in aff_data if a)
            elif isinstance(aff_data, str):
                all_affiliations.append(aff_data)

        if not all_affiliations:
            return []

        # Normalize and deduplicate
        normalized = []
        for aff in all_affiliations:
            clean = self._normalize_affiliation_string(aff)
            if clean:
                normalized.append(clean)

        unique = self._deduplicate_case_insensitive(normalized)
        return sorted(unique)

    # =========================================================================
    # Private helper methods
    # =========================================================================

    def _parse_author_names(
        self,
        authors: list[str] | list[dict[str, Any]] | str,
    ) -> list[str]:
        """Parse various author formats to list of name strings."""
        if isinstance(authors, list):
            return self._parse_author_list(authors)
        if isinstance(authors, str):
            return self._parse_author_string(authors)
        return []

    def _parse_author_list(
        self,
        authors: list[str] | list[dict[str, Any]],
    ) -> list[str]:
        """Parse list of authors (strings or dicts with 'name' key)."""
        names: list[str] = []

        for author in authors:
            if isinstance(author, str):
                stripped = author.strip()
                if stripped:
                    names.append(stripped)
            elif isinstance(author, dict):
                name = author.get("name")
                if name and isinstance(name, str):
                    stripped = name.strip()
                    if stripped:
                        names.append(stripped)

        return names

    def _parse_author_string(self, text: str) -> list[str]:
        """Parse author string (JSON or delimited format)."""
        text = text.strip()
        if not text:
            return []

        # Try JSON first
        if text.startswith("["):
            json_result = self._try_parse_json_authors(text)
            if json_result is not None:
                return json_result

        # Parse delimited string (semicolon or comma)
        return self._parse_delimited_authors(text)

    def _try_parse_json_authors(self, text: str) -> list[str] | None:
        """Try to parse JSON array of authors."""
        try:
            parsed = deserialize_from_json(text)
            if not isinstance(parsed, list):
                return None

            names = []
            for item in parsed:
                if isinstance(item, str) and item.strip():
                    names.append(item.strip())
                elif isinstance(item, dict):
                    name = item.get("name")
                    if name and isinstance(name, str) and name.strip():
                        names.append(name.strip())

            return names

        except (ValueError, TypeError):
            return None

    def _parse_delimited_authors(self, text: str) -> list[str]:
        """Parse delimited string (semicolon or comma separated)."""
        # Prefer semicolon (ChEMBL format)
        delimiter = ";" if ";" in text else ","
        parts = text.split(delimiter) if delimiter in text else [text]

        return [part.strip() for part in parts if part.strip()]

    def _extract_affiliation_strings(
        self,
        affiliations: list[str] | list[dict[str, Any]],
    ) -> list[str]:
        """Extract affiliation strings from mixed list."""
        strings: list[str] = []

        for aff in affiliations:
            if isinstance(aff, str) and aff.strip():
                strings.append(aff.strip())
            elif isinstance(aff, dict):
                # Try common keys: 'name', 'display_name', 'affiliation'
                for key in ("name", "display_name", "affiliation"):
                    value = aff.get(key)
                    if value and isinstance(value, str) and value.strip():
                        strings.append(value.strip())
                        break

        return strings

    def _normalize_affiliation_string(self, text: str) -> str | None:
        """Normalize affiliation string: HTML cleanup, whitespace, unicode NFC.

        Same pipeline as title/abstract normalization but for affiliations.
        """
        if not text:
            return None

        # Step 1: Strip HTML tags and decode entities
        normalized = _HTML_TAG_PATTERN.sub("", text)
        normalized = unescape(normalized)

        # Step 2: Collapse multiple whitespace to single space
        normalized = _WHITESPACE_PATTERN.sub(" ", normalized)

        # Step 3: Remove control characters (excluding whitespace)
        normalized = _CONTROL_CHARS_PATTERN.sub("", normalized)

        # Step 4: Unicode NFC normalization
        normalized = unicodedata.normalize("NFC", normalized)

        # Step 5: Trim leading/trailing whitespace
        normalized = normalized.strip()

        return normalized if normalized else None

    def _deduplicate_case_insensitive(self, strings: list[str]) -> list[str]:
        """Deduplicate strings case-insensitively, preserving original case.

        When duplicates are found, keeps the first occurrence.

        Examples:
            >>> self._deduplicate_case_insensitive(["MIT", "mit", "Harvard"])
            ['MIT', 'Harvard']
        """
        seen: dict[str, str] = {}  # lowercase -> original
        for s in strings:
            key = s.lower()
            if key not in seen:
                seen[key] = s

        return list(seen.values())

    def _hash_author_name(self, name: str, salt: str) -> str:
        """Hash author name with salt using SHA-256 per RULES.md §5.4.

        Normalization: strip whitespace, lowercase before hashing.
        Formula: sha256(lowercase(name) + SALT)

        Args:
            name: Author name to hash.
            salt: Salt for hashing.

        Returns:
            SHA-256 hex digest.
        """
        normalized = name.strip().lower()
        return hashlib.sha256(f"{normalized}{salt}".encode()).hexdigest()


__all__ = ["AuthorNormalizationService"]
