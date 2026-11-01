"""Organism cellularity classification for assay organism metadata.

Classifies assays into one of three cellularity categories:
- acellular (viruses, phages — no cellular structure)
- unicellular (bacteria, archaea, protists, yeasts)
- multicellular (animals, plants, filamentous fungi)

Classification priority:
1. taxonomy_id lookup (primary — more reliable than organism name)
2. normalized organism name (direct match, then keyword heuristics)
3. unresolved (insufficient data)

Pure domain logic with deterministic lookup tables (no I/O).

See Also:
    ``bioetl.domain.behavior.organism_classification_service`` for the service wrapper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bioetl.domain.mapping.organism_classification_constants import (
    KEYWORD_GROUPS as _KEYWORD_GROUPS,
)
from bioetl.domain.mapping.organism_classification_constants import (
    ORGANISM_ALIAS_MAP as _ORGANISM_ALIAS_MAP,
)
from bioetl.domain.mapping.organism_classification_constants import (
    ORGANISM_GENUS_CLASS_MAP as _ORGANISM_GENUS_CLASS_MAP,
)
from bioetl.domain.mapping.organism_classification_constants import (
    ORGANISM_NAME_CLASS_MAP as _ORGANISM_NAME_CLASS_MAP,
)
from bioetl.domain.mapping.organism_classification_constants import (
    PARENTHESES_RE as _PARENTHESES_RE,
)
from bioetl.domain.mapping.organism_classification_constants import (
    WHITESPACE_RE as _WHITESPACE_RE,
)
from bioetl.domain.mapping.organism_classification_taxonomy import (
    classify_by_taxonomy_id as _classify_by_taxonomy_id,
)
from bioetl.domain.types import CellularityType
from bioetl.domain.value_objects.taxonomy_id import validate_taxonomy_id

__all__ = [
    "OrganismClassificationResult",
    "classify_organism",
    "normalize_organism_name",
]


@dataclass(frozen=True, slots=True)
class OrganismClassificationResult:
    """Classification result with source diagnostics."""

    organism_class: CellularityType | None
    normalized_organism: str | None
    taxonomy_id: int | None
    source: Literal["taxonomy_id", "organism_name", "unresolved"]
    source_conflict: bool
    reason: str | None


def normalize_organism_name(organism_name: str | None) -> str | None:
    """Normalize organism name for deterministic lookup.

    Strips whitespace, lowercases, removes parenthetical annotations
    (e.g. strain info), and resolves common aliases.

    Args:
        organism_name: Raw organism name string.

    Returns:
        Normalized name, or None if input is None/empty.
    """
    if organism_name is None:
        return None

    normalized = _PARENTHESES_RE.sub("", organism_name.strip().lower())
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    if not normalized:
        return None

    return _ORGANISM_ALIAS_MAP.get(normalized, normalized)


def _match_species_prefix(normalized_organism: str) -> CellularityType | None:
    """Match organism name against known species prefixes (for strains)."""
    for species_name, cellularity in _ORGANISM_NAME_CLASS_MAP.items():
        if normalized_organism.startswith(f"{species_name} "):
            return cellularity
    return None


def _match_genus(normalized_organism: str) -> CellularityType | None:
    """Match organism name by genus when species-level coverage is incomplete."""
    genus = normalized_organism.split(" ", 1)[0]
    return _ORGANISM_GENUS_CLASS_MAP.get(genus)


def _match_keywords(normalized_organism: str) -> CellularityType | None:
    """Classify by keyword heuristics (fallback)."""
    for cellularity, keywords in _KEYWORD_GROUPS:
        if any(kw in normalized_organism for kw in keywords):
            return cellularity
    return None


def _classify_by_organism_name(
    normalized_organism: str | None,
) -> CellularityType | None:
    """Classify by normalized organism name: direct match, prefix, keywords."""
    if normalized_organism is None:
        return None

    return (
        _ORGANISM_NAME_CLASS_MAP.get(normalized_organism)
        or _match_species_prefix(normalized_organism)
        or _match_genus(normalized_organism)
        or _match_keywords(normalized_organism)
    )


def _build_taxonomy_result(
    taxonomy_id: int,
    normalized_organism: str | None,
    name_class: CellularityType | None,
) -> OrganismClassificationResult:
    """Build result when taxonomy_id is available."""
    taxonomy_class = _classify_by_taxonomy_id(taxonomy_id)
    if taxonomy_class is None:
        if name_class is not None:
            return OrganismClassificationResult(
                organism_class=name_class,
                normalized_organism=normalized_organism,
                taxonomy_id=taxonomy_id,
                source="organism_name",
                source_conflict=False,
                reason="taxonomy_id is valid but not mapped; fell back to organism name",
            )
        return OrganismClassificationResult(
            organism_class=None,
            normalized_organism=normalized_organism,
            taxonomy_id=taxonomy_id,
            source="unresolved",
            source_conflict=False,
            reason="taxonomy_id is valid but not mapped",
        )
    source_conflict = name_class is not None and name_class != taxonomy_class
    return OrganismClassificationResult(
        organism_class=taxonomy_class,
        normalized_organism=normalized_organism,
        taxonomy_id=taxonomy_id,
        source="taxonomy_id",
        source_conflict=source_conflict,
        reason="taxonomy_id and organism name conflict" if source_conflict else None,
    )


def classify_organism(
    assay_organism: str | None,
    assay_taxonomy_id: int | str | None,
) -> OrganismClassificationResult:
    """Classify organism cellularity with taxonomy-first precedence.

    Priority: taxonomy_id (if valid and mapped) > organism name > unresolved.

    Args:
        assay_organism: Raw organism name from ChEMBL assay.
        assay_taxonomy_id: NCBI Taxonomy ID (int or string).

    Returns:
        Classification result with diagnostics.
    """
    taxonomy_id = validate_taxonomy_id(assay_taxonomy_id)
    normalized_organism = normalize_organism_name(assay_organism)
    name_class = _classify_by_organism_name(normalized_organism)

    if taxonomy_id is not None:
        return _build_taxonomy_result(taxonomy_id, normalized_organism, name_class)

    if name_class is not None:
        return OrganismClassificationResult(
            organism_class=name_class,
            normalized_organism=normalized_organism,
            taxonomy_id=None,
            source="organism_name",
            source_conflict=False,
            reason=None,
        )

    return OrganismClassificationResult(
        organism_class=None,
        normalized_organism=normalized_organism,
        taxonomy_id=None,
        source="unresolved",
        source_conflict=False,
        reason="unable to classify from provided inputs",
    )
