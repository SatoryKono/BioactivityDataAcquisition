"""Unified Bioactivity domain entity.

Contains the Bioactivity entity and associated types for ChEMBL/PubChem bioactivity data.
This module consolidates bioactivity representation into a single domain model.

Design Rationale:
    - Single source of truth for bioactivity representation in domain layer
    - State tracking via BioactivityState enum for processing lifecycle
    - Factory method from_raw() for creating from API data
    - Immutable (frozen dataclass) for thread safety

Field Classification:
    - REQUIRED: Validated in __post_init__, will raise ValueError if empty
    - API-OPTIONAL: May or may not be present in API response, defaults to None
    - COMPUTED: Derived from other fields, may be None if source data missing

Migration Note:
    The `Activity` class is now deprecated in favor of `Bioactivity`.
    Use `from bioetl.domain.entities import Bioactivity` for new code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.types import BatchID, ContentHash, EntityID, RunID, RunType


class BioactivityState(str, Enum):
    """Processing state of a bioactivity record.

    Tracks the lifecycle of a bioactivity record through the ETL pipeline.

    States:
        RAW: Initial state from API/Bronze layer, minimal validation
        NORMALIZED: Data normalized (types converted, nulls handled)
        VALIDATED: Full domain validation passed, ready for Silver/Gold

    Transitions:
        RAW -> NORMALIZED -> VALIDATED

    Note:
        State is informational and does not affect entity behavior.
        Use for observability and debugging of pipeline stages.
    """

    RAW = "raw"
    """Initial state from API/Bronze layer."""

    NORMALIZED = "normalized"
    """Data normalized and types converted."""

    VALIDATED = "validated"
    """Full validation passed, ready for persistence."""

    def is_ready_for_silver(self) -> bool:
        """Check if record is ready for Silver layer.

        Returns:
            True if state is NORMALIZED or VALIDATED.
        """
        return self in (BioactivityState.NORMALIZED, BioactivityState.VALIDATED)

    def is_fully_validated(self) -> bool:
        """Check if record passed full validation.

        Returns:
            True if state is VALIDATED.
        """
        return self == BioactivityState.VALIDATED


@dataclass(frozen=True, kw_only=True)
class Bioactivity(BaseEntity):
    """Unified bioactivity measurement entity.

    Represents a single bioactivity measurement from ChEMBL or similar sources.
    Contains all fields from ChEMBL activity API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/activity

    Required Fields (validated):
        activity_id: Primary identifier (from BaseEntity fields + this)
        molecule_chembl_id: Molecule identifier (required for drug discovery)
        + All BaseEntity fields (entity_id, content_hash, run_id, etc.)

    API-Optional Fields:
        All other fields may be None depending on the activity record.
        Gold layer filters should be used to ensure required fields for analysis.

    State Tracking:
        _state: Processing state for observability (default: VALIDATED)

    Validation:
        - activity_id and molecule_chembl_id must be non-empty
        - pchembl_value must be non-negative if present

    Example:
        >>> # Create from raw API data
        >>> bioactivity = Bioactivity.from_raw(
        ...     raw_data={"activity_id": 123, "molecule_chembl_id": "CHEMBL1"},
        ...     run_id=run_id,
        ...     ingestion_ts=datetime.now(UTC),
        ... )
        >>> bioactivity.state  # BioactivityState.RAW

        >>> # Create validated entity directly
        >>> bioactivity = Bioactivity(
        ...     entity_id=EntityID("ACT123"),
        ...     content_hash=ContentHash("abc123"),
        ...     run_id=run_id,
        ...     run_type=RunType.INCREMENTAL,
        ...     ingestion_ts=datetime.now(UTC),
        ...     _index=0,
        ...     activity_id="ACT123",
        ...     molecule_chembl_id="CHEMBL1",
        ... )
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
        """Current processing state of the bioactivity record.

        Returns:
            Processing state enum value.
        """
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
        """Factory method to create Bioactivity from raw API data.

        Creates a Bioactivity entity from raw API response data with minimal
        processing. The entity is created in RAW state.

        Args:
            raw_data: Raw dictionary from API response.
            run_id: Pipeline run identifier.
            run_type: Type of pipeline run.
            ingestion_ts: Ingestion timestamp.
            index: Record index in the batch.
            source_batch_id: Optional batch identifier.

        Returns:
            Bioactivity entity in RAW state.

        Raises:
            ValueError: If required fields are missing in raw_data.

        Example:
            >>> bioactivity = Bioactivity.from_raw(
            ...     raw_data=api_response,
            ...     run_id=uuid4(),
            ...     ingestion_ts=datetime.now(UTC),
            ... )
        """
        import hashlib
        import json

        # Extract required fields
        activity_id = raw_data.get("activity_id")
        if activity_id is None:
            raise ValueError("raw_data must contain 'activity_id'")

        molecule_chembl_id = raw_data.get("molecule_chembl_id")
        if molecule_chembl_id is None:
            raise ValueError("raw_data must contain 'molecule_chembl_id'")

        # Generate entity_id and content_hash
        entity_id = EntityID(str(activity_id))
        content_hash_str = hashlib.sha256(
            json.dumps(raw_data, sort_keys=True, default=str).encode()
        ).hexdigest()

        # Extract optional fields with safe type conversion
        def safe_int(val: Any) -> int | None:
            if val is None:
                return None
            try:
                return int(val)
            except (ValueError, TypeError):
                return None

        def safe_float(val: Any) -> float | None:
            if val is None:
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        def safe_str(val: Any) -> str | None:
            if val is None:
                return None
            return str(val)

        return cls(
            # BaseEntity fields
            entity_id=entity_id,
            content_hash=ContentHash(content_hash_str),
            run_id=RunID(run_id) if isinstance(run_id, UUID) else run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
            _index=index,
            source_batch_id=BatchID(source_batch_id) if source_batch_id else None,
            # State
            _state=BioactivityState.RAW,
            # Required fields
            activity_id=str(activity_id),
            molecule_chembl_id=str(molecule_chembl_id),
            # Optional identifiers
            target_chembl_id=safe_str(raw_data.get("target_chembl_id")),
            assay_chembl_id=safe_str(raw_data.get("assay_chembl_id")),
            document_chembl_id=safe_str(raw_data.get("document_chembl_id")),
            record_id=safe_int(raw_data.get("record_id")),
            src_id=safe_int(raw_data.get("src_id")),
            # Molecule data
            canonical_smiles=safe_str(raw_data.get("canonical_smiles")),
            molecule_pref_name=safe_str(raw_data.get("molecule_pref_name")),
            parent_molecule_chembl_id=safe_str(
                raw_data.get("parent_molecule_chembl_id")
            ),
            # Target data
            target_pref_name=safe_str(raw_data.get("target_pref_name")),
            target_organism=safe_str(raw_data.get("target_organism")),
            target_tax_id=safe_str(raw_data.get("target_tax_id")),
            # Assay data
            assay_type=safe_str(raw_data.get("assay_type")),
            assay_description=safe_str(raw_data.get("assay_description")),
            assay_variant_accession=safe_str(raw_data.get("assay_variant_accession")),
            assay_variant_mutation=safe_str(raw_data.get("assay_variant_mutation")),
            # BAO annotations
            bao_endpoint=safe_str(raw_data.get("bao_endpoint")),
            bao_format=safe_str(raw_data.get("bao_format")),
            bao_label=safe_str(raw_data.get("bao_label")),
            # Raw activity values
            type=safe_str(raw_data.get("type")),
            value=safe_float(raw_data.get("value")),
            units=safe_str(raw_data.get("units")),
            relation=safe_str(raw_data.get("relation")),
            upper_value=safe_float(raw_data.get("upper_value")),
            text_value=safe_str(raw_data.get("text_value")),
            # Standardized values
            standard_type=safe_str(raw_data.get("standard_type")),
            standard_value=safe_float(raw_data.get("standard_value")),
            standard_units=safe_str(raw_data.get("standard_units")),
            standard_relation=safe_str(raw_data.get("standard_relation")),
            standard_upper_value=safe_float(raw_data.get("standard_upper_value")),
            standard_text_value=safe_str(raw_data.get("standard_text_value")),
            standard_flag=safe_int(raw_data.get("standard_flag")),
            # Derived metrics
            pchembl_value=safe_float(raw_data.get("pchembl_value")),
            # Document data
            document_journal=safe_str(raw_data.get("document_journal")),
            document_year=safe_int(raw_data.get("document_year")),
            # Quality annotations
            activity_comment=safe_str(raw_data.get("activity_comment")),
            data_validity_comment=safe_str(raw_data.get("data_validity_comment")),
            data_validity_description=safe_str(
                raw_data.get("data_validity_description")
            ),
            potential_duplicate=safe_int(raw_data.get("potential_duplicate")),
            # Activity properties
            activity_properties=(
                json.dumps(raw_data.get("activity_properties"))
                if raw_data.get("activity_properties")
                else None
            ),
            toid=safe_int(raw_data.get("toid")),
        )

    def with_state(self, new_state: BioactivityState) -> Bioactivity:
        """Create a copy with a new processing state.

        Since Bioactivity is immutable (frozen dataclass), this method
        creates a new instance with the updated state.

        Args:
            new_state: The new processing state.

        Returns:
            New Bioactivity instance with updated state.

        Example:
            >>> raw = Bioactivity.from_raw(...)
            >>> normalized = raw.with_state(BioactivityState.NORMALIZED)
        """
        from dataclasses import asdict

        data = asdict(self)
        data["_state"] = new_state
        return Bioactivity(**data)


# Backward compatibility alias with deprecation warning
def _create_activity_alias() -> type[Bioactivity]:
    """Create deprecated Activity alias.

    Returns:
        Bioactivity class with deprecation warning on instantiation.
    """
    import warnings

    class Activity(Bioactivity):
        """Deprecated alias for Bioactivity.

        .. deprecated:: 1.0.0
            Use :class:`Bioactivity` instead. This alias will be removed in 14 days.
        """

        def __init__(self, **kwargs: Any) -> None:
            warnings.warn(
                "Activity is deprecated, use Bioactivity instead. "
                "This alias will be removed in 14 days.",
                DeprecationWarning,
                stacklevel=2,
            )
            super().__init__(**kwargs)

    return Activity


# Note: Activity alias is created in chembl_activity.py for backward compatibility
