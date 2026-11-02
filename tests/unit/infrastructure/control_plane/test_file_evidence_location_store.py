# pyright: reportArgumentType=false
"""File evidence-location store: atomic publish, bounded lookup, fail-closed."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationConflictError,
    EvidenceLocationInvalidError,
    EvidenceLocationKind,
    EvidenceLocationLookupCode,
    EvidenceLocationRegisterOutcome,
    build_run_evidence_location,
)
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)

pytestmark = pytest.mark.unit

_SOURCE_A = "a" * 64
_SOURCE_B = "b" * 64
_RUN_A = "ac0b4e22-6a6e-5b7e-818e-106aeaf41390"
_RUN_B = "ffffffff-ffff-ffff-ffff-ffffffffffff"


def _location(**overrides: object):
    payload = {
        "kind": EvidenceLocationKind.PIPELINE,
        "owner": "chembl_assay",
        "run_id": _RUN_A,
        "workflow_run_id": "3dc8ffe4-305b-5d4b-a945-fe8e78f03828",
        "runtime_source_id": _SOURCE_A,
        "root_alias": DEFAULT_EVIDENCE_ROOT_ALIAS,
        "relative_data_root": "workflow-limit100-20261102T144403Z/chembl_assay",
    }
    payload.update(overrides)
    return build_run_evidence_location(**payload)  # type: ignore[arg-type]


def test_register_get_lookup_roundtrip(tmp_path: Path) -> None:
    store = FileEvidenceLocationStore(report_root=tmp_path / "run-reports")
    location = _location()
    decision = store.register(location)
    assert decision.outcome is EvidenceLocationRegisterOutcome.REGISTERED
    loaded = store.get(kind=location.kind, owner=location.owner, run_id=location.run_id)
    assert loaded == location
    found = store.lookup(
        kind=location.kind,
        owner=location.owner,
        run_id=location.run_id,
        expected_runtime_source_id=_SOURCE_A,
    )
    assert found.code is EvidenceLocationLookupCode.FOUND
    assert found.location == location


def test_identical_reregister_is_idempotent(tmp_path: Path) -> None:
    store = FileEvidenceLocationStore(report_root=tmp_path / "run-reports")
    first = store.register(_location())
    assert first.outcome is EvidenceLocationRegisterOutcome.REGISTERED
    again = store.register(_location())
    assert again.outcome is EvidenceLocationRegisterOutcome.ALREADY_IDENTICAL


def test_conflicting_register_refuses_overwrite(tmp_path: Path) -> None:
    store = FileEvidenceLocationStore(report_root=tmp_path / "run-reports")
    store.register(_location())
    with pytest.raises(EvidenceLocationConflictError):
        store.register(_location(relative_data_root="other-root/chembl_assay"))
    kept = store.get(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert kept is not None
    assert kept.relative_data_root.endswith("chembl_assay")
    assert kept.relative_data_root.startswith("workflow-limit100")


def test_lookup_codes_stay_distinct(tmp_path: Path) -> None:
    store = FileEvidenceLocationStore(report_root=tmp_path / "run-reports")
    missing = store.lookup(kind="pipeline", owner="chembl_assay", run_id="missing")
    assert missing.code is EvidenceLocationLookupCode.LOCATION_MISSING
    store.register(_location())
    conflict = store.lookup(
        kind="pipeline",
        owner="chembl_assay",
        run_id=_RUN_A,
        expected_runtime_source_id=_SOURCE_B,
    )
    assert conflict.code is EvidenceLocationLookupCode.IDENTITY_CONFLICT
    path = store._record_path(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    path.write_text("{not-json", encoding="utf-8")
    invalid = store.lookup(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert invalid.code is EvidenceLocationLookupCode.LOCATION_INVALID


def test_invalid_existing_does_not_fallback_to_foreign_run(tmp_path: Path) -> None:
    store = FileEvidenceLocationStore(report_root=tmp_path / "run-reports")
    foreign = _location(run_id=_RUN_B, relative_data_root="foreign/chembl_assay")
    store.register(foreign)
    target_path = store._record_path(
        kind="pipeline", owner="chembl_assay", run_id=_RUN_A
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("{broken", encoding="utf-8")
    with pytest.raises(EvidenceLocationConflictError, match="invalid"):
        store.register(_location())
    assert store.get(kind="pipeline", owner="chembl_assay", run_id=_RUN_B) == foreign


def test_competing_identical_registers_are_safe(tmp_path: Path) -> None:
    store = FileEvidenceLocationStore(report_root=tmp_path / "run-reports")
    location = _location()

    def _register() -> str:
        return store.register(location).outcome.value

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(lambda _: _register(), range(16)))
    assert set(outcomes) <= {
        EvidenceLocationRegisterOutcome.REGISTERED.value,
        EvidenceLocationRegisterOutcome.ALREADY_IDENTICAL.value,
    }
    assert outcomes.count(EvidenceLocationRegisterOutcome.REGISTERED.value) == 1
    assert store.get(kind="pipeline", owner="chembl_assay", run_id=_RUN_A) == location


def test_lookup_is_bounded_exact_path_not_rglob(tmp_path: Path) -> None:
    store = FileEvidenceLocationStore(report_root=tmp_path / "run-reports")
    store.register(_location())
    # Noise elsewhere must not be discovered by lookup for a missing key.
    decoy = (
        tmp_path
        / "run-reports"
        / "_evidence-locations"
        / "pipeline"
        / "other_pipeline"
        / "decoy.json"
    )
    decoy.parent.mkdir(parents=True)
    decoy.write_text(
        json.dumps(_location(owner="other_pipeline", run_id="decoy").to_dict()),
        encoding="utf-8",
    )
    missing = store.lookup(kind="pipeline", owner="chembl_assay", run_id="no-such-run")
    assert missing.code is EvidenceLocationLookupCode.LOCATION_MISSING
    assert missing.location is None


def test_catalog_symlink_escape_is_rejected_for_lookup_and_register(
    tmp_path: Path,
) -> None:
    report_root = tmp_path / "run-reports"
    report_root.mkdir()
    outside = tmp_path / "outside-catalog"
    outside.mkdir()
    catalog = report_root / "_evidence-locations"
    try:
        catalog.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    store = FileEvidenceLocationStore(report_root=report_root)
    # lookup classifies path-safety failures; register raises fail-closed.
    looked_up = store.lookup(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert looked_up.code is EvidenceLocationLookupCode.LOCATION_INVALID
    assert looked_up.detail is not None
    assert "symlink" in looked_up.detail or "escapes" in looked_up.detail
    with pytest.raises(EvidenceLocationInvalidError, match="symlink|escapes"):
        store.register(_location())
    assert list(outside.iterdir()) == []
