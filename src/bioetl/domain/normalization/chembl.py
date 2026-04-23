"""Pure normalization helpers for ChEMBL ontology, unit, and organism fields."""

from __future__ import annotations

import re

from bioetl.domain.mapping.organism_classification import normalize_organism_name
from bioetl.domain.normalization.text import normalize_string

__all__ = [
    "normalize_bao_identifier",
    "normalize_bao_label",
    "normalize_cellosaurus_id",
    "normalize_chembl_organism_name",
    "normalize_qudt_unit",
    "normalize_standard_unit",
    "normalize_uo_identifier",
]

_BAO_IDENTIFIER_RE = re.compile(r"^bao[_:](\d+)$", re.IGNORECASE)
_UO_IDENTIFIER_RE = re.compile(r"^uo[_:](\d+)$", re.IGNORECASE)
_CELLOSAURUS_IDENTIFIER_RE = re.compile(
    r"^cvcl(?:[_:\-\s]?)([a-z0-9]+)$",
    re.IGNORECASE,
)
_ORGANISM_WHITESPACE_RE = re.compile(r"\s+")

_UNIT_ALIASES: dict[str, str] = {
    "um": "µM",
    "micromolar": "µM",
    "nm": "nM",
    "nanomolar": "nM",
    "pm": "pM",
    "picomolar": "pM",
    "fm": "fM",
    "femtomolar": "fM",
    "mm": "mM",
    "millimolar": "mM",
    "m": "M",
    "molar": "M",
}

_ORGANISM_DISPLAY_NAME_MAP: dict[str, str] = {
    "homo sapiens": "Homo sapiens",
    "mus musculus": "Mus musculus",
    "rattus norvegicus": "Rattus norvegicus",
    "bos taurus": "Bos taurus",
    "sus scrofa": "Sus scrofa",
    "glycine max": "Glycine max",
    "oryza sativa japonica group": "Oryza sativa japonica group",
    "electrophorus electricus": "Electrophorus electricus",
    "chlorocebus aethiops": "Chlorocebus aethiops",
    "macaca fascicularis": "Macaca fascicularis",
    "macaca mulatta": "Macaca mulatta",
    "drosophila melanogaster": "Drosophila melanogaster",
    "xenopus laevis": "Xenopus laevis",
    "gallus gallus": "Gallus gallus",
    "aspergillus niger": "Aspergillus niger",
    "escherichia coli": "Escherichia coli",
    "staphylococcus aureus": "Staphylococcus aureus",
    "streptococcus pneumoniae": "Streptococcus pneumoniae",
    "pseudomonas aeruginosa": "Pseudomonas aeruginosa",
    "mycobacterium tuberculosis": "Mycobacterium tuberculosis",
    "candida albicans": "Candida albicans",
    "plasmodium falciparum": "Plasmodium falciparum",
    "trypanosoma brucei": "Trypanosoma brucei",
    "trypanosoma cruzi": "Trypanosoma cruzi",
    "leishmania major": "Leishmania major",
    "toxoplasma gondii": "Toxoplasma gondii",
    "methanosarcina thermophila": "Methanosarcina thermophila",
    "human immunodeficiency virus 1": "Human immunodeficiency virus 1",
    "human immunodeficiency virus 2": "Human immunodeficiency virus 2",
    "influenza a virus": "Influenza A virus",
    "enterobacteria phage lambda": "Enterobacteria phage lambda",
    "herpes simplex virus": "Herpes simplex virus",
}

_ORGANISM_DISPLAY_ALIASES: dict[str, str] = {
    "e. coli": "Escherichia coli",
}

_BAO_LABEL_BY_IDENTIFIER: dict[str, str] = {
    "BAO_0000019": "assay format",
    "BAO_0000219": "cell-based format",
    "BAO_0000221": "tissue-based format",
    "BAO_0000249": "cell membrane format",
    "BAO_0000251": "microsome format",
    "BAO_0000357": "single protein format",
    "BAO_0000366": "cell-free format",
}


def _normalize_prefixed_identifier(
    value: str | None,
    *,
    prefix: str,
    pattern: re.Pattern[str],
) -> str | None:
    """Canonicalize ontology identifiers to ``PREFIX_0000000`` form."""
    normalized = normalize_string(value)
    if normalized is None:
        return None

    match = pattern.fullmatch(normalized)
    if match is not None:
        return f"{prefix}_{match.group(1)}"

    if normalized.lower().startswith(prefix.lower()):
        return normalized.upper()
    return normalized


def _normalize_unit_name(unit: str) -> str:
    """Normalize ChEMBL unit aliases to canonical activity-unit strings."""
    normalized = unit.strip()
    return _UNIT_ALIASES.get(normalized.lower(), normalized)


def _has_invalid_parenthetical_annotation(annotation: str) -> bool:
    """Return True when the trailing parenthetical payload should be preserved."""
    return not annotation or any(char in annotation for char in "()\n\r")


def _strip_trailing_parenthetical_annotation(value: str) -> str:
    """Drop a trailing ``(annotation)`` suffix without relying on backtracking regex."""
    stripped = value.rstrip()
    if not stripped.endswith(")"):
        return stripped

    separator_index = stripped.rfind(" (")
    if separator_index < 0:
        return stripped

    annotation = stripped[separator_index + 2 : -1]
    if _has_invalid_parenthetical_annotation(annotation):
        return stripped
    return stripped[:separator_index]


def normalize_bao_identifier(value: str | None) -> str | None:
    """Normalize BAO identifiers to canonical underscore form."""
    return _normalize_prefixed_identifier(
        value,
        prefix="BAO",
        pattern=_BAO_IDENTIFIER_RE,
    )


def normalize_bao_label(
    value: str | None,
    *,
    bao_identifier: str | None = None,
) -> str | None:
    """Normalize BAO labels using evidence-backed assay format mappings."""
    normalized_identifier = normalize_bao_identifier(bao_identifier)
    if normalized_identifier is not None:
        canonical_label = _BAO_LABEL_BY_IDENTIFIER.get(normalized_identifier)
        if canonical_label is not None:
            return canonical_label

    normalized = normalize_string(value)
    return normalized.lower() if normalized is not None else None


def normalize_uo_identifier(value: str | None) -> str | None:
    """Normalize Units Ontology identifiers to canonical underscore form."""
    return _normalize_prefixed_identifier(
        value,
        prefix="UO",
        pattern=_UO_IDENTIFIER_RE,
    )


def normalize_cellosaurus_id(value: str | None) -> str | None:
    """Normalize Cellosaurus identifiers to canonical ``CVCL_XXXX`` form."""
    normalized = normalize_string(value)
    if normalized is None:
        return None

    match = _CELLOSAURUS_IDENTIFIER_RE.fullmatch(normalized)
    if match is None:
        return normalized
    return f"CVCL_{match.group(1).upper()}"


def normalize_standard_unit(value: str | None) -> str | None:
    """Normalize standard unit names using the shared activity-unit rules."""
    normalized = normalize_string(value)
    return _normalize_unit_name(normalized) if normalized is not None else None


def normalize_qudt_unit(value: str | None) -> str | None:
    """Normalize QUDT values by trimming only."""
    return normalize_string(value)


def normalize_chembl_organism_name(value: str | None) -> str | None:
    """Normalize ChEMBL organism text while keeping display-friendly output."""
    normalized = normalize_string(value)
    if normalized is None:
        return None

    cleaned = _strip_trailing_parenthetical_annotation(normalized)
    cleaned = _ORGANISM_WHITESPACE_RE.sub(" ", cleaned).strip()
    if not cleaned:
        return None

    lowered_cleaned = cleaned.lower()
    if lowered_cleaned in _ORGANISM_DISPLAY_ALIASES:
        return _ORGANISM_DISPLAY_ALIASES[lowered_cleaned]

    normalized_key = normalize_organism_name(cleaned)
    if normalized_key is None:
        return cleaned

    return _ORGANISM_DISPLAY_NAME_MAP.get(normalized_key, cleaned)
