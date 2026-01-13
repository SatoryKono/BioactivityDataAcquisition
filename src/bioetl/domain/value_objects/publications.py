"""Publication-related Value Objects for BioETL domain.

Contains Value Objects for publication identifiers:
- DOI: Digital Object Identifiers (10.1234/abc)
- PubMedId: PubMed article identifiers (PMID)
- OpenAlexId: OpenAlex Work IDs (W2741809807)
- SemanticScholarId: Semantic Scholar Paper IDs (40-char hex)
- ISSN: International Standard Serial Numbers
- ORCID: Open Researcher and Contributor IDs

These Value Objects encapsulate validation and normalization rules.
"""

from __future__ import annotations

import re

from bioetl.domain.value_objects.base import ValueObject


class DOI(ValueObject[str]):
    """Digital Object Identifier.

    Format: 10.XXXX/suffix where XXXX is a registrant code (4+ digits).
    Examples: 10.1000/xyz123, 10.12345/abc.def

    Invariants:
        - Starts with "10."
        - Has a registrant code of at least 4 digits
        - Has a non-empty suffix after "/"
        - Normalized to lowercase
        - URL prefixes (https://doi.org/, http://doi.org/, doi:) are stripped
    """

    __slots__ = ()
    _value: str

    _PATTERN = re.compile(r"^10\.\d{4,}/\S+$")
    _URL_PREFIXES = (
        "https://doi.org/",
        "http://doi.org/",
        "doi:",
        "DOI:",
    )

    def _strip_url_prefix(self, value: str) -> str:
        """Strip URL prefix from DOI if present."""
        for prefix in self._URL_PREFIXES:
            if value.lower().startswith(prefix.lower()):
                return value[len(prefix) :]
        return value

    def _validate(self, value: str) -> str:
        """Validate and normalize DOI.

        Args:
            value: Raw DOI string, optionally with URL prefix.

        Returns:
            Normalized lowercase DOI (without URL prefix).

        Raises:
            ValueError: If format is invalid.
        """
        if not isinstance(value, str):
            raise ValueError(f"DOI must be str, got {type(value).__name__}")

        normalized = value.strip()
        if not normalized:
            raise ValueError("DOI cannot be empty")

        # Strip URL prefixes and normalize to lowercase
        # Also strip whitespace after URL prefix removal (handles "https://doi.org/  10.1000/xyz  ")
        normalized = self._strip_url_prefix(normalized).strip().lower()

        if not self._PATTERN.match(normalized):
            raise ValueError(f"Invalid DOI format: {value!r}. Expected: 10.XXXX/suffix")

        return normalized

    @property
    def url(self) -> str:
        """Get the full DOI URL for web access.

        Returns:
            Complete HTTPS URL (e.g., 'https://doi.org/10.1038/nature12373').
        """
        return f"https://doi.org/{self._value}"

    @property
    def registrant_code(self) -> str:
        """Get the registrant code (organization identifier).

        The registrant code identifies the organization that registered
        the DOI. It appears after '10.' and before the '/'.

        Returns:
            Registrant code string (e.g., '1038' for Nature Publishing).
        """
        # Format: 10.XXXX/suffix
        return self._value.split("/")[0][3:]  # Skip "10."

    @classmethod
    def from_raw(cls, raw: str | None) -> DOI | None:
        """Create DOI from raw string with normalization.

        Handles common DOI formats including:
        - Plain DOI: 10.1038/nature12373
        - URL format: https://doi.org/10.1038/nature12373
        - Prefix format: doi:10.1038/nature12373

        Args:
            raw: Raw DOI string or None.

        Returns:
            DOI if valid, None if input is None, empty, or invalid.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None


class PubMedId(ValueObject[str]):
    """PubMed identifier (PMID).

    A numeric string uniquely identifying an article in PubMed.
    Stored as string to match PubMed API behavior and enable consistent
    cross-provider JOIN operations.

    Examples: "12345", "28891234"

    Invariants:
        - Must be a string containing only digits
        - Must represent a positive integer (no leading zeros except for "0")
        - Cannot exceed reasonable bounds (< 10^10)
    """

    __slots__ = ()
    _value: str
    _PATTERN = re.compile(r"^\d+$")
    _MAX_PMID = 10_000_000_000  # Reasonable upper bound

    def _coerce_to_str(self, value: str | int) -> str:
        """Coerce value to string, raising ValueError on failure."""
        if isinstance(value, bool):
            raise ValueError(f"PubMedId must be str or int, got {type(value).__name__}")
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str):
            return value.strip()
        raise ValueError(f"PubMedId must be str or int, got {type(value).__name__}")

    def _validate(self, value: str | int) -> str:
        """Validate and normalize PubMed ID to string."""
        str_value = self._coerce_to_str(value)

        if not str_value:
            raise ValueError("PubMed ID cannot be empty")
        if not self._PATTERN.match(str_value):
            raise ValueError(
                f"Invalid PubMed ID format: {value!r}. Must contain only digits."
            )

        int_value = int(str_value)
        if int_value <= 0:
            raise ValueError(f"PubMed ID must be positive: {str_value}")
        if int_value >= self._MAX_PMID:
            raise ValueError(f"PubMed ID too large: {str_value}")

        return str(int_value)

    @property
    def as_int(self) -> int:
        """Get the PMID as integer for numeric operations."""
        return int(self._value)

    @classmethod
    def from_raw(cls, raw: str | int | None) -> PubMedId | None:
        """Create PubMedId from raw value with normalization.

        Args:
            raw: Raw PMID string, integer, or None.

        Returns:
            PubMedId if valid, None if input is None, empty, or invalid.
        """
        if raw is None:
            return None
        if isinstance(raw, str) and not raw.strip():
            return None
        try:
            # str() is idempotent on strings, converts int to str
            return cls(str(raw))
        except ValueError:
            return None


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
        """Validate and normalize OpenAlex ID.

        Args:
            value: Raw OpenAlex ID string, optionally with URL prefix.

        Returns:
            Normalized uppercase OpenAlex ID.

        Raises:
            ValueError: If format is invalid.
        """
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
        """Get the full OpenAlex URL for web access.

        Returns:
            Complete HTTPS URL (e.g., 'https://openalex.org/W2741809807').
        """
        return f"{self._URL_PREFIX}{self._value}"

    @property
    def numeric_id(self) -> int:
        """Get the numeric part of the OpenAlex ID.

        Returns:
            Integer portion of the identifier (e.g., 2741809807 for W2741809807).
        """
        return int(self._value[1:])

    @classmethod
    def from_raw(cls, raw: str | None) -> OpenAlexId | None:
        """Create OpenAlexId from raw string with normalization.

        Handles common OpenAlex ID formats including:
        - Plain ID: W2741809807
        - URL format: https://openalex.org/W2741809807

        Args:
            raw: Raw OpenAlex ID string or None.

        Returns:
            OpenAlexId if valid, None if input is None, empty, or invalid.
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
        """Validate and normalize Semantic Scholar ID.

        Args:
            value: Raw Semantic Scholar ID string.

        Returns:
            Normalized lowercase Semantic Scholar ID.

        Raises:
            ValueError: If format is invalid.
        """
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
            raw: Raw Semantic Scholar ID string or None.

        Returns:
            SemanticScholarId if valid, None if input is None, empty, or invalid.
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
    Format: XXXX-XXXX where X is a digit (last digit can be 'X' for checksum 10).

    Examples: 0378-5955, 2049-3630, 0317-847X

    Invariants:
        - Eight characters in total (with or without hyphen)
        - First seven characters are digits
        - Last character is a digit or 'X' (check digit)
        - Normalized to include hyphen and uppercase X
    """

    __slots__ = ()
    _value: str
    # Pattern matches XXXX-XXXX or XXXXXXXX format
    _PATTERN = re.compile(r"^(\d{4})-?(\d{3}[\dXx])$")

    def _validate(self, value: str) -> str:
        """Validate and normalize ISSN.

        Args:
            value: Raw ISSN string.

        Returns:
            Normalized ISSN in XXXX-XXXX format.

        Raises:
            ValueError: If format is invalid.
        """
        if not isinstance(value, str):
            raise ValueError(f"ISSN must be str, got {type(value).__name__}")

        normalized = value.strip()
        if not normalized:
            raise ValueError("ISSN cannot be empty")

        match = self._PATTERN.match(normalized)
        if not match:
            raise ValueError(
                f"Invalid ISSN format: {value!r}. Expected: XXXX-XXXX"
            )

        # Normalize to XXXX-XXXX format with uppercase X
        first_part = match.group(1)
        second_part = match.group(2).upper()
        return f"{first_part}-{second_part}"

    @property
    def compact(self) -> str:
        """Get ISSN without hyphen.

        Returns:
            8-character ISSN string without hyphen.
        """
        return self._value.replace("-", "")

    @classmethod
    def from_raw(cls, raw: str | None) -> ISSN | None:
        """Create ISSN from raw string with normalization.

        Args:
            raw: Raw ISSN string or None.

        Returns:
            ISSN if valid, None if input is None, empty, or invalid.
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
    Format: XXXX-XXXX-XXXX-XXXX where X is a digit (last digit can be 'X').

    Example: 0000-0002-1825-0097, 0000-0001-5109-3700

    Invariants:
        - 16 digits total (with or without hyphens)
        - Last character can be 'X' for checksum 10
        - Normalized to include hyphens
        - URL prefixes are automatically stripped
    """

    __slots__ = ()
    _value: str
    # Pattern matches XXXX-XXXX-XXXX-XXXX or 16-char format
    _PATTERN = re.compile(r"^(\d{4})-?(\d{4})-?(\d{4})-?(\d{3}[\dXx])$")
    _URL_PREFIXES = (
        "https://orcid.org/",
        "http://orcid.org/",
        "orcid.org/",
    )

    def _strip_url_prefix(self, value: str) -> str:
        """Strip URL prefix from ORCID if present."""
        for prefix in self._URL_PREFIXES:
            if value.lower().startswith(prefix.lower()):
                return value[len(prefix) :]
        return value

    def _validate(self, value: str) -> str:
        """Validate and normalize ORCID.

        Args:
            value: Raw ORCID string, optionally with URL prefix.

        Returns:
            Normalized ORCID in XXXX-XXXX-XXXX-XXXX format.

        Raises:
            ValueError: If format is invalid.
        """
        if not isinstance(value, str):
            raise ValueError(f"ORCID must be str, got {type(value).__name__}")

        normalized = value.strip()
        if not normalized:
            raise ValueError("ORCID cannot be empty")

        # Strip URL prefixes
        normalized = self._strip_url_prefix(normalized).strip()

        match = self._PATTERN.match(normalized)
        if not match:
            raise ValueError(
                f"Invalid ORCID format: {value!r}. "
                f"Expected: XXXX-XXXX-XXXX-XXXX"
            )

        # Normalize to XXXX-XXXX-XXXX-XXXX format with uppercase X
        parts = [match.group(i) for i in range(1, 5)]
        parts[-1] = parts[-1].upper()
        return "-".join(parts)

    @property
    def url(self) -> str:
        """Get the full ORCID URL for web access.

        Returns:
            Complete HTTPS URL (e.g., 'https://orcid.org/0000-0002-1825-0097').
        """
        return f"https://orcid.org/{self._value}"

    @property
    def compact(self) -> str:
        """Get ORCID without hyphens.

        Returns:
            16-character ORCID string without hyphens.
        """
        return self._value.replace("-", "")

    @classmethod
    def from_raw(cls, raw: str | None) -> ORCID | None:
        """Create ORCID from raw string with normalization.

        Handles common ORCID formats including:
        - Plain ID: 0000-0002-1825-0097
        - URL format: https://orcid.org/0000-0002-1825-0097
        - Compact format: 0000000218250097

        Args:
            raw: Raw ORCID string or None.

        Returns:
            ORCID if valid, None if input is None, empty, or invalid.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None
