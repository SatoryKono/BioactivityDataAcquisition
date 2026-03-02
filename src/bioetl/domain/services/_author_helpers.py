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
    """Hash author name with SHA-256: sha256(lowercase(name) + salt).

    Args:
        name: Author name to hash.
        salt: Cryptographic salt for hashing.

    Returns:
        Hexadecimal SHA-256 hash of the normalized author name.
    """
    normalized = name.strip().lower()
    return hashlib.sha256(f"{normalized}{salt}".encode()).hexdigest()


def parse_author_names(
    authors: list[str] | list[dict[str, Any]] | str,  # Any: heterogeneous field values
) -> list[str]:
    """Parse various author formats to list of name strings.

    Args:
        authors: Authors.

    Returns:
        Parsed result.
    """
    if isinstance(authors, list):
        return [n for a in authors if (n := _extract_name_from_item(a))]
    if isinstance(authors, str):
        return parse_author_string(authors)
    return []


def _strip_or_none(value: Any) -> str | None:  # Any: raw API JSON value
    """Strip string and return None if empty or non-string."""
    return value.strip() or None if isinstance(value, str) else None


def _extract_name_from_item(item: Any) -> str | None:  # Any: raw API JSON value
    """Extract author name from a string or dict item."""
    if isinstance(item, str):
        return _strip_or_none(item)
    if isinstance(item, dict):
        return _strip_or_none(item.get("name"))
    return None


def parse_author_string(text: str) -> list[str]:
    """Parse author string (JSON or delimited format).

    Args:
        text: Input text string.

    Returns:
        Parsed result.
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
        text: Input text string.

    Returns:
        Result list.
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
        text: Input text string.

    Returns:
        Parsed result.
    """
    delimiter = ";" if ";" in text else ","
    parts = text.split(delimiter) if delimiter in text else [text]
    return [part.strip() for part in parts if part.strip()]


def extract_affiliation_strings(
    affiliations: list[str] | list[dict[str, Any]],  # Any: heterogeneous field values
) -> list[str]:
    """Extract affiliation strings from a mixed list of strings and dicts.

    Args:
        affiliations: Affiliations.

    Returns:
        Extracted value.
    """
    strings: list[str] = []
    for aff in affiliations:
        extracted = _extract_single_affiliation(aff)
        if extracted:
            strings.append(extracted)
    return strings


# Any: heterogeneous field va...
def _extract_affiliation_from_dict(aff: dict[str, Any]) -> str | None:
    """Extract first non-empty affiliation value from known keys."""
    for key in _AFFILIATION_KEYS:
        result = _strip_or_none(aff.get(key))
        if result:
            return result
    return None


def _extract_single_affiliation(aff: Any) -> str | None:  # Any: raw API JSON value
    """Extract affiliation string from a single item (str or dict)."""
    if isinstance(aff, str):
        return _strip_or_none(aff)
    if isinstance(aff, dict):
        return _extract_affiliation_from_dict(aff)
    return None


def normalize_affiliation_string(text: str) -> str | None:
    """Normalize affiliation: HTML → whitespace → control chars → NFC → trim.

    Args:
        text: Input text string.

    Returns:
        Normalized value.
    """
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
    """Deduplicate strings case-insensitively, keeping first occurrence.

    Args:
        strings: Strings.

    Returns:
        Result list.
    """
    seen: dict[str, str] = {}
    for s in strings:
        key = s.lower()
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
    """Parse space-separated tokens into ``Surname_F`` key.

    Detects three patterns:
    - Trailing initials (ChEMBL): ``["Smith", "JA"]`` → ``"Smith_J"``
    - Leading initials: ``["X.", "Zhou"]`` → ``"Zhou_X"``
    - Standard order: ``["John", "Doe"]`` → ``"Doe_J"``
    """
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

    Handles multiple input formats:
    - ``"Doe, John"`` → ``"Doe_J"``    (LastName, FirstName)
    - ``"Doe, J"``    → ``"Doe_J"``    (LastName, Initial)
    - ``"Doe, JA"``   → ``"Doe_J"``    (LastName, Initials)
    - ``"John Doe"``  → ``"Doe_J"``    (FirstName LastName)
    - ``"Smith JA"``  → ``"Smith_J"``  (LastName Initials — ChEMBL)
    - ``"X. Zhou"``   → ``"Zhou_X"``   (Initial. LastName)
    - ``"Madonna"``   → ``"Madonna"``  (single name — no initial)
    - ``"WHO"``       → ``"WHO"``      (organization — no underscore)

    Returns:
        Short key string, or None if name is empty.

    Args:
        name: Identifier name.
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


def _collect_affiliation_values(aff_data: Any) -> list[str]:  # Any: raw API JSON value
    """Extract affiliation strings from a single author's affiliation field."""
    if isinstance(aff_data, list):
        return [str(a) for a in aff_data if a]
    if isinstance(aff_data, str):
        return [aff_data]
    return []


def collect_affiliations_from_authors(
    authors: list[dict[str, Any]],  # Any: heterogeneous field values
) -> list[str]:
    """Collect raw affiliation strings from author dicts.

    Args:
        authors: Authors.

    Returns:
        Collected results.
    """
    result: list[str] = []
    for author in authors:
        if isinstance(author, dict) and author.get("affiliations"):
            result.extend(_collect_affiliation_values(author["affiliations"]))
    return result
