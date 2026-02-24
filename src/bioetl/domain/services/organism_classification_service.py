"""Organism classification service for assay biological context.

Classifies organisms into acellular/unicellular/multicellular using
NCBI taxonomy ID as primary source and normalized organism name as fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from re import sub
from typing import Literal

from bioetl.domain.value_objects import validate_taxonomy_id


class OrganismClass(str, Enum):
    """High-level organism classes used for assay context."""

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


@dataclass(frozen=True)
class _AliasEntry:
    canonical_name: str
    organism_class: OrganismClass
    taxonomy_id: int | None = None


_TAXONOMY_CLASS_MAP: dict[int, OrganismClass] = {
    562: OrganismClass.UNICELLULAR,
    1280: OrganismClass.UNICELLULAR,
    5476: OrganismClass.UNICELLULAR,
    5833: OrganismClass.UNICELLULAR,
    8005: OrganismClass.MULTICELLULAR,
    3847: OrganismClass.MULTICELLULAR,
    4530: OrganismClass.MULTICELLULAR,
    9534: OrganismClass.MULTICELLULAR,
    9606: OrganismClass.MULTICELLULAR,
    10116: OrganismClass.MULTICELLULAR,
    10710: OrganismClass.ACELLULAR,
    11676: OrganismClass.ACELLULAR,
    211044: OrganismClass.ACELLULAR,
}

_ALIAS_MAP: dict[str, _AliasEntry] = {
    "hiv": _AliasEntry(
        "human immunodeficiency virus 1", OrganismClass.ACELLULAR, 11676
    ),
    "rice": _AliasEntry(
        "oryza sativa japonica group", OrganismClass.MULTICELLULAR, 4530
    ),
    "eel": _AliasEntry("anguilla japonica", OrganismClass.MULTICELLULAR, 8005),
    "monkey": _AliasEntry("catarrhini", OrganismClass.MULTICELLULAR, 9534),
}

_NAME_CLASS_MAP: dict[str, OrganismClass] = {
    "homo sapiens": OrganismClass.MULTICELLULAR,
    "rattus norvegicus": OrganismClass.MULTICELLULAR,
    "glycine max": OrganismClass.MULTICELLULAR,
    "oryza sativa japonica group": OrganismClass.MULTICELLULAR,
    "escherichia coli": OrganismClass.UNICELLULAR,
    "staphylococcus aureus": OrganismClass.UNICELLULAR,
    "candida albicans": OrganismClass.UNICELLULAR,
    "plasmodium falciparum": OrganismClass.UNICELLULAR,
    "streptococcus pneumoniae": OrganismClass.UNICELLULAR,
    "human immunodeficiency virus 1": OrganismClass.ACELLULAR,
    "influenza a virus": OrganismClass.ACELLULAR,
    "enterobacteria phage lambda": OrganismClass.ACELLULAR,
}


def _normalize_organism_name(assay_organism: str | None) -> str | None:
    if assay_organism is None:
        return None

    cleaned = sub(r"\([^)]*\)", " ", assay_organism).strip().lower()
    normalized = " ".join(cleaned.split())
    return normalized or None


def _classify_by_taxonomy_id(taxonomy_id: int | None) -> OrganismClass | None:
    if taxonomy_id is None:
        return None
    return _TAXONOMY_CLASS_MAP.get(taxonomy_id)


def _lookup_alias_classification(
    organism_name: str,
) -> tuple[OrganismClass | None, str | None]:
    alias = _ALIAS_MAP.get(organism_name)
    if alias is None:
        return None, None
    return alias.organism_class, alias.canonical_name


def _lookup_direct_name_classification(
    organism_name: str,
) -> tuple[OrganismClass | None, str]:
    return _NAME_CLASS_MAP.get(organism_name), organism_name


def _is_acellular_keyword_match(organism_name: str) -> bool:
    return "virus" in organism_name or "phage" in organism_name


def _lookup_binomial_class(organism_name: str) -> tuple[OrganismClass | None, str]:
    tokens = organism_name.split()
    if len(tokens) < 2:
        return None, organism_name

    binomial = f"{tokens[0]} {tokens[1]}"
    return _NAME_CLASS_MAP.get(binomial), binomial


def _lookup_name_based_classification(
    organism_name: str,
) -> tuple[OrganismClass | None, str | None]:
    lookup_chain = (
        _lookup_alias_classification,
        _lookup_direct_name_classification,
        _lookup_binomial_class,
    )
    for lookup in lookup_chain:
        cls_result, normalized_name = lookup(organism_name)
        if cls_result is not None:
            return cls_result, normalized_name
    return None, None


def _classify_by_organism_name(
    normalized_organism: str | None,
) -> tuple[OrganismClass | None, str | None]:
    if normalized_organism is None:
        return None, None

    resolved_class, resolved_name = _lookup_name_based_classification(
        normalized_organism
    )
    if resolved_class is not None:
        return resolved_class, resolved_name

    if _is_acellular_keyword_match(normalized_organism):
        return OrganismClass.ACELLULAR, normalized_organism

    return None, normalized_organism


def _build_taxonomy_result(
    taxonomy_id: int,
    taxonomy_class: OrganismClass | None,
    normalized_organism: str | None,
    source_conflict: bool,
) -> OrganismClassificationResult:
    if taxonomy_class is None:
        return OrganismClassificationResult(
            organism_class=None,
            normalized_organism=normalized_organism,
            taxonomy_id=taxonomy_id,
            source="unresolved",
            source_conflict=False,
            reason="taxonomy_id_not_mapped",
        )

    return OrganismClassificationResult(
        organism_class=taxonomy_class,
        normalized_organism=normalized_organism,
        taxonomy_id=taxonomy_id,
        source="taxonomy_id",
        source_conflict=source_conflict,
        reason="taxonomy_id_classification",
    )


def _build_name_result(
    name_class: OrganismClass | None,
    normalized_organism: str | None,
) -> OrganismClassificationResult:
    if name_class is None:
        return OrganismClassificationResult(
            organism_class=None,
            normalized_organism=normalized_organism,
            taxonomy_id=None,
            source="unresolved",
            source_conflict=False,
            reason="insufficient_or_unrecognized_input",
        )

    return OrganismClassificationResult(
        organism_class=name_class,
        normalized_organism=normalized_organism,
        taxonomy_id=None,
        source="organism_name",
        source_conflict=False,
        reason="organism_name_classification",
    )


def _has_source_conflict(
    taxonomy_id: int | None,
    taxonomy_class: OrganismClass | None,
    name_class: OrganismClass | None,
) -> bool:
    return (
        taxonomy_id is not None
        and taxonomy_class is not None
        and name_class is not None
        and taxonomy_class != name_class
    )


def classify_organism(
    assay_organism: str | None,
    assay_taxonomy_id: int | str | None,
) -> OrganismClassificationResult:
    """Classify organism using taxonomy ID priority and name fallback."""
    taxonomy_id = validate_taxonomy_id(assay_taxonomy_id)
    normalized_organism = _normalize_organism_name(assay_organism)
    taxonomy_class = _classify_by_taxonomy_id(taxonomy_id)
    name_class, normalized_match = _classify_by_organism_name(normalized_organism)

    if taxonomy_id is not None:
        source_conflict = _has_source_conflict(taxonomy_id, taxonomy_class, name_class)
        return _build_taxonomy_result(
            taxonomy_id=taxonomy_id,
            taxonomy_class=taxonomy_class,
            normalized_organism=normalized_match,
            source_conflict=source_conflict,
        )

    return _build_name_result(
        name_class=name_class,
        normalized_organism=normalized_match,
    )
