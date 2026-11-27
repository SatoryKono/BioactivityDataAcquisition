"""Exact identity keys for approved local target-class assignments."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .policy import EC_SINGULAR, WORKING_CLASSES

ReviewKey = tuple[str, str, str]
_CLASSES = frozenset(
    (
        *WORKING_CLASSES,
        *(f"Enzyme.{category}" for _, category in EC_SINGULAR),
        "Enzyme.Multitarget",
        "Receptor.Nuclear receptor",
    )
)


@dataclass(frozen=True, slots=True)
class ReviewedClass:
    """A reviewed class with a reference to its identity and class evidence."""

    target_chembl_id: str
    taxon: str
    primary_uniprot: str
    effective_class: str
    origin: str
    reference: str

    def __post_init__(self) -> None:
        if not (
            re.fullmatch(r"CHEMBL[1-9]\d*", self.target_chembl_id, re.ASCII)
            and re.fullmatch(r"[1-9]\d*", self.taxon, re.ASCII)
            and re.fullmatch(
                r"[A-Z\d]{6,10}(?:-[1-9]\d*)?", self.primary_uniprot, re.ASCII
            )
        ):
            raise ValueError("invalid reviewed target identity key")
        if self.effective_class not in _CLASSES:
            raise ValueError("unrecognized reviewed effective class")
        if (
            self.origin not in {"manual_review", "ortholog"}
            or not self.reference.strip()
        ):
            raise ValueError("reviewed class requires an origin and evidence reference")

    @property
    def key(self) -> ReviewKey:
        return self.target_chembl_id, self.taxon, self.primary_uniprot
