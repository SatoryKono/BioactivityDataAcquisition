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
from bioetl.domain.services._date_helpers import (
    format_date_parts as _format_date_parts,
)
from bioetl.domain.services._date_helpers import (
    normalize_partial_date as _normalize_partial_date,
)
from bioetl.domain.services.author_normalization_service import (
    AuthorNormalizationService,
)
from bioetl.domain.services.data_normalization_config import DataNormalizationConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_DOI_URL_PREFIXES = ("https://doi.org/", "http://doi.org/", "doi:")


@dataclass(frozen=True, slots=True)
class DefaultDataNormalizationService:
    """Default implementation of data normalization service.

    Orchestrates text and data normalization for publication metadata.
    Delegates author/affiliation normalization to AuthorNormalizationService.
    """

    config: DataNormalizationConfig = field(default_factory=DataNormalizationConfig)
    _author_service: AuthorNormalizationService = field(
        default_factory=AuthorNormalizationService, init=False
    )

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
        """Parse various author formats into a list of names.

        .. deprecated:: 2.2.0
            Use :meth:`normalize_author_list` instead for unified author normalization
            with hashing. This method will be removed in version 3.0.0.

        Args:
            authors: Author data in various formats.

        Returns:
            List of author name strings.
        """
        import warnings

        warnings.warn(
            "parse_authors_to_list() is deprecated and will be removed in version 3.0.0. "
            "Use normalize_author_list() instead for unified author normalization.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Delegate to AuthorNormalizationService (same parsing logic)
        return self._author_service._parse_author_names(authors)

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

        Delegates to _date_helpers module. See _date_helpers.normalize_partial_date
        for full documentation.
        """
        return _normalize_partial_date(date_str)

    def format_date_parts(
        self, date_parts: Sequence[Sequence[int]] | None
    ) -> str | None:
        """Format CrossRef date-parts [[year, month?, day?]] to ISO YYYY-MM-DD.

        Delegates to _date_helpers module. See _date_helpers.format_date_parts
        for full documentation.
        """
        return _format_date_parts(date_parts)

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

        # Step 2: Remove control characters
        normalized = _CONTROL_CHARS_PATTERN.sub("", normalized)

        # Step 3: Unicode NFC normalization (canonical composition)
        normalized = unicodedata.normalize("NFC", normalized)

        # Step 4: Collapse multiple whitespace to single space
        normalized = _WHITESPACE_PATTERN.sub(" ", normalized)

        # Step 5: Trim leading/trailing whitespace
        normalized = normalized.strip()

        return normalized if normalized else None

    def normalize_author_list(
        self,
        authors: list[str] | list[dict[str, Any]] | str | None,
        salt: str,
    ) -> str | None:
        """Parse, normalize, and hash author names to JSON string.

        Delegates to AuthorNormalizationService.

        Args:
            authors: Author data in any supported format (list, dict, string, JSON).
            salt: Salt for PII hashing per RULES.md §5.4.

        Returns:
            JSON string of hashed author names or None if empty.
        """
        return self._author_service.normalize_author_list(authors, salt)

    def normalize_affiliations(
        self,
        affiliations: list[str] | list[dict[str, Any]] | None,
    ) -> str | None:
        """Extract, normalize, and deduplicate affiliations to JSON string.

        Delegates to AuthorNormalizationService.

        Args:
            affiliations: Affiliation data as strings or dicts.

        Returns:
            JSON string of unique normalized affiliations or None if empty.
        """
        return self._author_service.normalize_affiliations(affiliations)

    def extract_affiliations_from_authors(
        self,
        authors: list[dict[str, Any]],
    ) -> list[str]:
        """Extract unique affiliations from author objects.

        Delegates to AuthorNormalizationService.

        Args:
            authors: List of author dicts with 'affiliations' key.

        Returns:
            List of unique normalized affiliation strings (sorted).
        """
        return self._author_service.extract_affiliations_from_authors(authors)
