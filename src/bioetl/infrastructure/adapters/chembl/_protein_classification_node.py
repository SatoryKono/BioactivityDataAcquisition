"""Node dataclass for ChEMBL protein classification graph."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ProteinClassificationNode"]


@dataclass(frozen=True, slots=True)
class ProteinClassificationNode:
    """One ChEMBL protein_classification node."""

    protein_class_id: int
    parent_id: int | None
    class_level: int | None
    pref_name: str | None = None
    protein_class_desc: str | None = None
    replaced_by: int | None = None
