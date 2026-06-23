"""Lookup tables and helpers for organism cellularity classification."""

from __future__ import annotations

import re
from typing import Final

from bioetl.domain.types import CellularityType

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
    "ascaris suum": CellularityType.MULTICELLULAR,
    "caenorhabditis elegans": CellularityType.MULTICELLULAR,
    "penicillium chrysogenum": CellularityType.MULTICELLULAR,
    "saccharomyces cerevisiae": CellularityType.UNICELLULAR,
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
    "ascaris": CellularityType.MULTICELLULAR,
    "caenorhabditis": CellularityType.MULTICELLULAR,
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
    "penicillium": CellularityType.MULTICELLULAR,
    "pneumocystis": CellularityType.UNICELLULAR,
    "saccharomyces": CellularityType.UNICELLULAR,
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
