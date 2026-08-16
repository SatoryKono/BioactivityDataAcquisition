"""Author and affiliation normalization helpers."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from html import unescape

from bioetl.domain.serialization import deserialize_from_json
from bioetl.domain.types import JsonDict

__all__ = [
    "collect_affiliations_from_authors",
    "deduplicate_case_insensitive",
    "extract_affiliation_strings",
    "hash_author_name",
    "normalize_affiliation_string",
    "normalize_to_surname_initial",
    "parse_author_names",
    "parse_author_string",
    "parse_delimited_authors",
    "try_parse_json_authors",
]

# Regex patterns
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

# Keys to probe when extracting affiliation from a dict
_AFFILIATION_KEYS = ("name", "display_name", "affiliation")


def hash_author_name(name: str, salt: str) -> str:
    """Hash author name with SHA-256: sha256(lowercase(name) + salt).

    Args:
        name: Author name string to hash (stripped and lowercased before hashing).
        salt: Cryptographic salt appended before hashing for PII compliance.

    Returns:
        SHA-256 hex digest string of the normalized author name and salt.
    """
    normalized = name.strip().lower()
    return hashlib.sha256(f"{normalized}{salt}".encode()).hexdigest()


def parse_author_names(
    authors: list[str] | list[JsonDict] | str,
) -> list[str]:
    """Parse various author formats to list of name strings.

    Args:
        authors: Author data as a list of strings, list of dicts with 'name' key,
            or a delimited/JSON string.

    Returns:
        List of author name strings extracted from the input.
    """
    if isinstance(authors, list):
        return [n for a in authors if (n := _extract_name_from_item(a))]
    if isinstance(authors, str):
        return parse_author_string(authors)
    return []


def _strip_or_none(value: object) -> str | None:
    """Strip string and return None if empty or non-string."""
    return value.strip() or None if isinstance(value, str) else None


def _extract_name_from_item(item: object) -> str | None:
    """Extract author name from a string or dict item."""
    if isinstance(item, str):
        return _strip_or_none(item)
    if isinstance(item, dict):
        return _strip_or_none(item.get("name"))
    return None


def parse_author_string(text: str) -> list[str]:
    """Parse author string (JSON or delimited format).

    Tries JSON array parsing first; falls back to semicolon/comma delimiter.

    Args:
        text: Author string in JSON array format or delimited (';' or ',') format.

    Returns:
        List of author name strings parsed from the input text.
    """
    text = text.strip()
    if not text:
        return []
    if text.startswith("["):
        json_result = try_parse_json_authors(text)
        if json_result is not None:
            return json_result
    return parse_delimited_authors(text)


def try_parse_json_authors(text: str) -> list[str] | None:
    """Try to parse JSON array of authors. Returns None on parse failure.

    Args:
        text: String that may be a JSON array of author strings or dicts.

    Returns:
        List of author name strings if parsed successfully, None on parse failure.
    """
    try:
        parsed = deserialize_from_json(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, list):
        return None
    return [n for item in parsed if (n := _extract_name_from_item(item))]


def parse_delimited_authors(text: str) -> list[str]:
    """Parse semicolon- or comma-delimited author string.

    Args:
        text: Author string delimited by semicolons (preferred) or commas.

    Returns:
        List of author name strings split by the detected delimiter.
    """
    delimiter = ";" if ";" in text else ","
    parts = text.split(delimiter) if delimiter in text else [text]
    return [part.strip() for part in parts if part.strip()]


def extract_affiliation_strings(
    affiliations: list[str] | list[JsonDict],
) -> list[str]:
    """Extract affiliation strings from a mixed list of strings and dicts.

    Args:
        affiliations: List of affiliation items as plain strings or dicts
            with known keys ('name', 'display_name', 'affiliation').

    Returns:
        List of extracted affiliation strings, with empty values excluded.
    """
    strings: list[str] = []
    for aff in affiliations:
        extracted = _extract_single_affiliation(aff)
        if extracted:
            strings.append(extracted)
    return strings


def _extract_affiliation_from_dict(
    aff: JsonDict,
) -> str | None:
    """Extract first non-empty affiliation value from known keys."""
    for key in _AFFILIATION_KEYS:
        result = _strip_or_none(aff.get(key))
        if result:
            return result
    return None


def _extract_single_affiliation(aff: object) -> str | None:
    """Extract affiliation string from a single item (str or dict)."""
    if isinstance(aff, str):
        return _strip_or_none(aff)
    if isinstance(aff, dict):
        return _extract_affiliation_from_dict(aff)
    return None


def normalize_affiliation_string(text: str) -> str | None:
    """Normalize affiliation: HTML → whitespace → control chars → NFC → trim.

    Args:
        text: Raw affiliation string that may contain HTML, control characters,
            or inconsistent whitespace.

    Returns:
        Normalized affiliation string, or None if result is empty.
    """
    if not text:
        return None
    # Unescape first so entity-encoded markup (e.g. &lt;b&gt;) is stripped too.
    normalized = unescape(text)
    normalized = _HTML_TAG_PATTERN.sub("", normalized)
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    normalized = _CONTROL_CHARS_PATTERN.sub("", normalized)
    normalized = unicodedata.normalize("NFC", normalized)
    normalized = normalized.strip()
    return normalized if normalized else None


def deduplicate_case_insensitive(strings: list[str]) -> list[str]:
    """Deduplicate strings case-insensitively, keeping first occurrence.

    Args:
        strings: List of strings that may contain case-variant duplicates.

    Returns:
        List of deduplicated strings preserving original casing of first occurrence.
    """
    seen: dict[str, str] = {}
    for s in strings:
        key = s.casefold()
        if key not in seen:
            seen[key] = s
    return list(seen.values())


def _is_initials(token: str) -> bool:
    """Check if token looks like initials (1-3 uppercase letters, optionally dotted)."""
    cleaned = token.replace(".", "")
    return 1 <= len(cleaned) <= 3 and cleaned.isalpha() and cleaned.isupper()


def _surname_initial_from_comma(name: str) -> str | None:
    """Parse ``LastName, Rest`` format (PubMed / inverted)."""
    parts = name.split(",", 1)
    surname = parts[0].strip()
    rest = parts[1].strip()
    if not surname:
        return None
    if not rest:
        return surname
    return f"{surname}_{rest[0].upper()}"


def _surname_initial_from_tokens(tokens: list[str]) -> str:
    """Parse space-separated tokens into ``Surname_F`` key."""
    # Format: "LastName Initials" (ChEMBL: "Smith JA", "Zhou X")
    if _is_initials(tokens[-1]):
        surname = " ".join(tokens[:-1])
        initial = tokens[-1].replace(".", "")[0].upper()
        return f"{surname}_{initial}"

    # Format: "Initial. LastName" (e.g. "X. Zhou")
    if _is_initials(tokens[0]):
        surname = " ".join(tokens[1:])
        initial = tokens[0].replace(".", "")[0].upper()
        return f"{surname}_{initial}"

    # Format: "FirstName [Middle...] LastName" (CrossRef, OpenAlex, S2)
    return f"{tokens[-1]}_{tokens[0][0].upper()}"


def normalize_to_surname_initial(name: str) -> str | None:
    """Convert author name to ``Surname_F`` short key.

    Handles multiple formats: inverted ('Last, First'), ChEMBL ('Last FI'),
    and natural ('First [Middle] Last').

    Args:
        name: Author name string in any supported format.

    Returns:
        Short key string in Surname_Initial format (e.g., 'Smith_J'),
        or None for empty input.
    """
    if not name or not name.strip():
        return None
    name = name.strip()

    # Format: "LastName, Rest" (PubMed / inverted)
    if "," in name:
        return _surname_initial_from_comma(name)

    # Split on whitespace
    tokens = name.split()
    if len(tokens) == 1:
        return tokens[0]

    return _surname_initial_from_tokens(tokens)


def _collect_affiliation_values(aff_data: object) -> list[str]:
    """Extract affiliation strings from a single author's affiliation field."""
    if not isinstance(aff_data, list | str):
        return []
    items = aff_data if isinstance(aff_data, list) else [aff_data]
    extracted = (_extract_single_affiliation(item) for item in items)
    return [value for value in extracted if value]


def collect_affiliations_from_authors(
    authors: list[JsonDict],
) -> list[str]:
    """Collect raw affiliation strings from author dicts.

    Args:
        authors: List of author dicts, each potentially containing an
            'affiliations' key with string or list values.

    Returns:
        List of raw affiliation strings from all authors in the input.
    """
    result: list[str] = []
    for author in authors:
        if isinstance(author, dict) and author.get("affiliations"):
            result.extend(_collect_affiliation_values(author["affiliations"]))
    return result
