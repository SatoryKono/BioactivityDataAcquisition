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
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

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


# ---------------------------------------------------------------------------
# Taxonomy ID → CellularityType mapping (~100 entries from ChEMBL dataset)
# Uses frozenset for O(1) membership tests on large sets.
# ---------------------------------------------------------------------------

_ACELLULAR_TAX_IDS: Final[frozenset[int]] = frozenset(
    {
        10298,  # Human alphaherpesvirus 1
        10299,  # Herpes simplex virus (type 1 / strain 17)
        10309,  # Herpes simplex virus (type 1 / strain SC16)
        10310,  # Human alphaherpesvirus 2
        10335,  # Human alphaherpesvirus 3 (VZV)
        10360,  # Human herpesvirus 5 strain AD169 (CMV)
        10580,  # Human papillomavirus 11
        10665,  # Tequatrovirus T4 (bacteriophage)
        10710,  # Enterobacteria phage lambda
        11676,  # Human immunodeficiency virus 1
        11679,  # HIV-1 (CLONE 12)
        11709,  # Human immunodeficiency virus 2
        11866,  # Avian myeloblastosis virus
        11926,  # Human T-cell leukemia virus type 1
        11970,  # Woolly monkey sarcoma virus
        132504,  # Influenza A virus (A/X-31(H3N2))
        169066,  # Human rhinovirus sp.
        211044,  # Influenza A virus (A/Puerto Rico/8/1934(H1N1))
        694009,  # SARS-related coronavirus
        3052230,  # Hepacivirus hominis (Hep C)
    }
)

_UNICELLULAR_TAX_IDS: Final[frozenset[int]] = frozenset(
    {
        # Bacteria
        232,  # Alteromonas sp.
        271,  # Thermus aquaticus
        274,  # Thermus thermophilus
        287,  # Pseudomonas aeruginosa
        294,  # Pseudomonas fluorescens
        303,  # Pseudomonas putida
        480,  # Moraxella catarrhalis (b.catarr)
        485,  # Neisseria gonorrhoeae
        546,  # Citrobacter freundii
        548,  # Klebsiella aerogenes
        550,  # Enterobacter cloacae
        562,  # Escherichia coli
        571,  # Klebsiella oxytoca
        573,  # Klebsiella pneumoniae
        582,  # Morganella morganii
        584,  # Proteus mirabilis
        585,  # Proteus vulgaris
        615,  # Serratia marcescens
        632,  # Yersinia pestis
        671,  # Vibrio proteolyticus
        817,  # Bacteroides fragilis
        1280,  # Staphylococcus aureus
        1313,  # Streptococcus pneumoniae
        1393,  # Brevibacillus brevis
        1396,  # Bacillus cereus
        1402,  # Bacillus licheniformis
        1422,  # Geobacillus stearothermophilus
        1423,  # Bacillus subtilis
        1427,  # Bacillus thermoproteolyticus
        1467,  # Lederbergia lenta
        1582,  # Lacticaseibacillus casei
        1613,  # Limosilactobacillus fermentum
        1764,  # Mycobacterium avium
        1773,  # Mycobacterium tuberculosis
        13689,  # Sphingomonas paucimobilis
        31952,  # Streptomyces spp.
        40324,  # Stenotrophomonas maltophilia
        44001,  # Caldicellulosiruptor saccharolyticus
        158878,  # Staphylococcus aureus (strain)
        170187,  # Streptococcus pneumoniae TIGR4
        226185,  # Enterococcus faecalis V583
        # Archaea
        2210,  # Methanosarcina thermophila
        187420,  # Methanothermobacter thermautotrophicus
        # Unicellular eukaryotes (protists, yeasts)
        4754,  # Pneumocystis carinii
        5476,  # Candida albicans
        5656,  # Crithidia fasciculata
        5664,  # Leishmania major
        5665,  # Leishmania mexicana
        5691,  # Trypanosoma brucei
        5693,  # Trypanosoma cruzi
        5807,  # Cryptosporidium parvum
        5811,  # Toxoplasma gondii
        5833,  # Plasmodium falciparum
        5839,  # Plasmodium falciparum K1
        5888,  # Paramecium tetraurelia
        31286,  # Trypanosoma brucei rhodesiense
        36329,  # Plasmodium falciparum 3D7
        870730,  # Ogataea angusta (yeast)
    }
)

_MULTICELLULAR_TAX_IDS: Final[frozenset[int]] = frozenset(
    {
        # Animals (Metazoa)
        7052,  # Luciola lateralis
        7091,  # Bombyx mori
        7141,  # Choristoneura fumiferana
        7159,  # Aedes aegypti
        7227,  # Drosophila melanogaster
        7460,  # Apis mellifera
        7787,  # Torpedo californica
        7957,  # Carassius auratus
        8005,  # Electrophorus electricus (eel)
        8355,  # Xenopus laevis
        8643,  # Naja melanoleuca
        8644,  # Naja mocambique
        9031,  # Gallus gallus
        9103,  # Meleagris gallopavo
        9534,  # Chlorocebus aethiops (monkey)
        9541,  # Macaca fascicularis
        9544,  # Macaca mulatta
        9593,  # Gorilla gorilla
        9606,  # Homo sapiens
        9615,  # Canis lupus familiaris
        9796,  # Equus caballus
        9823,  # Sus scrofa
        9913,  # Bos taurus
        9940,  # Ovis aries
        9986,  # Oryctolagus cuniculus
        10029,  # Cricetulus griseus
        10036,  # Mesocricetus auratus (golden hamster)
        10090,  # Mus musculus
        10116,  # Rattus norvegicus
        10141,  # Cavia porcellus
        40353,  # Echis carinatus
        # Plants (Viridiplantae)
        3649,  # Carica papaya
        3847,  # Glycine max
        3888,  # Pisum sativum
        3988,  # Ricinus communis
        4577,  # Zea mays
        39947,  # Oryza sativa Japonica Group
        # Filamentous fungi
        4843,  # Rhizopus microsporus var. chinensis
        5061,  # Aspergillus niger
        5503,  # Curvularia lunata
        64493,  # Mucor hiemalis
        64495,  # Rhizopus arrhizus
    }
)


def _classify_by_taxonomy_id(taxonomy_id: int) -> CellularityType | None:
    """Classify by taxonomy ID using frozenset membership."""
    if taxonomy_id in _ACELLULAR_TAX_IDS:
        return CellularityType.ACELLULAR
    if taxonomy_id in _UNICELLULAR_TAX_IDS:
        return CellularityType.UNICELLULAR
    if taxonomy_id in _MULTICELLULAR_TAX_IDS:
        return CellularityType.MULTICELLULAR
    return None


# ---------------------------------------------------------------------------
# Organism name → CellularityType mapping
# ---------------------------------------------------------------------------

_ORGANISM_ALIAS_MAP: Final[dict[str, str]] = {
    "hiv": "human immunodeficiency virus 1",
    "rice": "oryza sativa japonica group",
    "eel": "electrophorus electricus",
    "monkey": "chlorocebus aethiops",
}

_ORGANISM_NAME_CLASS_MAP: Final[dict[str, CellularityType]] = {
    # Multicellular
    "homo sapiens": CellularityType.MULTICELLULAR,
    "mus musculus": CellularityType.MULTICELLULAR,
    "rattus norvegicus": CellularityType.MULTICELLULAR,
    "bos taurus": CellularityType.MULTICELLULAR,
    "sus scrofa": CellularityType.MULTICELLULAR,
    "glycine max": CellularityType.MULTICELLULAR,
    "oryza sativa japonica group": CellularityType.MULTICELLULAR,
    "electrophorus electricus": CellularityType.MULTICELLULAR,
    "chlorocebus aethiops": CellularityType.MULTICELLULAR,
    "macaca fascicularis": CellularityType.MULTICELLULAR,
    "macaca mulatta": CellularityType.MULTICELLULAR,
    "drosophila melanogaster": CellularityType.MULTICELLULAR,
    "xenopus laevis": CellularityType.MULTICELLULAR,
    "gallus gallus": CellularityType.MULTICELLULAR,
    "aspergillus niger": CellularityType.MULTICELLULAR,
    # Unicellular
    "escherichia coli": CellularityType.UNICELLULAR,
    "staphylococcus aureus": CellularityType.UNICELLULAR,
    "streptococcus pneumoniae": CellularityType.UNICELLULAR,
    "pseudomonas aeruginosa": CellularityType.UNICELLULAR,
    "mycobacterium tuberculosis": CellularityType.UNICELLULAR,
    "candida albicans": CellularityType.UNICELLULAR,
    "plasmodium falciparum": CellularityType.UNICELLULAR,
    "trypanosoma brucei": CellularityType.UNICELLULAR,
    "trypanosoma cruzi": CellularityType.UNICELLULAR,
    "leishmania major": CellularityType.UNICELLULAR,
    "toxoplasma gondii": CellularityType.UNICELLULAR,
    "methanosarcina thermophila": CellularityType.UNICELLULAR,
    # Acellular
    "human immunodeficiency virus 1": CellularityType.ACELLULAR,
    "human immunodeficiency virus 2": CellularityType.ACELLULAR,
    "influenza a virus": CellularityType.ACELLULAR,
    "enterobacteria phage lambda": CellularityType.ACELLULAR,
    "herpes simplex virus": CellularityType.ACELLULAR,
}

# Keyword heuristics for fallback classification (ordered by priority)
_ACELLULAR_KEYWORDS: Final[tuple[str, ...]] = (
    "virus",
    "viridae",
    "phage",
    "bacteriophage",
    "virion",
)
_UNICELLULAR_KEYWORDS: Final[tuple[str, ...]] = (
    "bacter",
    "bacillus",
    "coccus",
    "archaea",
    "archaeon",
    "yeast",
    "plasmodium",
    "candida",
    "leishmania",
    "trypanosoma",
)
_MULTICELLULAR_KEYWORDS: Final[tuple[str, ...]] = (
    "homo ",
    "mus ",
    "rattus",
    "glycine",
    "oryza",
    "macaca",
    "drosophila",
    "aspergillus",
)

_PARENTHESES_RE: Final[re.Pattern[str]] = re.compile(r"\s*\(.*\)")
_WHITESPACE_RE: Final[re.Pattern[str]] = re.compile(r"\s+")


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


_KEYWORD_GROUPS: Final[tuple[tuple[CellularityType, tuple[str, ...]], ...]] = (
    (CellularityType.ACELLULAR, _ACELLULAR_KEYWORDS),
    (CellularityType.UNICELLULAR, _UNICELLULAR_KEYWORDS),
    (CellularityType.MULTICELLULAR, _MULTICELLULAR_KEYWORDS),
)


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
