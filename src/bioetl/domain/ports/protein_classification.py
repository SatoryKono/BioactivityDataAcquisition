"""Protein classification resolution port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassHierarchy,
)

__all__ = ["ProteinClassificationPort"]


@runtime_checkable
class ProteinClassificationPort(Protocol):
    """Resolve protein class hierarchies for a target component."""

    def get_component_classifications(
        self,
        component_id: int,
    ) -> tuple[ProteinClassHierarchy, ...]:
        """Return deterministic protein class hierarchies for a component."""
        ...
