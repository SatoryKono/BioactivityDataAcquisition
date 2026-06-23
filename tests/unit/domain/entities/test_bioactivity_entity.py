"""Unit tests for Bioactivity entity and BioactivityState enum."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.entities.bioactivity import Bioactivity, BioactivityState

BASE_KWARGS = {
    "entity_id": "activity:123",
    "content_hash": "sha256hash",
    "run_id": "run-001",
    "run_type": "incremental",
    "ingestion_ts": datetime(2024, 6, 1, tzinfo=UTC),
    "_index": 0,
}


@pytest.mark.unit
class TestBioactivityState:
    """Tests for BioactivityState enum."""

    def test_bioactivity_state__state_values__2e16fddb(self) -> None:
        assert BioactivityState.RAW == "raw"
        assert BioactivityState.NORMALIZED == "normalized"
        assert BioactivityState.VALIDATED == "validated"

    def test_bioactivity_state__is_ready_for_silver__1690c709(self) -> None:
        assert BioactivityState.RAW.is_ready_for_silver() is False
        assert BioactivityState.NORMALIZED.is_ready_for_silver() is True
        assert BioactivityState.VALIDATED.is_ready_for_silver() is True

    def test_bioactivity_state__is_fully_validated__ebd2a07a(self) -> None:
        assert BioactivityState.RAW.is_fully_validated() is False
        assert BioactivityState.NORMALIZED.is_fully_validated() is False
        assert BioactivityState.VALIDATED.is_fully_validated() is True


@pytest.mark.unit
class TestBioactivity:
    """Tests for Bioactivity domain entity."""

    def test_from_raw_content_hash_ignores_meta_and_runtime_fields(self) -> None:
        ingestion_ts = datetime(2024, 6, 1, tzinfo=UTC)
        base_raw = {
            "activity_id": "ACT_001",
            "molecule_id": "CHEMBL25",
            "standard_type": "IC50",
            "standard_value": 50.0,
        }
        runtime_augmented_raw = {
            **base_raw,
            "_run_id": "runtime-run-id",
            "_ingestion_ts": "2026-01-01T00:00:00Z",
            "_runtime_trace_id": "trace-1",
            "_dq_warn": True,
            "_dq_error": False,
        }

        base_entity = Bioactivity.from_raw(
            raw_data=base_raw,
            run_id="run-001",
            ingestion_ts=ingestion_ts,
        )
        runtime_augmented_entity = Bioactivity.from_raw(
            raw_data=runtime_augmented_raw,
            run_id="run-002",
            ingestion_ts=ingestion_ts,
        )

        assert base_entity.content_hash == runtime_augmented_entity.content_hash

    def test_from_raw_content_hash_changes_on_semantic_field_change(self) -> None:
        ingestion_ts = datetime(2024, 6, 1, tzinfo=UTC)
        base_raw = {
            "activity_id": "ACT_001",
            "molecule_id": "CHEMBL25",
            "standard_type": "IC50",
            "standard_value": 50.0,
        }
        changed_raw = {**base_raw, "standard_value": 75.0}

        base_entity = Bioactivity.from_raw(
            raw_data=base_raw,
            run_id="run-001",
            ingestion_ts=ingestion_ts,
        )
        changed_entity = Bioactivity.from_raw(
            raw_data=changed_raw,
            run_id="run-001",
            ingestion_ts=ingestion_ts,
        )

        assert base_entity.content_hash != changed_entity.content_hash

    def test_valid_creation_minimal(self) -> None:
        b = Bioactivity(
            **BASE_KWARGS,
            activity_id="ACT_001",
            molecule_id="CHEMBL25",
        )
        assert b.activity_id == "ACT_001"
        assert b.molecule_id == "CHEMBL25"
        assert b.target_id is None
        assert b.state == BioactivityState.VALIDATED

    def test_valid_creation_with_values(self) -> None:
        b = Bioactivity(
            **BASE_KWARGS,
            activity_id="ACT_002",
            molecule_id="CHEMBL25",
            target_id="CHEMBL204",
            assay_id="CHEMBL1000",
            standard_type="IC50",
            standard_value=50.0,
            standard_units="nM",
            pchembl_value=7.3,
        )
        assert b.standard_type == "IC50"
        assert b.pchembl_value == pytest.approx(7.3)

    def test_empty_activity_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Activity ID is required"):
            Bioactivity(**BASE_KWARGS, activity_id="", molecule_id="CHEMBL25")

    def test_empty_molecule_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Molecule ID is required"):
            Bioactivity(**BASE_KWARGS, activity_id="ACT_001", molecule_id="")

    def test_negative_pchembl_value_raises(self) -> None:
        with pytest.raises(ValueError, match="pChemBL value must be non-negative"):
            Bioactivity(
                **BASE_KWARGS,
                activity_id="ACT_001",
                molecule_id="CHEMBL25",
                pchembl_value=-1.0,
            )

    def test_zero_pchembl_value_valid(self) -> None:
        b = Bioactivity(
            **BASE_KWARGS,
            activity_id="ACT_001",
            molecule_id="CHEMBL25",
            pchembl_value=0.0,
        )
        assert b.pchembl_value == pytest.approx(0.0)

    def test_with_state_returns_new_instance(self) -> None:
        b = Bioactivity(
            **BASE_KWARGS,
            activity_id="ACT_001",
            molecule_id="CHEMBL25",
            _state=BioactivityState.RAW,
        )
        normalized = b.with_state(BioactivityState.NORMALIZED)
        assert b.state == BioactivityState.RAW
        assert normalized.state == BioactivityState.NORMALIZED
        assert normalized.activity_id == b.activity_id

    def test_entity_bioactivity__immutable__40c1e991(self) -> None:
        b = Bioactivity(
            **BASE_KWARGS,
            activity_id="ACT_001",
            molecule_id="CHEMBL25",
        )
        with pytest.raises((AttributeError, TypeError)):
            b.activity_id = "other"  # type: ignore[misc]

    def test_dq_flags_defaults(self) -> None:
        b = Bioactivity(
            **BASE_KWARGS,
            activity_id="ACT_001",
            molecule_id="CHEMBL25",
        )
        assert b._dq_warn is False
        assert b._dq_error is False

    def test_dq_flags_set(self) -> None:
        b = Bioactivity(
            **BASE_KWARGS,
            activity_id="ACT_001",
            molecule_id="CHEMBL25",
            _dq_warn=True,
            _dq_error=True,
        )
        assert b._dq_warn is True
        assert b._dq_error is True
