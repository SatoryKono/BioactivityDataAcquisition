"""Shared fallback helpers for record normalization outside profile coverage."""

from __future__ import annotations

from bioetl.application.core.normalization_rules import NormalizationRulesPolicy

__all__ = [
    "UNHANDLED_FALLBACK_NORMALIZATION",
    "canonicalize_json_like_string",
    "is_date_field",
    "is_doi_field",
    "is_json_like_string",
    "is_pmid_field",
    "is_smiles_field",
    "normalize_named_text_field",
    "normalize_plain_text",
    "normalize_special_fallback_field",
]

_JSON_START_TOKENS = ("{", "[")
_JSON_END_TOKENS = ("}", "]")
_PMID_SUFFIXES = ("_pmid",)
_DOI_SUFFIXES = ("_doi",)
UNHANDLED_FALLBACK_NORMALIZATION = object()


def is_json_like_string(value: str) -> bool:
    """Return whether a string should be treated as JSON-like text."""
    stripped = value.strip()
    if len(stripped) < 2:
        return False
    return stripped.startswith(_JSON_START_TOKENS) and stripped.endswith(
        _JSON_END_TOKENS
    )


def is_doi_field(field_name: str, *, rule_set: NormalizationRulesPolicy) -> bool:
    """Return whether the field uses DOI fallback normalization."""
    return field_name in rule_set.doi_fields or field_name.endswith(_DOI_SUFFIXES)


def is_pmid_field(field_name: str, *, rule_set: NormalizationRulesPolicy) -> bool:
    """Return whether the field uses PMID fallback normalization."""
    return field_name in rule_set.pmid_fields or field_name.endswith(_PMID_SUFFIXES)


def is_date_field(field_name: str, *, rule_set: NormalizationRulesPolicy) -> bool:
    """Return whether the field uses partial-date fallback normalization."""
    if field_name.endswith("_ts"):
        return False
    return (
        field_name in rule_set.date_fields
        or field_name.endswith("_date")
        or field_name.startswith("date_")
    )


def is_smiles_field(field_name: str) -> bool:
    """Return whether the field uses SMILES fallback normalization."""
    return field_name == "smiles" or field_name.endswith("_smiles")


def normalize_special_fallback_field(
    field_name: str,
    value: object,
    *,
    rule_set: NormalizationRulesPolicy,
) -> object:
    """Normalize one fallback special field or return the unhandled sentinel."""
    if value is None:
        return None
    if is_smiles_field(field_name):
        from bioetl.domain.normalization.profiles.profile_normalizers import (
            normalize_profile_smiles,
        )

        return normalize_profile_smiles(
            value,
            is_canonical=(field_name == "canonical_smiles"),
        )
    if is_doi_field(field_name, rule_set=rule_set):
        from bioetl.domain.normalization.profiles.profile_normalizers import (
            normalize_profile_doi,
        )

        return normalize_profile_doi(value)
    if is_pmid_field(field_name, rule_set=rule_set):
        from bioetl.domain.normalization.profiles.profile_normalizers import (
            normalize_profile_pmid,
        )

        return normalize_profile_pmid(value)
    if is_date_field(field_name, rule_set=rule_set):
        from bioetl.domain.normalization.dates import normalize_partial_date

        return normalize_partial_date(value) if isinstance(value, str) else value
    return UNHANDLED_FALLBACK_NORMALIZATION


def normalize_named_text_field(
    field_name: str,
    value: str,
    *,
    rule_set: NormalizationRulesPolicy,
) -> str | None:
    """Normalize one configured named text field."""
    if field_name in rule_set.title_fields:
        from bioetl.domain.normalization.text import normalize_title

        return normalize_title(value)
    if field_name in rule_set.abstract_fields:
        from bioetl.domain.normalization.text import normalize_abstract

        return normalize_abstract(value)
    if field_name in rule_set.oa_status_fields:
        from bioetl.domain.normalization.text import normalize_oa_status

        return normalize_oa_status(value)
    return None


def canonicalize_json_like_string(value: str) -> str:
    """Canonicalize JSON-like text while preserving invalid JSON as trimmed text."""
    if not is_json_like_string(value):
        return value
    from bioetl.domain.normalization.profiles.profile_normalizers import (
        normalize_profile_json_string,
    )

    canonical_json = normalize_profile_json_string(value)
    return canonical_json if isinstance(canonical_json, str) else value


def normalize_plain_text(value: str) -> str | None:
    """Normalize plain text outside named field buckets."""
    from bioetl.domain.normalization.text import normalize_string

    return normalize_string(value)
