"""Organism classification utilities for assay organism metadata.

Classifies assay organisms into acellular / unicellular / multicellular
using NCBI taxonomy ID (source of truth) with fallback to normalized organism
name lookup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Literal

__all__ = [
    "OrganismClass",
    "OrganismClassificationResult",
    "classify_organism",
    "normalize_organism_name",
]


class OrganismClass(StrEnum):
    """High-level organism class for assay context."""

    ACELLULAR = "acellular"
    UNICELLULAR = "unicellular"
    MULTICELLULAR = "multicellular"


@dataclass(frozen=True, slots=True)
class OrganismClassificationResult:
    """Classification result with source diagnostics."""

    organism_class: OrganismClass | None
    normalized_organism: str | None
    taxonomy_id: int | None
    source: Literal["taxonomy_id", "organism_name", "unresolved"]
    source_conflict: bool
    reason: str | None


_PARENTHESES_RE: Final[re.Pattern[str]] = re.compile(r"\s*\([^)]*\)")
_WHITESPACE_RE: Final[re.Pattern[str]] = re.compile(r"\s+")

_ALIAS_TO_CANONICAL: Final[dict[str, str]] = {
    "hiv": "human immunodeficiency virus 1",
    "rice": "oryza sativa japonica group",
    "eel": "anguilla japonica",
    "monkey": "cercopithecidae",
}

_NAME_CLASS_MAP: Final[dict[str, OrganismClass]] = {
    "homo sapiens": OrganismClass.MULTICELLULAR,
    "rattus norvegicus": OrganismClass.MULTICELLULAR,
    "glycine max": OrganismClass.MULTICELLULAR,
    "oryza sativa japonica group": OrganismClass.MULTICELLULAR,
    "anguilla japonica": OrganismClass.MULTICELLULAR,
    "cercopithecidae": OrganismClass.MULTICELLULAR,
    "escherichia coli": OrganismClass.UNICELLULAR,
    "staphylococcus aureus": OrganismClass.UNICELLULAR,
    "candida albicans": OrganismClass.UNICELLULAR,
    "plasmodium falciparum": OrganismClass.UNICELLULAR,
    "streptococcus pneumoniae": OrganismClass.UNICELLULAR,
    "human immunodeficiency virus 1": OrganismClass.ACELLULAR,
    "influenza a virus": OrganismClass.ACELLULAR,
    "enterobacteria phage lambda": OrganismClass.ACELLULAR,
}

_TAXONOMY_CLASS_MAP: Final[dict[int, OrganismClass]] = {
    562: OrganismClass.UNICELLULAR,
    1280: OrganismClass.UNICELLULAR,
    3847: OrganismClass.MULTICELLULAR,
    5476: OrganismClass.UNICELLULAR,
    8005: OrganismClass.MULTICELLULAR,
    9534: OrganismClass.MULTICELLULAR,
    9606: OrganismClass.MULTICELLULAR,
    10116: OrganismClass.MULTICELLULAR,
    10710: OrganismClass.ACELLULAR,
    11676: OrganismClass.ACELLULAR,
    211044: OrganismClass.ACELLULAR,
}


def normalize_organism_name(assay_organism: str | None) -> str | None:
    """Normalize organism name for deterministic lookup."""
    if assay_organism is None:
        return None

    stripped = assay_organism.strip()
    if not stripped:
        return None

    no_parentheses = _PARENTHESES_RE.sub("", stripped)
    normalized = _WHITESPACE_RE.sub(" ", no_parentheses).strip().lower()
    if not normalized:
        return None
    return _ALIAS_TO_CANONICAL.get(normalized, normalized)


def _parse_taxonomy_id(assay_taxonomy_id: int | str | None) -> int | None:
    if assay_taxonomy_id is None:
        return None

    candidate = (
        assay_taxonomy_id
        if isinstance(assay_taxonomy_id, int)
        else _parse_taxonomy_string(assay_taxonomy_id)
    )
    return candidate if candidate > 0 else None


def _parse_taxonomy_string(raw_taxonomy_id: str) -> int:
    candidate = raw_taxonomy_id.strip()
    return int(candidate) if candidate.isdigit() else 0


def _classify_by_name(normalized_organism: str | None) -> OrganismClass | None:
    if normalized_organism is None:
        return None

    return (
        _classify_direct_name(normalized_organism)
        or _classify_prefixed_name(normalized_organism)
        or _classify_keyword_name(normalized_organism)
    )


def _classify_direct_name(normalized_organism: str) -> OrganismClass | None:
    return _NAME_CLASS_MAP.get(normalized_organism)


def _classify_prefixed_name(normalized_organism: str) -> OrganismClass | None:
    for base_name, organism_class in _NAME_CLASS_MAP.items():
        if normalized_organism.startswith(f"{base_name} "):
            return organism_class
    return None


def _classify_keyword_name(normalized_organism: str) -> OrganismClass | None:
    if "virus" in normalized_organism or "phage" in normalized_organism:
        return OrganismClass.ACELLULAR
    return None


def _build_result(
    *,
    organism_class: OrganismClass | None,
    normalized_organism: str | None,
    taxonomy_id: int | None,
    source: Literal["taxonomy_id", "organism_name", "unresolved"],
    source_conflict: bool,
    reason: str | None,
) -> OrganismClassificationResult:
    return OrganismClassificationResult(
        organism_class=organism_class,
        normalized_organism=normalized_organism,
        taxonomy_id=taxonomy_id,
        source=source,
        source_conflict=source_conflict,
        reason=reason,
    )


def _classify_from_invalid_taxonomy(
    normalized_organism: str | None,
) -> OrganismClassificationResult:
    name_class = _classify_by_name(normalized_organism)
    if name_class is not None:
        return _build_result(
            organism_class=name_class,
            normalized_organism=normalized_organism,
            taxonomy_id=None,
            source="organism_name",
            source_conflict=False,
            reason="taxonomy_id is invalid; used normalized organism name",
        )

    return _build_result(
        organism_class=None,
        normalized_organism=normalized_organism,
        taxonomy_id=None,
        source="unresolved",
        source_conflict=False,
        reason="taxonomy_id is invalid and organism name is not recognized",
    )


def _classify_from_taxonomy(
    taxonomy_id: int,
    normalized_organism: str | None,
) -> OrganismClassificationResult:
    taxonomy_class = _TAXONOMY_CLASS_MAP.get(taxonomy_id)
    if taxonomy_class is None:
        return _build_result(
            organism_class=None,
            normalized_organism=normalized_organism,
            taxonomy_id=taxonomy_id,
            source="unresolved",
            source_conflict=False,
            reason="taxonomy_id is valid but not mapped to organism class",
        )

    name_class = _classify_by_name(normalized_organism)
    conflict = name_class is not None and taxonomy_class != name_class
    return _build_result(
        organism_class=taxonomy_class,
        normalized_organism=normalized_organism,
        taxonomy_id=taxonomy_id,
        source="taxonomy_id",
        source_conflict=conflict,
        reason=(
            "taxonomy_id and organism name classifications conflict"
            if conflict
            else None
        ),
    )


def _classify_from_name(
    normalized_organism: str | None,
) -> OrganismClassificationResult:
    name_class = _classify_by_name(normalized_organism)
    if name_class is not None:
        return _build_result(
            organism_class=name_class,
            normalized_organism=normalized_organism,
            taxonomy_id=None,
            source="organism_name",
            source_conflict=False,
            reason=None,
        )

    if normalized_organism is None:
        return _build_result(
            organism_class=None,
            normalized_organism=None,
            taxonomy_id=None,
            source="unresolved",
            source_conflict=False,
            reason="assay_organism and taxonomy_id are empty",
        )

    return _build_result(
        organism_class=None,
        normalized_organism=normalized_organism,
        taxonomy_id=None,
        source="unresolved",
        source_conflict=False,
        reason="organism name is not recognized",
    )


def classify_organism(
    assay_organism: str | None,
    assay_taxonomy_id: int | str | None,
) -> OrganismClassificationResult:
    """Classify organism with taxonomy-first source precedence."""
    normalized_organism = normalize_organism_name(assay_organism)
    taxonomy_id = _parse_taxonomy_id(assay_taxonomy_id)

    if assay_taxonomy_id is not None and taxonomy_id is None:
        return _classify_from_invalid_taxonomy(normalized_organism)

    if taxonomy_id is not None:
        return _classify_from_taxonomy(taxonomy_id, normalized_organism)

    return _classify_from_name(normalized_organism)
