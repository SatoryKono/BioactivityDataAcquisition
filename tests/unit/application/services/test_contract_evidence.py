"""Unit tests for manifest contract-evidence derivation."""

from __future__ import annotations

from uuid import UUID

import pytest

from bioetl.application.services.control_plane.manifest.contract_evidence import (
    build_contract_evidence,
)
from bioetl.application.services.control_plane.manifest.models import (
    RunManifestCreateSpec,
)
from bioetl.domain.types import RunID, RunType

pytestmark = pytest.mark.unit


def _spec(**overrides: object) -> RunManifestCreateSpec:
    payload: dict[str, object] = {
        "run_id": RunID(UUID("11111111-1111-1111-1111-111111111111")),
        "run_type": RunType.INCREMENTAL,
        "pipeline_name": "chembl_activity",
        "provider": "chembl",
        "entity": "activity",
        "launch_context": {"resume": False},
        "runtime_config": {},
        "resolved_config": {},
        "contract_ref": "chembl.activity",
        "contract_schema_hash": "abc123",
    }
    payload.update(overrides)
    return RunManifestCreateSpec(**payload)  # type: ignore[arg-type]


def test_build_contract_evidence_compatible_when_ref_and_hash_present() -> None:
    evidence = build_contract_evidence(_spec())
    assert evidence["contract_comparison_status"] == "compatible"
    assert evidence["resume_contract"] == "resume_not_requested"
    assert evidence["lock_owner_id"] == "n/a"
    assert evidence["lock_owner_reason"] == "no_distributed_lock"


def test_build_contract_evidence_unknown_without_registry_anchors() -> None:
    evidence = build_contract_evidence(
        _spec(contract_ref=None, contract_schema_hash=None)
    )
    assert evidence["contract_comparison_status"] == "UNKNOWN"
    assert evidence["contract_comparison_reason"] == (
        "contract_ref_or_schema_hash_missing"
    )


def test_build_contract_evidence_records_resume_and_lock() -> None:
    evidence = build_contract_evidence(
        _spec(
            launch_context={"resume": True, "lock_owner_id": "owner-1"},
        )
    )
    assert evidence["resume_contract"] == "resume_requested"
    assert evidence["lock_owner_id"] == "owner-1"
    assert evidence["lock_owner_reason"] == "distributed_lock_recorded"


def test_build_runtime_contract_evidence_records_lock_owner() -> None:
    from bioetl.application.services.control_plane.manifest.contract_evidence import (
        CONTRACT_EVIDENCE_SCHEMA_VERSION,
        build_runtime_contract_evidence,
    )

    evidence = build_runtime_contract_evidence(
        manifest_id="manifest-1",
        contract_ref="chembl.activity",
        contract_schema_hash="abc123",
        resume_requested=False,
        lock_owner_id="run-owner",
    )
    assert evidence["schema_version"] == CONTRACT_EVIDENCE_SCHEMA_VERSION
    assert evidence["manifest_id"] == "manifest-1"
    assert evidence["lock_owner_id"] == "run-owner"
    assert evidence["lock_owner_reason"] == "distributed_lock_recorded"
    assert evidence["resume_contract"] == "resume_not_requested"

