"""Target and publication vocab owned by the ChEMBL enum catalog."""

from __future__ import annotations

TARGET_TYPES: frozenset[str] = frozenset(
    [
        "SINGLE PROTEIN",
        "PROTEIN FAMILY",
        "PROTEIN COMPLEX",
        "PROTEIN COMPLEX GROUP",
        "SELECTIVITY GROUP",
        "CHIMERIC PROTEIN",
        "CELL-LINE",
        "TISSUE",
        "ORGANISM",
        "MACROMOLECULE",
        "SMALL MOLECULE",
        "LIPID",
        "METAL",
        "UNKNOWN",
    ]
)

TARGET_COMPONENT_RELATIONSHIPS: frozenset[str] = frozenset(
    [
        "SINGLE PROTEIN",
        "PROTEIN SUBUNIT",
        "RNA",
        "INTERACTING PROTEIN",
    ]
)

TARGET_COMPONENT_TYPES: frozenset[str] = frozenset(["PROTEIN", "DNA", "RNA"])
TARGET_ORGANISM_CLASSES: frozenset[str] = frozenset(
    ["acellular", "unicellular", "multicellular"]
)

PUBLICATION_TYPES: frozenset[str] = frozenset(
    [
        "journal-article",
        "patent",
        "dataset",
        "book",
        "review",
        "letter",
        "editorial",
        "clinical-trial",
        "meta-analysis",
        "case-reports",
        "comparative-study",
        "evaluation-study",
        "preprint",
        "book-chapter",
        "proceedings-article",
        "posted-content",
        "report",
        "standard",
        "dissertation",
        "other",
    ]
)

OA_STATUS_VALUES: tuple[str, ...] = (
    "gold",
    "green",
    "hybrid",
    "bronze",
    "closed",
    "diamond",
)

PUBLICATION_TERM_TYPES: frozenset[str] = frozenset(
    ["MESH_HEADING", "MESH_QUALIFIER", "KEYWORD"]
)

__all__ = [
    "OA_STATUS_VALUES",
    "PUBLICATION_TERM_TYPES",
    "PUBLICATION_TYPES",
    "TARGET_COMPONENT_RELATIONSHIPS",
    "TARGET_COMPONENT_TYPES",
    "TARGET_ORGANISM_CLASSES",
    "TARGET_TYPES",
]
