"""Data normalization service for text and publication metadata.

Pure domain service (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from html import unescape
from typing import TYPE_CHECKING, Any

from bioetl.domain.services.data_normalization_config import DataNormalizationConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_DATE_FORMATS = {3: "{0:04d}-{1:02d}-{2:02d}", 2: "{0:04d}-{1:02d}", 1: "{0:04d}"}


@dataclass(frozen=True, slots=True)
class DefaultDataNormalizationService:
    """Default implementation of data normalization service.

    Orchestrates text and data normalization for publication metadata.
    """

    config: DataNormalizationConfig = field(default_factory=DataNormalizationConfig)

    def normalize_doi(self, doi: str | None) -> str | None:
        """Normalize DOI to lowercase, stripped format."""
        return doi.strip().lower() if doi else None

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
        return json.dumps(hashed, ensure_ascii=True)

    def _hash_pii(self, value: str, salt: str) -> str:
        """Hash a PII value with salt using SHA-256."""
        return hashlib.sha256(f"{salt}{value}".encode()).hexdigest()

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
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _filter_json_authors(self, items: list[Any]) -> list[str]:
        """Filter and convert JSON array items to author strings."""
        return [str(a).strip() for a in items if a is not None and str(a).strip()]

    def _parse_delimited(self, text: str) -> list[str]:
        """Parse delimited string (semicolon or comma separated)."""
        delimiter = ";" if ";" in text else ","
        parts = text.split(delimiter) if delimiter in text else [text]
        return [a.strip() for a in parts if a.strip()]

    def format_date_parts(
        self, date_parts: Sequence[Sequence[int]] | None
    ) -> str | None:
        """Format CrossRef date-parts [[year, month?, day?]] to ISO string."""
        if not date_parts or not date_parts[0]:
            return None
        parts = date_parts[0]
        fmt = _DATE_FORMATS.get(min(len(parts), 3))
        return fmt.format(*parts) if fmt else None
