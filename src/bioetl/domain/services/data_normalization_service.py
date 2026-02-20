"""Data normalization service for text and publication metadata.

Pure domain service (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from html import unescape
from typing import TYPE_CHECKING, Any

from bioetl.domain.serialization import deserialize_from_json, serialize_to_json
from bioetl.domain.services.data_normalization_config import DataNormalizationConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0e-\x1f\x7f-\x9f]")
_DATE_FULL_FMT = "{0:04d}-{1:02d}-{2:02d}"
_DOI_URL_PREFIXES = ("https://doi.org/", "http://doi.org/", "doi:")

# Partial date patterns for end of period normalization
_FULL_DATE_LEN = 10  # YYYY-MM-DD
_PARTIAL_MONTH_LEN = 7  # YYYY-MM
_PARTIAL_YEAR_LEN = 4  # YYYY


@dataclass(frozen=True, slots=True)
class DefaultDataNormalizationService:
    """Default implementation of data normalization service.

    Orchestrates text and data normalization for publication metadata.
    """

    config: DataNormalizationConfig = field(default_factory=DataNormalizationConfig)

    def normalize_doi(self, doi: str | None) -> str | None:
        """Normalize DOI to lowercase, stripped format.

        Handles DOIs in various formats:
        - Bare DOI: "10.1038/nature12373"
        - HTTPS URL: "https://doi.org/10.1038/nature12373"
        - HTTP URL: "http://doi.org/10.1038/nature12373"
        - doi: prefix: "doi:10.1038/nature12373"

        Args:
            doi: DOI string in any supported format.

        Returns:
            Normalized bare DOI (lowercase, stripped) or None if input is None/empty.
        """
        if not doi:
            return None
        stripped = self._strip_doi_prefix(doi)
        result = stripped.strip().lower()
        return result if result else None

    def _strip_doi_prefix(self, doi: str) -> str:
        """Strip known DOI URL prefixes (https://doi.org/, http://doi.org/, doi:)."""
        for prefix in _DOI_URL_PREFIXES:
            if doi.startswith(prefix):
                return doi[len(prefix) :]
        return doi

    def normalize_pmid(self, pmid: str | int | None) -> str | None:
        """Normalize PubMed ID to string format. Returns None for invalid inputs."""
        str_value = self._pmid_to_string(pmid)
        return self._validate_pmid_string(str_value) if str_value else None

    def _pmid_to_string(self, pmid: str | int | None) -> str | None:
        """Convert PMID to string, rejecting invalid types."""
        if pmid is None or isinstance(pmid, bool):
            return None
        if isinstance(pmid, (int, str)):
            result = str(pmid).strip()
            return result if result else None
        return None

    def _validate_pmid_string(self, str_value: str) -> str | None:
        """Validate and normalize PMID string."""
        if not str_value.isdigit():
            return None
        int_value = int(str_value)
        return str(int_value) if int_value > 0 else None

    def normalize_year(self, year: int | None) -> tuple[int | None, bool]:
        """Validate publication year. Returns (year, is_warning) tuple."""
        if year is None:
            return None, False
        if self.config.min_publication_year <= year <= self.config.max_publication_year:
            return year, False
        return year, True

    def normalize_authors(
        self, authors: list[str] | str | None, salt: str
    ) -> str | None:
        """Parse, hash, and serialize author names. Returns JSON string or None."""
        author_list = self.parse_authors_to_list(authors)
        if not author_list:
            return None
        hashed = [self._hash_pii(name, salt) for name in author_list]
        return serialize_to_json(hashed, ensure_ascii=True)

    def _hash_pii(self, value: str, salt: str) -> str:
        """Hash a PII value with salt using SHA-256 per RULES.md §5.4.

        Normalization: strip whitespace, lowercase before hashing.
        Formula: sha256(lowercase(value) + SALT)
        """
        normalized = value.strip().lower()
        return hashlib.sha256(f"{normalized}{salt}".encode()).hexdigest()

    def strip_html_tags(self, text: str | None) -> str | None:
        """Remove HTML tags, decode entities, normalize whitespace."""
        if not text:
            return None
        clean = _HTML_TAG_PATTERN.sub("", text)
        clean = unescape(clean)
        clean = _WHITESPACE_PATTERN.sub(" ", clean).strip()
        return clean if clean else None

    def normalize_oa_status(self, status: str | None) -> str | None:
        """Normalize Open Access status to lowercase."""
        if not status:
            return None
        stripped = status.strip()
        return stripped.lower() if stripped else None

    def normalize_string(self, value: str | None) -> str | None:
        """Normalize string by stripping whitespace."""
        if value is None:
            return None
        stripped = value.strip()
        return stripped if stripped else None

    def normalize_to_string(self, value: Any) -> str | None:
        """Convert value to string, strip whitespace, return None if empty."""
        if value is None:
            return None
        str_value = str(value).strip()
        return str_value if str_value else None

    def parse_authors_to_list(self, authors: list[str] | str | None) -> list[str]:
        """Parse various author formats into a list of names."""
        if authors is None:
            return []
        if isinstance(authors, list):
            return self._parse_authors_from_list(authors)
        if isinstance(authors, str) and authors.strip():
            return self._parse_authors_string(authors.strip())
        return []

    def _parse_authors_from_list(self, authors: list[Any]) -> list[str]:
        """Parse author list, filtering non-strings and empty values."""
        return [a.strip() for a in authors if isinstance(a, str) and a.strip()]

    def _parse_authors_string(self, text: str) -> list[str]:
        """Parse string as JSON or delimited format."""
        json_result = self._parse_authors_from_json(text)
        return json_result if json_result is not None else self._parse_delimited(text)

    def _parse_authors_from_json(self, text: str) -> list[str] | None:
        """Try to parse JSON array of authors."""
        if not text.startswith("["):
            return None
        parsed = self._try_json_loads(text)
        if isinstance(parsed, list):
            return self._filter_json_authors(parsed)
        return None

    def _try_json_loads(self, text: str) -> Any:
        """Attempt JSON parsing, returning None on failure."""
        try:
            return deserialize_from_json(text)
        except ValueError:
            return None

    def _filter_json_authors(self, items: list[Any]) -> list[str]:
        """Filter and convert JSON array items to author strings."""
        return [str(a).strip() for a in items if a is not None and str(a).strip()]

    def _parse_delimited(self, text: str) -> list[str]:
        """Parse delimited string (semicolon or comma separated)."""
        delimiter = ";" if ";" in text else ","
        parts = text.split(delimiter) if delimiter in text else [text]
        return [a.strip() for a in parts if a.strip()]

    def normalize_partial_date(self, date_str: str | None) -> str | None:
        """Normalize partial date to full YYYY-MM-DD format (end of period).

        Partial dates are normalized to the END of the period:
        - YYYY-MM → YYYY-MM-30 (end of month, day 30 for simplicity)
        - YYYY → YYYY-12-31 (end of year)
        - YYYY-MM-DD → unchanged
        - None/empty → None

        Args:
            date_str: Date string in partial or full ISO format.

        Returns:
            Full ISO date string (YYYY-MM-DD), or None if invalid.
        """
        cleaned = self._clean_date_string(date_str)
        if not cleaned:
            return None
        return self._normalize_by_length(cleaned)

    def _clean_date_string(self, date_str: str | None) -> str | None:
        """Strip whitespace from date string, return None if empty."""
        if not date_str:
            return None
        stripped = date_str.strip()
        return stripped if stripped else None

    def _normalize_by_length(self, date_str: str) -> str | None:
        """Normalize date string based on length pattern."""
        length = len(date_str)
        if length == _FULL_DATE_LEN:
            return self._validate_full_date(date_str)
        if length == _PARTIAL_MONTH_LEN:
            return self._normalize_partial_month(date_str)
        if length == _PARTIAL_YEAR_LEN:
            return self._normalize_partial_year(date_str)
        return None

    def _validate_full_date(self, date_str: str) -> str | None:
        """Validate YYYY-MM-DD format, return as-is if valid."""
        if date_str[4] == "-" and date_str[7] == "-":
            return date_str
        return None

    def _normalize_partial_month(self, date_str: str) -> str | None:
        """Normalize YYYY-MM to YYYY-MM-30 (end of month)."""
        if date_str[4] == "-":
            return f"{date_str}-30"
        return None

    def _normalize_partial_year(self, date_str: str) -> str | None:
        """Normalize YYYY to YYYY-12-31 (end of year)."""
        if date_str.isdigit():
            return f"{date_str}-12-31"
        return None

    def format_date_parts(
        self, date_parts: Sequence[Sequence[int]] | None
    ) -> str | None:
        """Format CrossRef date-parts [[year, month?, day?]] to ISO YYYY-MM-DD string.

        Uses end-of-period normalization for partial dates:
        - Complete date [[2024, 3, 15]]: returns "2024-03-15"
        - Month-only [[2024, 3]]: returns "2024-03-31" (last day of month)
        - Year-only [[2024]]: returns "2024-12-31" (last day of year)
        """
        parts = self._extract_date_parts(date_parts)
        if not parts:
            return None
        return self._format_parts_to_date(parts)

    def _extract_date_parts(
        self, date_parts: Sequence[Sequence[int]] | None
    ) -> Sequence[int] | None:
        """Extract first date-parts array if valid, else None."""
        if not date_parts:
            return None
        parts = date_parts[0]
        return parts if parts else None

    def _format_parts_to_date(self, parts: Sequence[int]) -> str:
        """Format date parts to YYYY-MM-DD with end-of-period normalization."""
        from calendar import monthrange

        year = parts[0]
        if len(parts) >= 3:
            return _DATE_FULL_FMT.format(year, parts[1], parts[2])
        if len(parts) == 2:
            return _DATE_FULL_FMT.format(year, parts[1], monthrange(year, parts[1])[1])
        return _DATE_FULL_FMT.format(year, 12, 31)

    def normalize_title(self, title: str | None) -> str | None:
        """Normalize publication title: HTML cleanup, whitespace, unicode NFC, trim.

        Normalization steps:
        1. Strip HTML tags and decode entities
        2. Remove control characters (0x00-0x1F, 0x7F-0x9F)
        3. Normalize unicode to NFC form
        4. Collapse multiple whitespace to single space
        5. Trim leading/trailing whitespace

        Args:
            title: Raw title string (may contain HTML tags, extra whitespace).

        Returns:
            Normalized title or None if input is None/empty after normalization.

        Examples:
            >>> service.normalize_title("<b>Hello</b>  World")
            'Hello World'
            >>> service.normalize_title("Café")  # é normalized to NFC
            'Café'
        """
        return self._normalize_text_field(title)

    def normalize_abstract(self, abstract: str | None) -> str | None:
        """Normalize publication abstract: HTML cleanup, whitespace, unicode NFC, trim.

        Uses same normalization pipeline as normalize_title():
        1. Strip HTML tags and decode entities
        2. Remove control characters
        3. Normalize unicode to NFC form
        4. Collapse multiple whitespace to single space
        5. Trim leading/trailing whitespace

        Args:
            abstract: Raw abstract string (may contain HTML tags, extra whitespace).

        Returns:
            Normalized abstract or None if input is None/empty after normalization.

        Examples:
            >>> service.normalize_abstract("<p>Study of α-particles</p>")
            'Study of α-particles'
        """
        return self._normalize_text_field(abstract)

    def _normalize_text_field(self, text: str | None) -> str | None:
        """Internal method: normalize text field through complete pipeline.

        Pipeline steps (order matters):
        1. Strip HTML tags and decode HTML entities
        2. Remove control characters (0x00-0x1F, 0x7F-0x9F)
        3. Normalize unicode to NFC (canonical composition)
        4. Collapse multiple whitespace (spaces, tabs, newlines) to single space
        5. Trim leading/trailing whitespace

        Args:
            text: Raw text to normalize.

        Returns:
            Normalized text or None if input is None/empty after normalization.
        """
        if not text:
            return None

        # Step 1: Strip HTML tags and decode entities
        normalized = _HTML_TAG_PATTERN.sub("", text)
        normalized = unescape(normalized)

        # Step 2: Remove non-whitespace control characters (NUL, DEL, C1 controls)
        # Note: \t, \n, \r are handled by whitespace collapse in step 4
        normalized = _CONTROL_CHARS_PATTERN.sub("", normalized)

        # Step 3: Unicode NFC normalization (canonical composition)
        normalized = unicodedata.normalize("NFC", normalized)

        # Step 4: Collapse multiple whitespace to single space
        normalized = _WHITESPACE_PATTERN.sub(" ", normalized)

        # Step 5: Trim leading/trailing whitespace
        normalized = normalized.strip()

        return normalized if normalized else None
