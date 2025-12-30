"""Unified Bioactivity domain entity.

Single source of truth for bioactivity representation in domain layer.
State tracking via BioactivityState enum. Factory method from_raw() for API data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.types import BatchID, ContentHash, EntityID, RunID, RunType


def _safe_int(val: Any) -> int | None:
    """Convert value to int or None."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val: Any) -> float | None:
    """Convert value to float or None."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_str(val: Any) -> str | None:
    """Convert value to str or None."""
    return None if val is None else str(val)


def _validate_required_fields(activity_id: Any, molecule_chembl_id: Any) -> None:
    """Validate required fields for Bioactivity creation."""
    if activity_id is None:
        raise ValueError("raw_data must contain 'activity_id'")
    if molecule_chembl_id is None:
        raise ValueError("raw_data must contain 'molecule_chembl_id'")


class BioactivityState(str, Enum):
    """Processing state: RAW -> NORMALIZED -> VALIDATED."""

    RAW = "raw"
    NORMALIZED = "normalized"
    VALIDATED = "validated"

    def is_ready_for_silver(self) -> bool:
        """Check if record is ready for Silver layer."""
        return self in (BioactivityState.NORMALIZED, BioactivityState.VALIDATED)

    def is_fully_validated(self) -> bool:
        """Check if record passed full validation."""
        return self == BioactivityState.VALIDATED


@dataclass(frozen=True, kw_only=True)
class Bioactivity(BaseEntity):
    """Unified bioactivity measurement from ChEMBL.

    Required: activity_id, molecule_chembl_id (validated in __post_init__).
    All other fields are optional from API response.
    """

    # Processing state (informational, does not affect behavior)
    _state: BioactivityState = BioactivityState.VALIDATED

    # REQUIRED: Primary identifier (validated in __post_init__)
    activity_id: str

    # REQUIRED: Core identifiers (validated in __post_init__)
    molecule_chembl_id: str
    target_chembl_id: str | None = None
    assay_chembl_id: str | None = None
    document_chembl_id: str | None = None
    record_id: int | None = None
    src_id: int | None = None

    # Molecule data
    canonical_smiles: str | None = None
    molecule_pref_name: str | None = None
    parent_molecule_chembl_id: str | None = None

    # Target data
    target_pref_name: str | None = None
    target_organism: str | None = None
    target_tax_id: str | None = None

    # Assay data
    assay_type: str | None = None
    assay_description: str | None = None
    assay_variant_accession: str | None = None
    assay_variant_mutation: str | None = None

    # BAO (BioAssay Ontology) annotations
    bao_endpoint: str | None = None
    bao_format: str | None = None
    bao_label: str | None = None

    # Raw activity values
    type: str | None = None
    value: float | None = None
    units: str | None = None
    relation: str | None = None
    upper_value: float | None = None
    text_value: str | None = None

    # Standardized activity values
    standard_type: str | None = None
    standard_value: float | None = None
    standard_units: str | None = None
    standard_relation: str | None = None
    standard_upper_value: float | None = None
    standard_text_value: str | None = None
    standard_flag: int | None = None

    # Derived metrics
    pchembl_value: float | None = None

    # Ligand efficiency metrics (flattened from ChEMBL API dict)
    ligand_efficiency_bei: float | None = None  # Binding Efficiency Index
    ligand_efficiency_le: float | None = None  # Ligand Efficiency
    ligand_efficiency_lle: float | None = None  # Lipophilic Ligand Efficiency
    ligand_efficiency_sei: float | None = None  # Surface Efficiency Index

    # Units ontology
    qudt_units: str | None = None
    uo_units: str | None = None

    # Document/Publication data
    document_journal: str | None = None
    document_year: int | None = None

    # Quality annotations
    activity_comment: str | None = None
    data_validity_comment: str | None = None
    data_validity_description: str | None = None
    potential_duplicate: int | None = None

    # Action type (flattened from ChEMBL API nested structure)
    action_type_action_type: str | None = (
        None  # Type of action (INHIBITOR, AGONIST, etc.)
    )
    action_type_description: str | None = None  # Description of the action type
    action_type_parent_type: str | None = None  # Higher-level grouping (nullable)

    # Activity properties
    activity_properties: str | None = None  # JSON string of list
    toid: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        """Validate business invariants.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        if not self.activity_id:
            raise ValueError("Activity ID is required")
        if not self.molecule_chembl_id:
            raise ValueError("Molecule ID is required")
        self._validate_pchembl_value()

    def _validate_pchembl_value(self) -> None:
        """Validate pchembl_value is non-negative if present.

        Raises:
            ValueError: If pchembl_value is negative.
        """
        if self.pchembl_value is not None and self.pchembl_value < 0:
            raise ValueError(
                f"pChemBL value must be non-negative, got {self.pchembl_value}"
            )

    @property
    def state(self) -> BioactivityState:
        """Current processing state."""
        return self._state

    @classmethod
    def from_raw(
        cls,
        *,
        raw_data: dict[str, Any],
        run_id: RunID | UUID,
        run_type: RunType = RunType.INCREMENTAL,
        ingestion_ts: datetime,
        index: int = 0,
        source_batch_id: UUID | None = None,
    ) -> Bioactivity:
        """Create Bioactivity from raw API data in RAW state."""
        import hashlib
        import json

        activity_id = raw_data.get("activity_id")
        molecule_chembl_id = raw_data.get("molecule_chembl_id")
        _validate_required_fields(activity_id, molecule_chembl_id)

        entity_id = EntityID(str(activity_id))
        content_hash_str = hashlib.sha256(
            json.dumps(raw_data, sort_keys=True, default=str).encode()
        ).hexdigest()

        return cls(
            entity_id=entity_id,
            content_hash=ContentHash(content_hash_str),
            run_id=RunID(run_id) if isinstance(run_id, UUID) else run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
            _index=index,
            source_batch_id=BatchID(source_batch_id) if source_batch_id else None,
            _state=BioactivityState.RAW,
            activity_id=str(activity_id),
            molecule_chembl_id=str(molecule_chembl_id),
            target_chembl_id=_safe_str(raw_data.get("target_chembl_id")),
            assay_chembl_id=_safe_str(raw_data.get("assay_chembl_id")),
            document_chembl_id=_safe_str(raw_data.get("document_chembl_id")),
            record_id=_safe_int(raw_data.get("record_id")),
            src_id=_safe_int(raw_data.get("src_id")),
            canonical_smiles=_safe_str(raw_data.get("canonical_smiles")),
            molecule_pref_name=_safe_str(raw_data.get("molecule_pref_name")),
            parent_molecule_chembl_id=_safe_str(
                raw_data.get("parent_molecule_chembl_id")
            ),
            target_pref_name=_safe_str(raw_data.get("target_pref_name")),
            target_organism=_safe_str(raw_data.get("target_organism")),
            target_tax_id=_safe_str(raw_data.get("target_tax_id")),
            assay_type=_safe_str(raw_data.get("assay_type")),
            assay_description=_safe_str(raw_data.get("assay_description")),
            assay_variant_accession=_safe_str(raw_data.get("assay_variant_accession")),
            assay_variant_mutation=_safe_str(raw_data.get("assay_variant_mutation")),
            bao_endpoint=_safe_str(raw_data.get("bao_endpoint")),
            bao_format=_safe_str(raw_data.get("bao_format")),
            bao_label=_safe_str(raw_data.get("bao_label")),
            type=_safe_str(raw_data.get("type")),
            value=_safe_float(raw_data.get("value")),
            units=_safe_str(raw_data.get("units")),
            relation=_safe_str(raw_data.get("relation")),
            upper_value=_safe_float(raw_data.get("upper_value")),
            text_value=_safe_str(raw_data.get("text_value")),
            standard_type=_safe_str(raw_data.get("standard_type")),
            standard_value=_safe_float(raw_data.get("standard_value")),
            standard_units=_safe_str(raw_data.get("standard_units")),
            standard_relation=_safe_str(raw_data.get("standard_relation")),
            standard_upper_value=_safe_float(raw_data.get("standard_upper_value")),
            standard_text_value=_safe_str(raw_data.get("standard_text_value")),
            standard_flag=_safe_int(raw_data.get("standard_flag")),
            pchembl_value=_safe_float(raw_data.get("pchembl_value")),
            document_journal=_safe_str(raw_data.get("document_journal")),
            document_year=_safe_int(raw_data.get("document_year")),
            activity_comment=_safe_str(raw_data.get("activity_comment")),
            data_validity_comment=_safe_str(raw_data.get("data_validity_comment")),
            data_validity_description=_safe_str(
                raw_data.get("data_validity_description")
            ),
            potential_duplicate=_safe_int(raw_data.get("potential_duplicate")),
            activity_properties=(
                json.dumps(raw_data.get("activity_properties"))
                if raw_data.get("activity_properties")
                else None
            ),
            toid=_safe_int(raw_data.get("toid")),
        )

    def with_state(self, new_state: BioactivityState) -> Bioactivity:
        """Create a copy with a new processing state."""
        from dataclasses import asdict

        data = asdict(self)
        data["_state"] = new_state
        return Bioactivity(**data)
