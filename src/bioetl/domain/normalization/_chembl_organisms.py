"""Private organism display-name normalization helpers for ChEMBL fields."""

from __future__ import annotations

import re

from bioetl.domain.mapping.organism_classification import normalize_organism_name
from bioetl.domain.normalization.text import normalize_string

_ORGANISM_WHITESPACE_RE = re.compile(r"\s+")
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


def _strip_trailing_parenthetical_annotation(value: str) -> str:
    stripped = value.rstrip()
    if not stripped.endswith(")"):
        return stripped

    separator_index = stripped.rfind(" (")
    if separator_index < 0:
        return stripped

    annotation = stripped[separator_index + 2 : -1]
    if not annotation or any(char in annotation for char in "()\n\r"):
        return stripped
    return stripped[:separator_index]
