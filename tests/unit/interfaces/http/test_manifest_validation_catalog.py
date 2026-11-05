"""Manifest-validation uses both catalogs before declaring a run missing."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.application.observability.control_plane_evidence.models import (
    unresolved_scope_check,
)
from bioetl.application.observability.control_plane_evidence.service import (
    ControlPlaneEvidenceService,
)
from bioetl.application.observability.control_plane_evidence.service_support import (
    EvidenceScopeContext,
)
from bioetl.domain.types import RunID
from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope
from bioetl.interfaces.http._health_server_control_plane_evidence_routing import (
    reconcile_manifest_validation_scope,
)

pytestmark = pytest.mark.unit

_RUN_ID = "ee3ce1ed-9487-572f-ae24-c98c6f6e3a37"


def _scope(*, resolved_via: str, manifest: object | None = None) -> _IdentityScope:
    return _IdentityScope(
        requested_pipeline=".*",
        selected_pipelines=(".*",),
        selected_run_types=(),
        selected_run_id=_RUN_ID,
        resolved_manifest=manifest,
        resolved_via=resolved_via,
    )


def test_report_catalog_run_without_manifest_is_not_a_missing_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def _identity(run_id: str, scopes: dict[str, tuple[str, ...]], **kwargs: object):
        seen["run_id"] = run_id
        seen["scopes"] = scopes
        seen["store"] = kwargs.get("store")
        return {"run_id": run_id, "pipeline_name": "uniprot_protein"}

    monkeypatch.setattr(
        "bioetl.interfaces.http._health_server_control_plane_evidence_routing.verified_report_identity_for_run",
        _identity,
    )
    store = SimpleNamespace()
    resolved = reconcile_manifest_validation_scope(
        _scope(resolved_via="selected_run_id_not_found"),
        report_store=store,  # type: ignore[arg-type]
    )

    assert resolved.resolved_via == "resolved_without_manifest"
    assert seen["run_id"] == _RUN_ID
    assert seen["scopes"] == {
        "workflow": (),
        "pipeline": (),
        "run_type": (),
        "run_status": (),
    }
    assert seen["store"] is store
    payload = ControlPlaneEvidenceService().manifest_validation(
        scope=EvidenceScopeContext(
            requested_pipeline=resolved.requested_pipeline,
            selected_run_id=resolved.selected_run_id,
            selected_run_types=resolved.selected_run_types,
            resolved_via=resolved.resolved_via,
            manifest=None,
        )
    )
    assert payload["resolved_via"] == "resolved_without_manifest"
    assert payload["rows"] == [
        {
            "check": "manifest_not_recorded",
            "status": "UNKNOWN",
            "reason": "manifest_not_recorded",
            "reason_display": "manifest_not_recorded",
            "detail": (
                "The run is in the report catalog, but its manifest was not recorded."
            ),
        }
    ]


def test_run_absent_from_both_catalogs_stays_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bioetl.interfaces.http._health_server_control_plane_evidence_routing.verified_report_identity_for_run",
        lambda *_args, **_kwargs: None,
    )
    resolved = reconcile_manifest_validation_scope(
        _scope(resolved_via="selected_run_id_not_found"),
        report_store=SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert resolved.resolved_via == "selected_run_id_not_found"
    check = unresolved_scope_check(resolved.resolved_via)
    assert check.reason == "selected_run_id_not_found"
    assert check.check == "scope_resolution"


def test_manifest_catalog_hit_does_not_consult_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("report catalog must not be read for a manifest hit")

    monkeypatch.setattr(
        "bioetl.interfaces.http._health_server_control_plane_evidence_routing.verified_report_identity_for_run",
        _forbidden,
    )
    manifest = SimpleNamespace(run_id=RunID(UUID(_RUN_ID)))
    resolved = reconcile_manifest_validation_scope(
        _scope(resolved_via="selected_run_id", manifest=manifest),
        report_store=SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert resolved.resolved_via == "selected_run_id"
    assert resolved.resolved_manifest is manifest


def test_missing_report_store_keeps_not_found() -> None:
    resolved = reconcile_manifest_validation_scope(
        _scope(resolved_via="selected_run_id_not_found"),
        report_store=None,
    )
    assert resolved.resolved_via == "selected_run_id_not_found"
