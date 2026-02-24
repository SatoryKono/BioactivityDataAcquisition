"""Organism classification by taxonomy ID and organism name.

Pure domain logic with deterministic lookup tables (no I/O).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from bioetl.domain.value_objects.taxonomy_id import validate_taxonomy_id


class OrganismClass(str, Enum):
    """High-level organism class."""

    ACELLULAR = "acellular"
    UNICELLULAR = "unicellular"
    MULTICELLULAR = "multicellular"


@dataclass(frozen=True)
class OrganismClassificationResult:
    """Classification result with source and diagnostics."""

    organism_class: OrganismClass | None
    normalized_organism: str | None
    taxonomy_id: int | None
    source: Literal["taxonomy_id", "organism_name", "unresolved"]
    source_conflict: bool
    reason: str | None


_TAXONOMY_CLASS_MAP: dict[int, OrganismClass] = {
    562: OrganismClass.UNICELLULAR,  # Escherichia coli
    1280: OrganismClass.UNICELLULAR,  # Staphylococcus aureus
    3847: OrganismClass.MULTICELLULAR,  # Glycine max
    5476: OrganismClass.UNICELLULAR,  # Candida albicans
    8005: OrganismClass.MULTICELLULAR,  # eel
    9534: OrganismClass.MULTICELLULAR,  # monkey (Catarrhini)
    9606: OrganismClass.MULTICELLULAR,  # Homo sapiens
    10116: OrganismClass.MULTICELLULAR,  # Rattus norvegicus
    10710: OrganismClass.ACELLULAR,  # Enterobacteria phage lambda
    11676: OrganismClass.ACELLULAR,  # Human immunodeficiency virus 1
    211044: OrganismClass.ACELLULAR,  # Influenza A virus
}

_ORGANISM_ALIAS_TO_CANONICAL: dict[str, str] = {
    "hiv": "human immunodeficiency virus 1",
    "eel": "anguilla anguilla",
    "rice": "oryza sativa japonica group",
    "monkey": "catarrhini",
}

_ORGANISM_NAME_CLASS_MAP: dict[str, OrganismClass] = {
    "homo sapiens": OrganismClass.MULTICELLULAR,
    "rattus norvegicus": OrganismClass.MULTICELLULAR,
    "glycine max": OrganismClass.MULTICELLULAR,
    "oryza sativa japonica group": OrganismClass.MULTICELLULAR,
    "catarrhini": OrganismClass.MULTICELLULAR,
    "anguilla anguilla": OrganismClass.MULTICELLULAR,
    "escherichia coli": OrganismClass.UNICELLULAR,
    "staphylococcus aureus": OrganismClass.UNICELLULAR,
    "candida albicans": OrganismClass.UNICELLULAR,
    "plasmodium falciparum": OrganismClass.UNICELLULAR,
    "human immunodeficiency virus 1": OrganismClass.ACELLULAR,
    "influenza a virus": OrganismClass.ACELLULAR,
    "enterobacteria phage lambda": OrganismClass.ACELLULAR,
}

_ACELLULAR_HINTS: tuple[str, ...] = ("virus", "phage", "virion")
_UNICELLULAR_HINTS: tuple[str, ...] = (
    "bacter",
    "archaea",
    "archaeon",
    "yeast",
    "plasmodium",
    "candida",
)
_MULTICELLULAR_HINTS: tuple[str, ...] = (
    "homo sapiens",
    "rattus",
    "mus musculus",
    "glycine",
    "oryza",
    "monkey",
    "fish",
    "eel",
)

_CLASS_HINTS: tuple[tuple[OrganismClass, tuple[str, ...]], ...] = (
    (OrganismClass.ACELLULAR, _ACELLULAR_HINTS),
    (OrganismClass.UNICELLULAR, _UNICELLULAR_HINTS),
    (OrganismClass.MULTICELLULAR, _MULTICELLULAR_HINTS),
)


def _normalize_organism_name(assay_organism: str | None) -> str | None:
    """Normalize organism name for deterministic lookup."""
    if assay_organism is None:
        return None

    normalized = assay_organism.strip().lower()
    if not normalized:
        return None

    normalized = re.sub(r"\([^)]*\)", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = _ORGANISM_ALIAS_TO_CANONICAL.get(normalized, normalized)

    for canonical in _ORGANISM_NAME_CLASS_MAP:
        if normalized.startswith(f"{canonical} "):
            return canonical

    return normalized


def _classify_from_organism_name(
    normalized_organism: str | None,
) -> OrganismClass | None:
    """Classify by normalized organism name and heuristic hints."""
    if normalized_organism is None:
        return None

    direct_match = _ORGANISM_NAME_CLASS_MAP.get(normalized_organism)
    if direct_match is not None:
        return direct_match

    return _classify_by_hints(normalized_organism)


def _classify_by_hints(normalized_organism: str) -> OrganismClass | None:
    """Classify name by ordered token hints."""
    for organism_class, hints in _CLASS_HINTS:
        if any(hint in normalized_organism for hint in hints):
            return organism_class
    return None


def _build_result_from_taxonomy(
    taxonomy_id: int,
    normalized_organism: str | None,
    name_class: OrganismClass | None,
) -> OrganismClassificationResult:
    """Build result for valid taxonomy ID input."""
    taxonomy_class = _TAXONOMY_CLASS_MAP.get(taxonomy_id)
    if taxonomy_class is None:
        return OrganismClassificationResult(
            organism_class=None,
            normalized_organism=normalized_organism,
            taxonomy_id=taxonomy_id,
            source="unresolved",
            source_conflict=False,
            reason=f"taxonomy_id {taxonomy_id} is valid but not mapped",
        )

    source_conflict = name_class is not None and name_class != taxonomy_class
    return OrganismClassificationResult(
        organism_class=taxonomy_class,
        normalized_organism=normalized_organism,
        taxonomy_id=taxonomy_id,
        source="taxonomy_id",
        source_conflict=source_conflict,
        reason="taxonomy_id took priority over conflicting organism name"
        if source_conflict
        else None,
    )


def classify_organism(
    assay_organism: str | None,
    assay_taxonomy_id: int | str | None,
) -> OrganismClassificationResult:
    """Classify organism as acellular/unicellular/multicellular.

    Priority: taxonomy_id (if valid) > organism_name > unresolved.
    """
    taxonomy_id = validate_taxonomy_id(assay_taxonomy_id)
    normalized_organism = _normalize_organism_name(assay_organism)

    name_class = _classify_from_organism_name(normalized_organism)

    if taxonomy_id is not None:
        return _build_result_from_taxonomy(taxonomy_id, normalized_organism, name_class)

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
        reason="unable to classify organism from provided inputs",
    )
