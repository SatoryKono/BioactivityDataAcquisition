"""Governed chemical structure standardization policies.

The current PubChem policy is intentionally dependency-free: it trims and
validates structural identifiers using existing domain value objects, derives a
stable parent key when safe, and records visible warnings for operations that
require a chemistry toolkit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bioetl.domain.value_objects import SMILES, InChIKey

ChemicalStandardizationStatus = Literal[
    "standardized",
    "partial",
    "invalid",
    "missing_structure",
]

CHEMICAL_STANDARDIZATION_POLICY_VERSION = "pubchem-basic-v1"
CHEMICAL_STANDARDIZATION_STATUSES: tuple[ChemicalStandardizationStatus, ...] = (
    "standardized",
    "partial",
    "invalid",
    "missing_structure",
)


@dataclass(frozen=True, slots=True)
class ChemicalStandardizationResult:
    """Result of a deterministic chemical structure standardization pass."""

    standardized_canonical_smiles: str | None
    standardized_isomeric_smiles: str | None
    standardized_inchi: str | None
    standardized_inchi_key: str | None
    structure_parent_key: str | None
    chemical_standardization_status: ChemicalStandardizationStatus
    chemical_standardization_warnings: tuple[str, ...]
    chemical_standardization_policy_version: str = (
        CHEMICAL_STANDARDIZATION_POLICY_VERSION
    )


def standardize_chemical_structure(
    *,
    canonical_smiles: object,
    isomeric_smiles: object,
    inchi: object,
    inchi_key: object,
    covalent_unit_count: int | None = None,
    charge: int | None = None,
) -> ChemicalStandardizationResult:
    """Standardize PubChem structural identifiers before hash/merge operations."""
    warnings: list[str] = []
    standardized_canonical_smiles = _normalize_smiles(
        canonical_smiles,
        field_name="canonical_smiles",
        is_canonical=True,
        warnings=warnings,
    )
    standardized_isomeric_smiles = _normalize_smiles(
        isomeric_smiles,
        field_name="isomeric_smiles",
        is_canonical=False,
        warnings=warnings,
    )
    standardized_inchi = _normalize_inchi(inchi, warnings=warnings)
    standardized_inchi_key = _normalize_inchi_key(inchi_key, warnings=warnings)

    _record_parent_deferred_warnings(
        standardized_canonical_smiles=standardized_canonical_smiles,
        standardized_isomeric_smiles=standardized_isomeric_smiles,
        covalent_unit_count=covalent_unit_count,
        charge=charge,
        warnings=warnings,
    )
    structure_parent_key = _derive_structure_parent_key(
        standardized_canonical_smiles=standardized_canonical_smiles,
        standardized_inchi_key=standardized_inchi_key,
        warnings=warnings,
    )
    status = _resolve_standardization_status(
        raw_values=(canonical_smiles, isomeric_smiles, inchi, inchi_key),
        standardized_values=(
            standardized_canonical_smiles,
            standardized_isomeric_smiles,
            standardized_inchi,
            standardized_inchi_key,
        ),
        warnings=warnings,
    )
    return ChemicalStandardizationResult(
        standardized_canonical_smiles=standardized_canonical_smiles,
        standardized_isomeric_smiles=standardized_isomeric_smiles,
        standardized_inchi=standardized_inchi,
        standardized_inchi_key=standardized_inchi_key,
        structure_parent_key=structure_parent_key,
        chemical_standardization_status=status,
        chemical_standardization_warnings=_unique_warning_codes(warnings),
    )


def _normalize_smiles(
    value: object,
    *,
    field_name: str,
    is_canonical: bool,
    warnings: list[str],
) -> str | None:
    """Normalize one SMILES value using the domain SMILES value object."""
    if _is_blank(value):
        return None
    if not isinstance(value, str):
        warnings.append(f"{field_name}_invalid")
        return None
    smiles = SMILES.from_raw(value, is_canonical=is_canonical, mode="soft")
    if smiles is None:
        warnings.append(f"{field_name}_invalid")
        return None
    return smiles.value


def _normalize_inchi(value: object, *, warnings: list[str]) -> str | None:
    """Normalize an InChI identifier using the repository's basic contract."""
    if _is_blank(value):
        return None
    if not isinstance(value, str):
        warnings.append("inchi_invalid")
        return None
    normalized = value.strip()
    if not normalized.startswith("InChI="):
        warnings.append("inchi_invalid")
        return None
    return normalized


def _normalize_inchi_key(value: object, *, warnings: list[str]) -> str | None:
    """Normalize an InChIKey value using the domain value object."""
    if _is_blank(value):
        return None
    if not isinstance(value, str):
        warnings.append("inchi_key_invalid")
        return None
    inchi_key = InChIKey.from_raw(value)
    if inchi_key is None:
        warnings.append("inchi_key_invalid")
        return None
    return str(inchi_key.value)


def _record_parent_deferred_warnings(
    *,
    standardized_canonical_smiles: str | None,
    standardized_isomeric_smiles: str | None,
    covalent_unit_count: int | None,
    charge: int | None,
    warnings: list[str],
) -> None:
    """Record visible warnings for unsupported parent normalization cases."""
    if _has_parent_deferred_multi_component_input(
        covalent_unit_count=covalent_unit_count,
        standardized_canonical_smiles=standardized_canonical_smiles,
        standardized_isomeric_smiles=standardized_isomeric_smiles,
    ):
        warnings.append("multi_component_parent_deferred")
    if _has_nonzero_charge(charge):
        warnings.append("charge_normalization_deferred")


def _derive_structure_parent_key(
    *,
    standardized_canonical_smiles: str | None,
    standardized_inchi_key: str | None,
    warnings: list[str],
) -> str | None:
    """Derive a stable structure key without mutating chemistry semantics."""
    if standardized_inchi_key is not None:
        connectivity_layer = standardized_inchi_key.split("-", maxsplit=1)[0]
        return f"inchikey14:{connectivity_layer}"
    if standardized_canonical_smiles is not None:
        if _has_multi_component_smiles(standardized_canonical_smiles):
            warnings.append("structure_parent_key_unavailable")
            return None
        warnings.append("parent_key_from_smiles_without_inchi_key")
        return f"smiles:{standardized_canonical_smiles}"
    warnings.append("structure_parent_key_unavailable")
    return None


def _resolve_standardization_status(
    *,
    raw_values: tuple[object, ...],
    standardized_values: tuple[str | None, ...],
    warnings: list[str],
) -> ChemicalStandardizationStatus:
    """Resolve the bounded status from raw inputs and normalized outputs."""
    if not _has_any_raw_structure(raw_values):
        return "missing_structure"
    if not _has_any_standardized_structure(standardized_values):
        return "invalid"
    if warnings:
        return "partial"
    return "standardized"


def _has_parent_deferred_multi_component_input(
    *,
    covalent_unit_count: int | None,
    standardized_canonical_smiles: str | None,
    standardized_isomeric_smiles: str | None,
) -> bool:
    """Return whether parent normalization is deferred for multi-component input."""
    if covalent_unit_count is not None and covalent_unit_count > 1:
        return True
    return _has_multi_component_smiles(
        standardized_canonical_smiles
    ) or _has_multi_component_smiles(standardized_isomeric_smiles)


def _has_nonzero_charge(charge: int | None) -> bool:
    """Return whether charge normalization remains deferred."""
    return charge not in (None, 0)


def _has_any_raw_structure(raw_values: tuple[object, ...]) -> bool:
    """Return whether at least one raw structure input is present."""
    return any(not _is_blank(value) for value in raw_values)


def _has_any_standardized_structure(
    standardized_values: tuple[str | None, ...],
) -> bool:
    """Return whether at least one standardized structure was produced."""
    return any(value is not None for value in standardized_values)


def _is_blank(value: object) -> bool:
    """Return whether a raw structure value is absent or blank."""
    return value is None or (isinstance(value, str) and not value.strip())


def _has_multi_component_smiles(value: str | None) -> bool:
    """Detect multi-component SMILES strings that need toolkit-based parenting."""
    return value is not None and "." in value


def _unique_warning_codes(warnings: list[str]) -> tuple[str, ...]:
    """Return warning codes in deterministic first-seen order."""
    return tuple(dict.fromkeys(warnings))


__all__ = [
    "CHEMICAL_STANDARDIZATION_POLICY_VERSION",
    "CHEMICAL_STANDARDIZATION_STATUSES",
    "ChemicalStandardizationResult",
    "ChemicalStandardizationStatus",
    "standardize_chemical_structure",
]
