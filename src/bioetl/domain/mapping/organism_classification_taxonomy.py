"""Taxonomy-ID lookup tables for organism cellularity classification."""

from __future__ import annotations

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
        2210,
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
        13689,
        31286,
        31952,
        36329,
        40324,
        44001,
        158878,
        170187,
        187420,
        226185,
        559292,
        870730,
    }
)

MULTICELLULAR_TAX_IDS: Final[frozenset[int]] = frozenset(
    {
        3649,
        3847,
        3888,
        3988,
        4577,
        4843,
        5061,
        5076,
        5503,
        6239,
        6253,
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
        39947,
        40353,
        64493,
        64495,
    }
)


def classify_by_taxonomy_id(taxonomy_id: int) -> CellularityType | None:
    """Classify by taxonomy ID using frozenset membership."""
    if taxonomy_id in ACELLULAR_TAX_IDS:
        return CellularityType.ACELLULAR
    if taxonomy_id in UNICELLULAR_TAX_IDS:
        return CellularityType.UNICELLULAR
    if taxonomy_id in MULTICELLULAR_TAX_IDS:
        return CellularityType.MULTICELLULAR
    return None


__all__ = [
    "ACELLULAR_TAX_IDS",
    "MULTICELLULAR_TAX_IDS",
    "UNICELLULAR_TAX_IDS",
    "classify_by_taxonomy_id",
]
