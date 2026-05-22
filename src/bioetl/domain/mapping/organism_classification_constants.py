"""Lookup tables and helpers for organism cellularity classification."""

from __future__ import annotations

import re
from typing import Final

from bioetl.domain.types import CellularityType

ACELLULAR_TAX_IDS: Final[frozenset[int]] = frozenset(
    {
        10298,
        10299,
        10309,
        10310,
        10335,
        10360,
        10580,
        10665,
        10710,
        11676,
        11679,
        11709,
        11866,
        11926,
        11970,
        132504,
        169066,
        211044,
        694009,
        3052230,
    }
)

UNICELLULAR_TAX_IDS: Final[frozenset[int]] = frozenset(
    {
        232,
        271,
        274,
        287,
        294,
        303,
        480,
        485,
        546,
        548,
        550,
        562,
        571,
        573,
        582,
        584,
        585,
        615,
        632,
        671,
        817,
        1280,
        1313,
        1393,
        1396,
        1402,
        1422,
        1423,
        1427,
        1467,
        1582,
        1613,
        1764,
        1773,
        13689,
        31952,
        40324,
        44001,
        158878,
        170187,
        226185,
        2210,
        187420,
        4754,
        5476,
        5656,
        5664,
        5665,
        5691,
        5693,
        5807,
        5811,
        5833,
        5839,
        5888,
        31286,
        36329,
        870730,
    }
)

MULTICELLULAR_TAX_IDS: Final[frozenset[int]] = frozenset(
    {
        7052,
        7091,
        7141,
        7159,
        7227,
        7460,
        7787,
        7957,
        8005,
        8355,
        8643,
        8644,
        9031,
        9103,
        9534,
        9541,
        9544,
        9593,
        9606,
        9615,
        9796,
        9823,
        9913,
        9940,
        9986,
        10029,
        10036,
        10090,
        10116,
        10141,
        40353,
        3649,
        3847,
        3888,
        3988,
        4577,
        39947,
        4843,
        5061,
        5503,
        64493,
        64495,
    }
)

ORGANISM_ALIAS_MAP: Final[dict[str, str]] = {
    "hiv": "human immunodeficiency virus 1",
    "rice": "oryza sativa japonica group",
    "eel": "electrophorus electricus",
    "monkey": "chlorocebus aethiops",
}

ORGANISM_NAME_CLASS_MAP: Final[dict[str, CellularityType]] = {
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
    "human immunodeficiency virus 1": CellularityType.ACELLULAR,
    "human immunodeficiency virus 2": CellularityType.ACELLULAR,
    "influenza a virus": CellularityType.ACELLULAR,
    "enterobacteria phage lambda": CellularityType.ACELLULAR,
    "herpes simplex virus": CellularityType.ACELLULAR,
}

ORGANISM_GENUS_CLASS_MAP: Final[dict[str, CellularityType]] = {
    # Mammals and other vertebrates
    "callithrix": CellularityType.MULTICELLULAR,
    "canis": CellularityType.MULTICELLULAR,
    "cavia": CellularityType.MULTICELLULAR,
    "danio": CellularityType.MULTICELLULAR,
    "equus": CellularityType.MULTICELLULAR,
    "lymnaea": CellularityType.MULTICELLULAR,
    "luciola": CellularityType.MULTICELLULAR,
    "meleagris": CellularityType.MULTICELLULAR,
    "mesocricetus": CellularityType.MULTICELLULAR,
    "oryctolagus": CellularityType.MULTICELLULAR,
    "ovis": CellularityType.MULTICELLULAR,
    "torpedo": CellularityType.MULTICELLULAR,
    # Invertebrates and helminths
    "anopheles": CellularityType.MULTICELLULAR,
    "apis": CellularityType.MULTICELLULAR,
    "aplysia": CellularityType.MULTICELLULAR,
    "dermatophagoides": CellularityType.MULTICELLULAR,
    "onchocerca": CellularityType.MULTICELLULAR,
    "patiria": CellularityType.MULTICELLULAR,
    "photinus": CellularityType.MULTICELLULAR,
    "photuris": CellularityType.MULTICELLULAR,
    "schistosoma": CellularityType.MULTICELLULAR,
    # Plants
    "arabidopsis": CellularityType.MULTICELLULAR,
    "canavalia": CellularityType.MULTICELLULAR,
    "carica": CellularityType.MULTICELLULAR,
    "flaveria": CellularityType.MULTICELLULAR,
    "ricinus": CellularityType.MULTICELLULAR,
    "solanum": CellularityType.MULTICELLULAR,
    "spinacia": CellularityType.MULTICELLULAR,
    "zea": CellularityType.MULTICELLULAR,
    # Fungi
    "agaricus": CellularityType.MULTICELLULAR,
    "malassezia": CellularityType.UNICELLULAR,
    "pneumocystis": CellularityType.UNICELLULAR,
    "trichophyton": CellularityType.MULTICELLULAR,
    # Bacteria
    "aeromonas": CellularityType.UNICELLULAR,
    "alcaligenes": CellularityType.UNICELLULAR,
    "aliivibrio": CellularityType.UNICELLULAR,
    "clostridium": CellularityType.UNICELLULAR,
    "francisella": CellularityType.UNICELLULAR,
    "klebsiella": CellularityType.UNICELLULAR,
    "magnetospirillum": CellularityType.UNICELLULAR,
    "neisseria": CellularityType.UNICELLULAR,
    "peptoclostridium": CellularityType.UNICELLULAR,
    "pseudomonas": CellularityType.UNICELLULAR,
    "serratia": CellularityType.UNICELLULAR,
    "stenotrophomonas": CellularityType.UNICELLULAR,
    "yersinia": CellularityType.UNICELLULAR,
    # Protists and algae
    "chlamydomonas": CellularityType.UNICELLULAR,
    "crithidia": CellularityType.UNICELLULAR,
    "cryptosporidium": CellularityType.UNICELLULAR,
    "eimeria": CellularityType.UNICELLULAR,
}

ACELLULAR_KEYWORDS: Final[tuple[str, ...]] = (
    "virus",
    "viridae",
    "phage",
    "bacteriophage",
    "virion",
)
UNICELLULAR_KEYWORDS: Final[tuple[str, ...]] = (
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
MULTICELLULAR_KEYWORDS: Final[tuple[str, ...]] = (
    "homo ",
    "mus ",
    "rattus",
    "glycine",
    "oryza",
    "macaca",
    "drosophila",
    "aspergillus",
)

KEYWORD_GROUPS: Final[tuple[tuple[CellularityType, tuple[str, ...]], ...]] = (
    (CellularityType.ACELLULAR, ACELLULAR_KEYWORDS),
    (CellularityType.UNICELLULAR, UNICELLULAR_KEYWORDS),
    (CellularityType.MULTICELLULAR, MULTICELLULAR_KEYWORDS),
)

PARENTHESES_RE: Final[re.Pattern[str]] = re.compile(r"\s*\(.*\)")
WHITESPACE_RE: Final[re.Pattern[str]] = re.compile(r"\s+")


def classify_by_taxonomy_id(taxonomy_id: int) -> CellularityType | None:
    """Classify by taxonomy ID using frozenset membership.

    Args:
        taxonomy_id: NCBI taxonomy ID to classify.

    Returns:
        CellularityType if the taxonomy ID is in a known frozenset, None if unclassified.
    """
    if taxonomy_id in ACELLULAR_TAX_IDS:
        return CellularityType.ACELLULAR
    if taxonomy_id in UNICELLULAR_TAX_IDS:
        return CellularityType.UNICELLULAR
    if taxonomy_id in MULTICELLULAR_TAX_IDS:
        return CellularityType.MULTICELLULAR
    return None
