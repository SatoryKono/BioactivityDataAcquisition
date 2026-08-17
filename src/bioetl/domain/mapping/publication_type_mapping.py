"""Canonical publication type mapping for cross-provider normalization.

Maps raw publication type strings from each provider to canonical
kebab-case lowercase values defined in ``domain.types.PublicationType``.

The mapping is case-sensitive: raw values arrive in a fixed format from
each provider API and are matched exactly.

Usage::

    from bioetl.domain.mapping.publication_type_mapping import (
        PUBLICATION_TYPE_MAPPING,
        normalize_publication_type,
    )

    canonical = normalize_publication_type("PUBLICATION")  # "journal-article"
    canonical = normalize_publication_type("Journal Article")  # "journal-article"
    canonical = normalize_publication_type(None)  # None
    canonical = normalize_publication_type("unknown-value")  # None
"""

from __future__ import annotations

from typing import Final, cast

__all__ = [
    "PUBLICATION_TYPE_MAPPING",
    "normalize_publication_type",
]

PUBLICATION_TYPE_MAPPING: Final[dict[str, str]] = {
    # ── ChEMBL (UPPER_CASE) ──────────────────────────────────────────────
    "PUBLICATION": "journal-article",
    "BOOK": "book",
    "DATASET": "dataset",
    "PATENT": "patent",
    # ── PubMed (Title Case) ──────────────────────────────────────────────
    "Journal Article": "journal-article",
    "Review": "review",
    "Letter": "letter",
    "Editorial": "editorial",
    "Clinical Trial": "clinical-trial",
    "Meta-Analysis": "meta-analysis",
    "Case Reports": "case-reports",
    "Comparative Study": "comparative-study",
    "Evaluation Study": "evaluation-study",
    "Preprint": "preprint",
    # ── CrossRef (kebab-case, already canonical — included for completeness) ─
    "journal-article": "journal-article",
    "book-chapter": "book-chapter",
    "proceedings-article": "proceedings-article",
    "posted-content": "posted-content",
    "book": "book",
    "report": "report",
    "dataset": "dataset",
    "standard": "standard",
    # ── OpenAlex (lowercase) ─────────────────────────────────────────────
    "article": "journal-article",
    "dissertation": "dissertation",
    "preprint": "preprint",
    # ── Semantic Scholar (PascalCase) ────────────────────────────────────
    "JournalArticle": "journal-article",
    "Conference": "proceedings-article",
    "CaseReport": "case-reports",
    "ClinicalTrial": "clinical-trial",
    "MetaAnalysis": "meta-analysis",
    "Dataset": "dataset",
    "Book": "book",
    "BookSection": "book-chapter",
    "LettersAndComments": "letter",
    "News": "other",
    "Study": "other",
    # ── Shared (PubMed + S2 share "Review" / "Editorial"; canonical lowercase) ─
    "review": "review",
    "letter": "letter",
    "editorial": "editorial",
    "other": "other",
    "patent": "patent",
}


def _normalize_single(raw: str) -> str | None:
    """Normalize a single publication type token to canonical form."""
    return PUBLICATION_TYPE_MAPPING.get(raw)


def _normalize_pipe_separated(raw_value: str) -> str | None:
    """Normalize a pipe-separated publication type string."""
    parts = _non_empty_publication_type_parts(raw_value)
    if not parts:
        return None
    normalized = _normalize_known_publication_type_parts(parts)
    return None if normalized is None else "|".join(normalized)


def _non_empty_publication_type_parts(raw_value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw_value.split("|") if part.strip())


def _normalize_known_publication_type_parts(
    parts: tuple[str, ...],
) -> tuple[str, ...] | None:
    normalized = tuple(_normalize_single(part) for part in parts)
    if any(value is None for value in normalized):
        return None
    return cast("tuple[str, ...]", normalized)


def normalize_publication_type(raw_value: str | None) -> str | None:
    """Normalize a raw publication type string to its canonical form.

    For pipe-separated multi-value strings (PubMed, Semantic Scholar),
    each component is normalized individually and re-joined.

    Args:
        raw_value: Raw publication type from provider API, or None.

    Returns:
        Canonical kebab-case value, or None for absent or unknown input.

    """
    if raw_value is None:
        return None
    if "|" in raw_value:
        return _normalize_pipe_separated(raw_value)
    return _normalize_single(raw_value)
