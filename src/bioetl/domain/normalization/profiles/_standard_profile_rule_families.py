"""Field-family rule declarations for the standard profile builder."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_abstract,
    normalize_profile_date,
    normalize_profile_doi,
    normalize_profile_float,
    normalize_profile_int,
    normalize_profile_json_string,
    normalize_profile_pmc_id,
    normalize_profile_pmid,
    normalize_profile_title,
)

FieldNormalizer = Callable[[object], object]
RuleFamilySpec = tuple[frozenset[str], FieldNormalizer, str]


def _rule_family_specs(
    *,
    title_fields: frozenset[str],
    abstract_fields: frozenset[str],
    doi_fields: frozenset[str],
    pmid_fields: frozenset[str],
    pmc_id_fields: frozenset[str],
    date_fields: frozenset[str],
    int_fields: frozenset[str],
    float_fields: frozenset[str],
    set_like_fields: frozenset[str],
    json_string_fields: frozenset[str],
) -> tuple[RuleFamilySpec, ...]:
    return (
        (
            title_fields,
            normalize_profile_title,
            "Normalize title text to canonical textual form.",
        ),
        (
            abstract_fields,
            normalize_profile_abstract,
            "Normalize abstract text through canonical whitespace and entity cleanup.",
        ),
        (
            doi_fields,
            normalize_profile_doi,
            "Normalize DOI to canonical registry form before hashing.",
        ),
        (
            pmid_fields,
            normalize_profile_pmid,
            "Normalize PMID to digits-only canonical string.",
        ),
        (
            pmc_id_fields,
            normalize_profile_pmc_id,
            "Normalize PMC identifier to canonical PMC-prefixed string.",
        ),
        (
            date_fields,
            normalize_profile_date,
            "Canonicalize partial-date text to stable date semantics.",
        ),
        (
            int_fields,
            normalize_profile_int,
            "Coerce stable integer semantics for deterministic hashing.",
        ),
        (
            float_fields,
            normalize_profile_float,
            "Coerce stable float semantics and remove NaN/Inf noise.",
        ),
        (
            set_like_fields,
            normalize_profile_json_string,
            "Canonicalize JSON; when represented as an array, treat item order as set-like for content_hash.",
        ),
        (
            json_string_fields,
            normalize_profile_json_string,
            "Canonicalize JSON-bearing string payloads after textual cleanup.",
        ),
    )
