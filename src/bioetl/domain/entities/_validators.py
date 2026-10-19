"""Shared pure validators for domain entity invariants."""

from __future__ import annotations

__all__ = [
    "require_non_empty_str",
    "require_positive_id",
    "require_structure_identifier",
]


def require_structure_identifier(
    canonical_smiles: str | None,
    isomeric_smiles: str | None,
    inchi: str | None,
    entity_name: str,
) -> None:
    """Require a non-empty SMILES or InChI; an InChI key alone is insufficient."""
    if not (canonical_smiles or isomeric_smiles or inchi):
        raise ValueError(
            f"{entity_name} must have at least one structural identifier (SMILES/InChI)"
        )


def require_positive_id(value: int, field_name: str) -> None:
    """Raise ValueError when ``value`` is not a positive integer."""
    if value < 1:
        raise ValueError(f"{field_name} must be > 0, got {value}")


def require_non_empty_str(value: str, field_name: str) -> None:
    """Raise ValueError when ``value`` is empty or whitespace-only."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
