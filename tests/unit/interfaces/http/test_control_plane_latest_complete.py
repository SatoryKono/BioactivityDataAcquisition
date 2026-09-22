"""Discovery never substitutes processing success for complete aggregate evidence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import UUID

import pytest

from bioetl.application.observability.control_plane_evidence import (
    ControlPlaneEvidenceService,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunID, RunType
from bioetl.interfaces.http import _control_plane_latest_complete as subject

pytestmark = pytest.mark.unit
NOW = datetime(2026, 9, 15, tzinfo=UTC)


def manifest(
    index: int, *, pipeline: str = "chembl_assay", workflow: str = "baseline"
) -> RunManifest:
    return RunManifest(
        manifest_id=f"manifest-{index}",
        execution_fingerprint=f"fp-{index}",
        schema_version="1.0",
        created_at=NOW + timedelta(minutes=index),
        run_id=RunID(UUID(int=index)),
        run_type=RunType.BACKFILL,
        pipeline_name=pipeline,
        provider="chembl",
        entity="assay",
        launch_context={"workflow_name": workflow},
    )


def discover(
    manifests: tuple[RunManifest, ...], service: Mock, *, scan_seconds: float = 9.0
) -> dict[str, object]:
    return subject.build_latest_complete_run_payload(
        manifests=manifests,
        workflow_manifests=(),
        service=service,
        pipeline="chembl_assay",
        run_type="backfill",
        workflows=("baseline",),
        selected_run_id="historical-run",
        now=NOW,
        scan_seconds=scan_seconds,
    )


@pytest.mark.parametrize("trust", ["ERROR", "INCOMPLETE", "UNKNOWN", "WARN"])
def test_skips_newer_success_without_aggregate_ok(trust: str) -> None:
    service = Mock(spec=ControlPlaneEvidenceService)
    service.trust_summary.side_effect = [
        {"processing_status": "success", "trust_status": trust},
        {"processing_status": "success", "trust_status": "OK"},
    ]
    older, newer = manifest(1), manifest(2)
    payload = discover((older, newer), service)
    assert payload["selected_run_id"] == "historical-run"
    assert payload["replay_authorized"] is False
    assert payload["rows"][0]["candidate_run_id"] == str(older.run_id)
    assert service.trust_summary.call_args_list[0].kwargs["scope"].manifest == newer


@pytest.mark.parametrize("processing", ["failed", "unknown", "shutdown"])
def test_complete_but_unsuccessful_run_is_not_a_candidate(processing: str) -> None:
    service = Mock(spec=ControlPlaneEvidenceService)
    service.trust_summary.return_value = {
        "trust_status": "OK",
        "processing_status": processing,
    }
    assert discover((manifest(1),), service)["rows"][0].get("candidate_run_id") is None


def test_scope_mismatch_does_not_fall_back_to_whole_catalog() -> None:
    service = Mock(spec=ControlPlaneEvidenceService)
    payload = discover(
        (manifest(1, pipeline="chembl_activity"), manifest(2, workflow="other")),
        service,
    )
    assert payload["candidate_count"] == 0
    assert payload["rows"][0]["reason"] == "no_complete_run_in_scope"
    service.trust_summary.assert_not_called()


def test_scan_cap_is_explicit_and_has_no_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "LATEST_COMPLETE_SCAN_LIMIT", 1)
    service = Mock(spec=ControlPlaneEvidenceService)
    service.trust_summary.return_value = {"trust_status": "UNKNOWN"}
    payload = discover((manifest(1), manifest(2)), service)
    assert payload["scanned"] == 1
    assert payload["rows"][0]["status"] == "INCOMPLETE"
    assert payload["rows"][0].get("candidate_run_id") is None


def test_time_budget_stops_before_another_file_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "monotonic", Mock(side_effect=[0.0, 10.0]))
    service = Mock(spec=ControlPlaneEvidenceService)
    payload = discover((manifest(1),), service)
    assert payload["rows"][0]["reason"] == "complete_run_scan_limit"
    service.trust_summary.assert_not_called()


def test_catalog_exhausted_budget_does_not_start_evidence_reads() -> None:
    service = Mock(spec=ControlPlaneEvidenceService)
    payload = discover((manifest(1),), service, scan_seconds=0.0)
    assert payload["rows"][0]["status"] == "INCOMPLETE"
    assert payload["rows"][0]["reason"] == "complete_run_scan_limit"
    assert payload["scanned"] == 0
    service.trust_summary.assert_not_called()


def test_read_failure_is_not_swallowed_as_no_complete_runs() -> None:
    service = Mock(spec=ControlPlaneEvidenceService)
    service.trust_summary.side_effect = OSError("unreadable")
    with pytest.raises(OSError, match="unreadable"):
        discover((manifest(1),), service)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("pipeline", "run_types"),
    [
        ("All", ("backfill",)),
        ("chembl_assay,chembl_activity", ("backfill",)),
        ("chembl_assay", ()),
        ("chembl_assay", ("backfill", "incremental")),
        ("chembl_assay", ("$__all",)),
    ],
)
async def test_discovery_rejects_broad_scope_before_catalog_reads(
    pipeline: str, run_types: tuple[str, ...]
) -> None:
    from bioetl.interfaces.http._health_server_control_plane_evidence_routing import (
        _latest_complete_payload,
    )

    host = Mock()
    host._read_required_param.return_value = pipeline
    host._read_scope_csv_param.return_value = run_types
    host._is_all_scope_token.side_effect = lambda value: value in {"All", "$__all"}
    with pytest.raises(ValueError, match="one pipeline and one run_type"):
        await _latest_complete_payload(host, {})
    host._run_manifest_port.list_all.assert_not_called()
