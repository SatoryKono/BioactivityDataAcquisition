"""Discovery avoids artifact reads for runs which cannot be successful candidates."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

FIXED_NOW = datetime(2026, 9, 23, tzinfo=UTC)

import pytest

from bioetl.application.observability.control_plane_evidence import (
    ControlPlaneEvidenceService,
    EvidenceScopeContext,
)
from tests.unit.application.services.run_manifest_test_support import make_run_manifest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("event", ["run_failed", "run_shutdown", "run_started", None])
def test_unsuccessful_discovery_candidate_does_not_read_artifacts(event, monkeypatch):
    manifest = make_run_manifest()
    ledger = Mock()
    ledger.list_entries.return_value = (
        (SimpleNamespace(event_type=event),) if event else ()
    )
    component = Mock(side_effect=AssertionError("unnecessary artifact read"))
    for name in ("manifest_validation", "lineage_validation", "retention_compliance"):
        monkeypatch.setattr(ControlPlaneEvidenceService, name, component)
    scope = EvidenceScopeContext(
        requested_pipeline=manifest.pipeline_name,
        selected_run_id=str(manifest.run_id),
        selected_run_types=(manifest.run_type.value,),
        resolved_via="selected_run_id",
        manifest=manifest,
    )
    service = ControlPlaneEvidenceService(ledger_port=ledger)
    assert service.successful_run_trust_summary(scope=scope, now=FIXED_NOW) is None
    ledger.list_entries.assert_called_once_with(manifest.manifest_id)
    component.assert_not_called()


def test_success_still_requires_all_components_and_one_ledger_read(monkeypatch):
    manifest = make_run_manifest()
    ledger = Mock()
    snapshot = (SimpleNamespace(event_type="run_finished"),)
    ledger.list_entries.return_value = snapshot
    components = []
    for name in ("manifest_validation", "lineage_validation", "retention_compliance"):
        component = Mock(
            return_value={
                "endpoint": name,
                "rows": [
                    {
                        "check": name,
                        "status": "UNKNOWN",
                        "reason": "missing",
                        "detail": "missing evidence",
                    }
                ],
            }
        )
        monkeypatch.setattr(ControlPlaneEvidenceService, name, component)
        components.append(component)
    scope = EvidenceScopeContext(
        requested_pipeline=manifest.pipeline_name,
        selected_run_id=str(manifest.run_id),
        selected_run_types=(manifest.run_type.value,),
        resolved_via="selected_run_id",
        manifest=manifest,
    )
    payload = ControlPlaneEvidenceService(
        ledger_port=ledger
    ).successful_run_trust_summary(scope=scope, now=FIXED_NOW)
    assert payload["processing_status"] == "success"
    assert payload["trust_status"] != "OK"
    ledger.list_entries.assert_called_once_with(manifest.manifest_id)
    for component in components:
        assert component.call_args.kwargs["ledger_snapshot"] is snapshot
