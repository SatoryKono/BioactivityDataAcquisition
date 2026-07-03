"""BioactivityState enum and Bioactivity dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.types import EntityID, JsonDict, RunID, RunType

from ._converters import _require_field
from ._extractors import (
    _build_content_hash,
    _extract_bioactivity_fields,
    _normalize_run_id,
    _normalize_source_batch_id,
)


class BioactivityState(StrEnum):
    """Processing state: RAW -> NORMALIZED -> VALIDATED."""

    RAW = "raw"
    NORMALIZED = "normalized"
    VALIDATED = "validated"

    def is_ready_for_silver(self) -> bool:
        """True if NORMALIZED or VALIDATED."""
        return self in (BioactivityState.NORMALIZED, BioactivityState.VALIDATED)

    def is_fully_validated(self) -> bool:
        """True if VALIDATED."""
        return self == BioactivityState.VALIDATED


@dataclass(frozen=True, kw_only=True)
class Bioactivity(BaseEntity):
    """Bioactivity measurement from ChEMBL. Required: activity_id, molecule_id."""

    _state: BioactivityState = BioactivityState.VALIDATED

    activity_id: str

    molecule_id: str
    target_id: str | None = None
    assay_id: str | None = None
    publication_id: str | None = None
    record_id: int | None = None
    src_id: int | None = None

    canonical_smiles: str | None = None
    molecule_pref_name: str | None = None
    parent_molecule_id: str | None = None

    target_pref_name: str | None = None
    target_organism: str | None = None
    target_taxonomy_id: int | None = None

    assay_type: str | None = None
    assay_description: str | None = None
    assay_variant_accession: str | None = None
    assay_variant_mutation: str | None = None

    bao_endpoint: str | None = None
    bao_endpoint_iri: str | None = None
    bao_endpoint_mapping_status: str | None = None
    bao_format: str | None = None
    bao_format_iri: str | None = None
    bao_format_mapping_status: str | None = None
    bao_label: str | None = None
    bao_ontology_version: str | None = None

    activity_type: str | None = None
    activity_value: float | None = None
    units: str | None = None
    activity_relation: str | None = None
    upper_value: float | None = None
    text_value: str | None = None

    standard_type: str | None = None
    standard_value: float | None = None
    standard_units: str | None = None
    standard_relation: str | None = None
    standard_upper_value: float | None = None
    standard_text_value: str | None = None
    standard_flag: int | None = None

    pchembl_value: float | None = None

    ligand_efficiency_bei: float | None = None
    ligand_efficiency_le: float | None = None
    ligand_efficiency_lle: float | None = None
    ligand_efficiency_sei: float | None = None

    qudt_units: str | None = None
    qudt_unit_iri: str | None = None
    qudt_unit_mapping_status: str | None = None
    qudt_ontology_version: str | None = None
    uo_units: str | None = None
    uo_unit_iri: str | None = None
    uo_unit_mapping_status: str | None = None
    uo_ontology_version: str | None = None

    journal: str | None = None
    publication_year: int | None = None
    publication_doi: str | None = None
    publication_pmid: str | None = None
    publication_pmc_id: str | None = None

    activity_comment: str | None = None
    data_validity_comment: str | None = None
    data_validity_description: str | None = None
    potential_duplicate: int | None = None
    manual_curation_flag: int | None = None
    original_activity_id: int | None = None

    action_type: str | None = None
    action_type_description: str | None = None
    action_type_parent_type: str | None = None

    activity_properties: str | None = None
    toid: int | None = None

    def _validate_invariants(self) -> None:
        """Validate business invariants."""
        if not self.activity_id:
            raise ValueError("Activity ID is required")
        if not self.molecule_id:
            raise ValueError("Molecule ID is required")
        self._validate_pchembl_value()

    def _validate_pchembl_value(self) -> None:
        """Validate pchembl_value is non-negative if present."""
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
        raw_data: JsonDict,
        run_id: RunID | UUID,
        run_type: RunType = RunType.INCREMENTAL,
        ingestion_ts: datetime,
        index: int = 0,
        source_batch_id: UUID | None = None,
    ) -> Bioactivity:
        """Create RAW bioactivity entity from source payload.

        Args:
            raw_data: Raw record dict from the ChEMBL bioactivity API.
            run_id: Pipeline run correlation ID (RunID or UUID).
            run_type: Type of pipeline run. Defaults to INCREMENTAL.
            ingestion_ts: Timestamp of data ingestion.
            index: Sequential record index within the pipeline run. Defaults to 0.
            source_batch_id: Optional Bronze batch UUID for lineage tracking.

        Returns:
            Bioactivity entity in RAW state.
        """
        activity_id = _require_field(raw_data, "activity_id")
        molecule_id = _require_field(raw_data, "molecule_id")
        base_fields = {
            "entity_id": EntityID(str(activity_id)),
            "content_hash": _build_content_hash(raw_data),
            "run_id": _normalize_run_id(run_id),
            "run_type": run_type,
            "ingestion_ts": ingestion_ts,
            "_index": index,
            "source_batch_id": _normalize_source_batch_id(source_batch_id),
            "_state": BioactivityState.RAW,
            "activity_id": str(activity_id),
            "molecule_id": str(molecule_id),
        }
        entity_fields = _extract_bioactivity_fields(raw_data)

        return cls(
            **base_fields,  # type: ignore[arg-type]
            **entity_fields,  # type: ignore[arg-type]
        )

    def with_state(self, new_state: BioactivityState) -> Bioactivity:
        """Create copy with new state (immutable pattern).

        Args:
            new_state: Target processing state to transition to.

        Returns:
            New Bioactivity instance with all fields copied and _state updated.
        """
        from dataclasses import asdict

        data = asdict(self)
        data["_state"] = new_state
        return Bioactivity(**data)
