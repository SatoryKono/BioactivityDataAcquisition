"""Publication-related Value Objects for BioETL domain.

Contains Value Objects for publication identifiers:
- DOI: Digital Object Identifiers (10.1234/abc)
- PubMedId: PubMed article identifiers (PMID)

These Value Objects encapsulate validation and normalization rules.
"""

from __future__ import annotations

import re

from bioetl.domain.normalization.identifiers import PMID_MAX_EXCLUSIVE
from bioetl.domain.value_objects.base import ValueObject

__all__ = [
    "DOI",
    "PubMedId",
]


class DOI(ValueObject[str]):
    """Digital Object Identifier.

    Format: 10.NNNN/suffix where NNNN is a registrant code (4+ digits).
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
        *(f"{scheme}://doi.org/" for scheme in ("https", "http")),
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
            raise ValueError(f"Invalid DOI format: {value!r}. Expected: 10.NNNN/suffix")

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
        # Format: 10.NNNN/suffix
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
    _MAX_PMID = PMID_MAX_EXCLUSIVE  # Keep ValueObject bound aligned with helper seam

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
