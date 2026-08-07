"""Academic identifier Value Objects for BioETL domain.

Contains Value Objects for academic publication identifiers:
- OpenAlexId: OpenAlex Work IDs (W2741809807)
- SemanticScholarId: Semantic Scholar Paper IDs (40-char hex)
- ISSN: International Standard Serial Numbers
- ORCID: Open Researcher and Contributor IDs

These Value Objects encapsulate validation and normalization rules.
"""

from __future__ import annotations

import re

from bioetl.domain.value_objects.base import ValueObject

__all__ = [
    "ISSN",
    "ORCID",
    "OpenAlexId",
    "SemanticScholarId",
]


class OpenAlexId(ValueObject[str]):
    """OpenAlex Work ID.

    OpenAlex assigns unique identifiers to works (papers, articles, etc.)
    in the format Wxxxx... where x is a digit.
    Can also be extracted from OpenAlex URLs.

    Examples: W2741809807, https://openalex.org/W2741809807

    Invariants:
        - Starts with "W" followed by one or more digits
        - Normalized to uppercase
        - URL prefixes are automatically stripped
    """

    __slots__ = ()
    _value: str
    _PATTERN = re.compile(r"^W\d+$")
    _URL_PREFIX = "https://openalex.org/"

    def _validate(self, value: str) -> str:
        """Validate and normalize OpenAlex ID."""
        if not isinstance(value, str):
            raise ValueError(f"OpenAlexId must be str, got {type(value).__name__}")

        normalized = value.strip()
        if not normalized:
            raise ValueError("OpenAlexId cannot be empty")

        # Extract from URL if needed
        if normalized.lower().startswith(self._URL_PREFIX.lower()):
            normalized = normalized[len(self._URL_PREFIX) :]

        normalized = normalized.strip().upper()

        if not self._PATTERN.match(normalized):
            raise ValueError(
                f"Invalid OpenAlex ID format: {value!r}. Expected: W<digits>"
            )

        return normalized

    @property
    def url(self) -> str:
        """Get the full OpenAlex URL for web access."""
        return f"{self._URL_PREFIX}{self._value}"

    @property
    def numeric_id(self) -> int:
        """Get the numeric part of the OpenAlex ID."""
        return int(self._value[1:])

    @classmethod
    def from_raw(cls, raw: str | None) -> OpenAlexId | None:
        """Create OpenAlexId from raw string with normalization.

        Args:
            raw: Raw input value.

        Returns:
            New instance constructed from the input.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None


class SemanticScholarId(ValueObject[str]):
    """Semantic Scholar Paper ID.

    Semantic Scholar assigns 40-character hexadecimal identifiers
    to papers (CorpusId format has been deprecated).

    Example: 649def34f8be52c8b66281af98ae884c09aef38b

    Invariants:
        - Exactly 40 hexadecimal characters
        - Normalized to lowercase
    """

    __slots__ = ()
    _value: str
    _PATTERN = re.compile(r"^[0-9a-f]{40}$")

    def _validate(self, value: str) -> str:
        """Validate and normalize Semantic Scholar ID."""
        if not isinstance(value, str):
            raise ValueError(
                f"SemanticScholarId must be str, got {type(value).__name__}"
            )

        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("SemanticScholarId cannot be empty")

        if not self._PATTERN.match(normalized):
            raise ValueError(
                f"Invalid Semantic Scholar ID format: {value!r}. "
                f"Expected: 40-character hexadecimal string"
            )

        return normalized

    @classmethod
    def from_raw(cls, raw: str | None) -> SemanticScholarId | None:
        """Create SemanticScholarId from raw string with normalization.

        Args:
            raw: Raw input value.

        Returns:
            New instance constructed from the input.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None


class ISSN(ValueObject[str]):
    """International Standard Serial Number.

    ISSN is a unique identifier for serial publications (journals, magazines).
    Format: NNNN-NNNN where N is a digit (last digit can be 'X' for checksum 10).

    Examples: 0378-5955, 2049-3630, 0317-847X

    Invariants:
        - Eight characters in total (with or without hyphen)
        - First seven characters are digits
        - Last character is a digit or 'X' (check digit)
        - Normalized to include hyphen and uppercase X
    """

    __slots__ = ()
    _value: str
    _PATTERN = re.compile(r"^(\d{4})-?(\d{3}[\dXx])$")

    def _validate(self, value: str) -> str:
        """Validate and normalize ISSN."""
        if not isinstance(value, str):
            raise ValueError(f"ISSN must be str, got {type(value).__name__}")

        normalized = value.strip()
        if not normalized:
            raise ValueError("ISSN cannot be empty")

        match = self._PATTERN.match(normalized)
        if not match:
            raise ValueError(f"Invalid ISSN format: {value!r}. Expected: NNNN-NNNN")

        first_part = match.group(1)
        second_part = match.group(2).upper()
        return f"{first_part}-{second_part}"

    @property
    def compact(self) -> str:
        """Get ISSN without hyphen."""
        return self._value.replace("-", "")

    @classmethod
    def from_raw(cls, raw: str | None) -> ISSN | None:
        """Create ISSN from raw string with normalization.

        Args:
            raw: Raw input value.

        Returns:
            New instance constructed from the input.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None


class ORCID(ValueObject[str]):
    """Open Researcher and Contributor ID.

    ORCID is a unique identifier for researchers.
    Format: NNNN-NNNN-NNNN-NNNN where N is a digit (last digit can be 'X').

    Example: 0000-0002-1825-0097, 0000-0001-5109-3700

    Invariants:
        - 16 digits total (with or without hyphens)
        - Last character can be 'X' for checksum 10
        - Normalized to include hyphens
        - URL prefixes are automatically stripped
    """

    __slots__ = ()
    _value: str
    _PATTERN = re.compile(r"^(\d{4})-?(\d{4})-?(\d{4})-?(\d{3}[\dXx])$")
    _URL_PREFIXES = (
        *(f"{scheme}://orcid.org/" for scheme in ("https", "http")),
        "orcid.org/",
        *(f"{scheme}://orcid.org/" for scheme in ("https", "http")),
        "orcid.org/",
    )

    def _strip_url_prefix(self, value: str) -> str:
        """Strip URL prefix from ORCID if present."""
        for prefix in self._URL_PREFIXES:
            if value.lower().startswith(prefix.lower()):
                return value[len(prefix) :]
        return value

    def _validate(self, value: str) -> str:
        """Validate and normalize ORCID."""
        if not isinstance(value, str):
            raise ValueError(f"ORCID must be str, got {type(value).__name__}")

        normalized = value.strip()
        if not normalized:
            raise ValueError("ORCID cannot be empty")

        normalized = self._strip_url_prefix(normalized).strip()

        match = self._PATTERN.match(normalized)
        if not match:
            raise ValueError(
                f"Invalid ORCID format: {value!r}. Expected: NNNN-NNNN-NNNN-NNNN"
            )

        parts = [match.group(i) for i in range(1, 5)]
        parts[-1] = parts[-1].upper()
        digits = "".join(parts)
        body, check = digits[:15], digits[15]
        total = 0
        for digit in body:
            total = (total + int(digit)) * 2
        remainder = total % 11
        result = (12 - remainder) % 11
        expected = "X" if result == 10 else str(result)
        if check != expected:
            raise ValueError(
                f"Invalid ORCID checksum: {value!r} (expected check digit {expected})"
            )
        return "-".join(parts)

    @property
    def url(self) -> str:
        """Get the full ORCID URL for web access."""
        return f"https://orcid.org/{self._value}"

    @property
    def compact(self) -> str:
        """Get ORCID without hyphens."""
        return self._value.replace("-", "")

    @classmethod
    def from_raw(cls, raw: str | None) -> ORCID | None:
        """Create ORCID from raw string with normalization.

        Args:
            raw: Raw input value.

        Returns:
            New instance constructed from the input.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None
