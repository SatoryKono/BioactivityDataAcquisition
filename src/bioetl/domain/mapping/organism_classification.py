"""Organism class classification for assay organism metadata.

Classifies assays into one of three organism classes:
- acellular (viruses/phages)
- unicellular (bacteria/archaea/single-celled eukaryotes)
- multicellular (animals/plants/fungi multicellular forms)

Classification priority:
1. taxonomy_id (if valid and mapped)
2. normalized organism name (including aliases)
3. unresolved
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
    """Unified organism categories for assay metadata."""

    ACELLULAR = "acellular"
    UNICELLULAR = "unicellular"
    MULTICELLULAR = "multicellular"


@dataclass(frozen=True, slots=True)
class OrganismClassificationResult:
    """Classification result with diagnostics."""

    organism_class: OrganismClass | None
    normalized_organism: str | None
    taxonomy_id: int | None
    source: Literal["taxonomy_id", "organism_name", "unresolved"]
    source_conflict: bool
    reason: str | None


_TAXONOMY_CLASS_MAP: Final[dict[int, OrganismClass]] = {
    # Animals
    9606: OrganismClass.MULTICELLULAR,  # Homo sapiens
    10090: OrganismClass.MULTICELLULAR,  # Mus musculus
    10116: OrganismClass.MULTICELLULAR,  # Rattus norvegicus
    9534: OrganismClass.MULTICELLULAR,  # Macaca
    8005: OrganismClass.MULTICELLULAR,  # Anguilla anguilla (eel)
    # Plants
    3847: OrganismClass.MULTICELLULAR,  # Glycine max
    39947: OrganismClass.MULTICELLULAR,  # Oryza sativa Japonica Group
    # Bacteria / unicellular microbes
    562: OrganismClass.UNICELLULAR,  # Escherichia coli
    1280: OrganismClass.UNICELLULAR,  # Staphylococcus aureus
    1313: OrganismClass.UNICELLULAR,  # Streptococcus pneumoniae
    5476: OrganismClass.UNICELLULAR,  # Candida albicans
    5833: OrganismClass.UNICELLULAR,  # Plasmodium falciparum
    # Acellular
    11676: OrganismClass.ACELLULAR,  # Human immunodeficiency virus 1
    10710: OrganismClass.ACELLULAR,  # Enterobacteria phage lambda
    211044: OrganismClass.ACELLULAR,  # Influenza A virus
}

_ORGANISM_ALIAS_MAP: Final[dict[str, str]] = {
    "hiv": "human immunodeficiency virus 1",
    "rice": "oryza sativa japonica group",
    "eel": "anguilla anguilla",
    "monkey": "macaca",
}

_ORGANISM_NAME_CLASS_MAP: Final[dict[str, OrganismClass]] = {
    "homo sapiens": OrganismClass.MULTICELLULAR,
    "rattus norvegicus": OrganismClass.MULTICELLULAR,
    "glycine max": OrganismClass.MULTICELLULAR,
    "oryza sativa japonica group": OrganismClass.MULTICELLULAR,
    "anguilla anguilla": OrganismClass.MULTICELLULAR,
    "macaca": OrganismClass.MULTICELLULAR,
    "escherichia coli": OrganismClass.UNICELLULAR,
    "staphylococcus aureus": OrganismClass.UNICELLULAR,
    "streptococcus pneumoniae": OrganismClass.UNICELLULAR,
    "candida albicans": OrganismClass.UNICELLULAR,
    "plasmodium falciparum": OrganismClass.UNICELLULAR,
    "human immunodeficiency virus 1": OrganismClass.ACELLULAR,
    "influenza a virus": OrganismClass.ACELLULAR,
    "enterobacteria phage lambda": OrganismClass.ACELLULAR,
}

_ACELLULAR_KEYWORDS: Final[tuple[str, ...]] = (
    "virus",
    "viridae",
    "phage",
    "bacteriophage",
)

_UNICELLULAR_KEYWORDS: Final[tuple[str, ...]] = (
    "bacter",
    "archaea",
    "archae",
    "yeast",
    "plasmodium",
    "candida",
)

_MULTICELLULAR_KEYWORDS: Final[tuple[str, ...]] = (
    "homo",
    "mus ",
    "rattus",
    "glycine",
    "oryza",
    "macaca",
    "anguilla",
)

_PARENTHESES_RE: Final[re.Pattern[str]] = re.compile(r"\s*\([^)]*\)")
_SPACES_RE: Final[re.Pattern[str]] = re.compile(r"\s+")


def normalize_organism_name(organism_name: str | None) -> str | None:
    """Normalize organism name for deterministic lookup."""
    if organism_name is None:
        return None

    normalized = _PARENTHESES_RE.sub("", organism_name.strip().lower())
    normalized = _SPACES_RE.sub(" ", normalized).strip()
    return normalized or None


def _parse_taxonomy_id(assay_taxonomy_id: int | str | None) -> int | None:
    if assay_taxonomy_id is None:
        return None
    if isinstance(assay_taxonomy_id, int):
        return assay_taxonomy_id if assay_taxonomy_id > 0 else None

    stripped = assay_taxonomy_id.strip()
    if not stripped or not stripped.isdigit():
        return None

    parsed = int(stripped)
    return parsed if parsed > 0 else None


def _classify_from_taxonomy_id(taxonomy_id: int) -> OrganismClass | None:
    return _TAXONOMY_CLASS_MAP.get(taxonomy_id)


def _classify_from_organism_name(
    normalized_organism: str | None,
) -> OrganismClass | None:
    if normalized_organism is None:
        return None

    canonical = _ORGANISM_ALIAS_MAP.get(normalized_organism, normalized_organism)

    direct = _ORGANISM_NAME_CLASS_MAP.get(canonical)
    if direct is not None:
        return direct

    # Handle strains / isolates by prefix matching canonical species names.
    for species_name, organism_class in _ORGANISM_NAME_CLASS_MAP.items():
        if canonical.startswith(f"{species_name} "):
            return organism_class

    if any(keyword in canonical for keyword in _ACELLULAR_KEYWORDS):
        return OrganismClass.ACELLULAR
    if any(keyword in canonical for keyword in _UNICELLULAR_KEYWORDS):
        return OrganismClass.UNICELLULAR
    if any(keyword in canonical for keyword in _MULTICELLULAR_KEYWORDS):
        return OrganismClass.MULTICELLULAR

    return None


def classify_organism(
    assay_organism: str | None,
    assay_taxonomy_id: int | str | None,
) -> OrganismClassificationResult:
    """Classify organism by taxonomy id first, then by normalized organism name."""
    normalized_organism = normalize_organism_name(assay_organism)
    taxonomy_id = _parse_taxonomy_id(assay_taxonomy_id)

    name_class = _classify_from_organism_name(normalized_organism)

    if taxonomy_id is not None:
        taxonomy_class = _classify_from_taxonomy_id(taxonomy_id)
        if taxonomy_class is not None:
            source_conflict = name_class is not None and name_class != taxonomy_class
            reason = "taxonomy_id_priority"
            if source_conflict:
                reason = "taxonomy_id_priority_conflict_with_organism_name"

            return OrganismClassificationResult(
                organism_class=taxonomy_class,
                normalized_organism=normalized_organism,
                taxonomy_id=taxonomy_id,
                source="taxonomy_id",
                source_conflict=source_conflict,
                reason=reason,
            )

        return OrganismClassificationResult(
            organism_class=None,
            normalized_organism=normalized_organism,
            taxonomy_id=taxonomy_id,
            source="unresolved",
            source_conflict=False,
            reason="taxonomy_id_not_mapped",
        )

    if name_class is not None:
        return OrganismClassificationResult(
            organism_class=name_class,
            normalized_organism=normalized_organism,
            taxonomy_id=None,
            source="organism_name",
            source_conflict=False,
            reason="classified_by_organism_name",
        )

    return OrganismClassificationResult(
        organism_class=None,
        normalized_organism=normalized_organism,
        taxonomy_id=None,
        source="unresolved",
        source_conflict=False,
        reason="insufficient_or_unknown_input",
    )
