"""Author and affiliation normalization helpers.

Pure functions extracted from AuthorNormalizationService to keep class under
LOC and CC limits. No I/O per RULES.md §1.1.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from html import unescape
from typing import Any

from bioetl.domain.serialization import deserialize_from_json

# Regex patterns
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

# Keys to probe when extracting affiliation from a dict
_AFFILIATION_KEYS = ("name", "display_name", "affiliation")


def hash_author_name(name: str, salt: str) -> str:
    """Hash author name with SHA-256: sha256(lowercase(name) + salt)."""
    normalized = name.strip().lower()
    return hashlib.sha256(f"{normalized}{salt}".encode()).hexdigest()


def parse_author_names(
    authors: list[str] | list[dict[str, Any]] | str,
) -> list[str]:
    """Parse various author formats to list of name strings."""
    if isinstance(authors, list):
        return [n for a in authors if (n := _extract_name_from_item(a))]
    if isinstance(authors, str):
        return parse_author_string(authors)
    return []


def _extract_name_from_item(item: Any) -> str | None:
    """Extract author name from a string or dict item."""
    if isinstance(item, str):
        stripped = item.strip()
        return stripped if stripped else None
    if isinstance(item, dict):
        name = item.get("name")
        if isinstance(name, str):
            stripped = name.strip()
            return stripped if stripped else None
    return None


def parse_author_string(text: str) -> list[str]:
    """Parse author string (JSON or delimited format)."""
    text = text.strip()
    if not text:
        return []
    if text.startswith("["):
        json_result = try_parse_json_authors(text)
        if json_result is not None:
            return json_result
    return parse_delimited_authors(text)


def try_parse_json_authors(text: str) -> list[str] | None:
    """Try to parse JSON array of authors. Returns None on parse failure."""
    try:
        parsed = deserialize_from_json(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, list):
        return None
    return [n for item in parsed if (n := _extract_name_from_item(item))]


def parse_delimited_authors(text: str) -> list[str]:
    """Parse semicolon- or comma-delimited author string."""
    delimiter = ";" if ";" in text else ","
    parts = text.split(delimiter) if delimiter in text else [text]
    return [part.strip() for part in parts if part.strip()]


def extract_affiliation_strings(
    affiliations: list[str] | list[dict[str, Any]],
) -> list[str]:
    """Extract affiliation strings from a mixed list of strings and dicts."""
    strings: list[str] = []
    for aff in affiliations:
        extracted = _extract_single_affiliation(aff)
        if extracted:
            strings.append(extracted)
    return strings


def _extract_single_affiliation(aff: Any) -> str | None:
    """Extract affiliation string from a single item (str or dict)."""
    if isinstance(aff, str):
        stripped = aff.strip()
        return stripped if stripped else None
    if isinstance(aff, dict):
        for key in _AFFILIATION_KEYS:
            value = aff.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def normalize_affiliation_string(text: str) -> str | None:
    """Normalize affiliation: HTML → whitespace → control chars → NFC → trim."""
    if not text:
        return None
    normalized = _HTML_TAG_PATTERN.sub("", text)
    normalized = unescape(normalized)
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    normalized = _CONTROL_CHARS_PATTERN.sub("", normalized)
    normalized = unicodedata.normalize("NFC", normalized)
    normalized = normalized.strip()
    return normalized if normalized else None


def deduplicate_case_insensitive(strings: list[str]) -> list[str]:
    """Deduplicate strings case-insensitively, keeping first occurrence."""
    seen: dict[str, str] = {}
    for s in strings:
        key = s.lower()
        if key not in seen:
            seen[key] = s
    return list(seen.values())


def collect_affiliations_from_authors(
    authors: list[dict[str, Any]],
) -> list[str]:
    """Collect raw affiliation strings from author dicts."""
    result: list[str] = []
    for author in authors:
        if not isinstance(author, dict):
            continue
        aff_data = author.get("affiliations")
        if not aff_data:
            continue
        if isinstance(aff_data, list):
            result.extend(str(a) for a in aff_data if a)
        elif isinstance(aff_data, str):
            result.append(aff_data)
    return result
