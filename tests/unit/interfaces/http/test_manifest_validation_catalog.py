"""Manifest-validation uses both catalogs before declaring a run missing."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from bioetl.interfaces.http import (
    _health_server_control_plane_evidence_scope as scope_module,
)

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
from bioetl.interfaces.http._health_server_control_plane_evidence_routing import (
    _service_payload,
    reconcile_manifest_validation_scope,
)
from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_validation_read_error_is_unknown_without_exposing_exception(monkeypatch):
    import json

    import bioetl.interfaces.http._health_server_control_plane_evidence_routing as routing

    service = ControlPlaneEvidenceService()

    async def resolved(*_args, **_kwargs):
        return _scope(resolved_via="selected_run_id_not_found"), None

    def fail(_self, **_kwargs):
        raise OSError("private filesystem diagnostic")

    monkeypatch.setattr(routing, "resolve_evidence_scope", resolved)
    monkeypatch.setattr(ControlPlaneEvidenceService, "trust_summary", fail)
    payload = await _service_payload(
        SimpleNamespace(_control_plane_evidence_service=service),
        {},
        endpoint="trust-summary",
    )
    assert payload["rows"][0]["status"] == "UNKNOWN"
    assert payload["rows"][0]["reason"] == "trust_evidence_read_error"
    assert "private filesystem diagnostic" not in json.dumps(payload)


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
        "bioetl.interfaces.http._health_server_control_plane_evidence_scope.verified_report_identity_for_run",
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
        "bioetl.interfaces.http._health_server_control_plane_evidence_scope.verified_report_identity_for_run",
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
        "bioetl.interfaces.http._health_server_control_plane_evidence_scope.verified_report_identity_for_run",
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


@pytest.mark.asyncio
async def test_corrupt_report_catalog_returns_evidence_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bioetl.interfaces.http._health_server_control_plane_evidence_routing as routing

    scope = _scope(resolved_via="selected_run_id_not_found")

    async def _resolved(*_args: object, **_kwargs: object) -> tuple[object, None]:
        return scope, None

    scheduled: list[str] = []

    async def _to_thread(fn, /, *args, **kwargs):  # type: ignore[no-untyped-def]
        scheduled.append(fn.__name__)
        return fn(*args, **kwargs)

    monkeypatch.setattr(routing, "resolve_evidence_scope", _resolved)
    monkeypatch.setattr(routing.asyncio, "to_thread", _to_thread)
    monkeypatch.setattr(
        scope_module,
        "verified_report_identity_for_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("Persisted selector report is unreadable")
        ),
    )
    payload = await _service_payload(
        SimpleNamespace(  # type: ignore[arg-type]
            _control_plane_evidence_service=object(),
            _run_report_store=object(),
        ),
        {},
        endpoint="manifest-validation",
    )
    assert scheduled == ["reconcile_manifest_validation_scope"]
    assert payload["endpoint"] == "manifest-validation"
    assert payload["status"] == "UNKNOWN"
    rows = payload["rows"]
    assert isinstance(rows, list)
    assert rows[0]["reason"] == "manifest_parse_error"
    assert rows[0]["check"] == "parse"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "resolver_error", [OSError("unavailable"), ValueError("invalid locator")]
)
async def test_report_only_run_keeps_manifest_missing_with_resolver(
    monkeypatch, resolver_error
):
    import bioetl.interfaces.http._health_server_control_plane_evidence_routing as routing
    from bioetl.application.services.evidence_location.resolver import (
        EvidenceLocationResolver,
    )

    async def resolved(*_args, **_kwargs):
        return _scope(resolved_via="selected_run_id_not_found"), None

    def fail_resolve(*_args, **_kwargs):
        raise resolver_error

    monkeypatch.setattr(EvidenceLocationResolver, "resolve", fail_resolve)

    monkeypatch.setattr(routing, "resolve_evidence_scope", resolved)
    monkeypatch.setattr(
        scope_module,
        "verified_report_identity_for_run",
        lambda *_args, **_kwargs: {
            "run_id": _RUN_ID,
            "pipeline_name": "chembl_activity",
        },
    )
    payload = await _service_payload(
        SimpleNamespace(
            _control_plane_evidence_service=ControlPlaneEvidenceService(),
            _run_report_store=object(),
            _evidence_location_resolver=EvidenceLocationResolver(
                locations=None, aliases=None, opener=None
            ),
        ),
        {},
        endpoint="manifest-validation",
    )
    assert payload["resolved_via"] == "resolved_without_manifest"
    assert payload["rows"][0]["reason"] == "manifest_not_recorded"
    assert payload["rows"][0]["status"] == "UNKNOWN"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "lookup_code, via, expected_check, expected_reason",
    [
        (
            "found",
            "selected_run_id_not_found",
            "scope_resolution",
            "selected_run_id_not_found",
        ),
        (
            "location_missing",
            "selected_run_id_not_found",
            "scope_resolution",
            "selected_run_id_not_found",
        ),
        (
            "identity_conflict",
            "selected_run_id_not_found",
            "parse",
            "manifest_parse_error",
        ),
        (
            "location_invalid",
            "selected_run_id_not_found",
            "parse",
            "manifest_parse_error",
        ),
        ("found", "selected_run_id", "parse", "manifest_parse_error"),
    ],
)
async def test_bound_missing_uuid_preserves_diagnostic_after_root_validation(
    monkeypatch, lookup_code, via, expected_check, expected_reason
):
    from dataclasses import replace
    from unittest.mock import Mock
    import bioetl.interfaces.http._health_server_control_plane_evidence_routing as routing
    from bioetl.application.services.evidence_location.resolver import (
        EvidenceLocationResolver,
    )

    selected = replace(
        _scope(resolved_via=via),
        requested_pipeline="chembl_activity",
        selected_pipelines=("chembl_activity",),
    )

    async def resolved(*_args, **_kwargs):
        return selected, None

    manifest_read = Mock(return_value=None)
    service_getter = Mock(
        side_effect=AssertionError("missing UUID must not bind evidence ports")
    )
    context = SimpleNamespace(
        get_manifest_by_run_id=manifest_read, get_validation_service=service_getter
    )
    location_reads = []

    def resolve_location(_self, **kwargs):
        location_reads.append(kwargs)
        return SimpleNamespace(code=SimpleNamespace(value=lookup_code), context=context)

    monkeypatch.setattr(routing, "resolve_evidence_scope", resolved)
    monkeypatch.setattr(
        scope_module, "verified_report_identity_for_run", lambda *_a, **_k: None
    )
    monkeypatch.setattr(EvidenceLocationResolver, "resolve", resolve_location)
    payload = await _service_payload(
        SimpleNamespace(
            _control_plane_evidence_service=ControlPlaneEvidenceService(),
            _run_report_store=object(),
            _runtime_source_id="selected-source",
            _evidence_location_resolver=EvidenceLocationResolver(None, None, None),
        ),
        {},
        endpoint="manifest-validation",
    )
    assert payload["rows"][0]["check"] == expected_check
    assert payload["rows"][0]["reason"] == expected_reason
    assert location_reads == [
        {
            "kind": "pipeline",
            "owner": "chembl_activity",
            "run_id": _RUN_ID,
            "expected_runtime_source_id": "selected-source",
        }
    ]
    service_getter.assert_not_called()
    if lookup_code in {"identity_conflict", "location_invalid"}:
        manifest_read.assert_not_called()
    else:
        manifest_read.assert_called_once_with(_RUN_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("pipeline", ["chembl_activity", "All"])
async def test_missing_uuid_keeps_scope_diagnostic_with_real_selected_file_context(
    monkeypatch, tmp_path, pipeline
):
    from dataclasses import replace
    import bioetl.interfaces.http._health_server_control_plane_evidence_routing as routing
    from bioetl.application.services.evidence_location.resolver import (
        EvidenceLocationResolver,
    )
    from bioetl.application.services.run_reports.evidence_location_paths import (
        default_evidence_root_alias_registry,
    )
    from bioetl.composition.control_plane_paths import FileEvidenceReadContextFactory
    from bioetl.infrastructure.control_plane.file_evidence_location_store import (
        FileEvidenceLocationStore,
    )

    selected = replace(
        _scope(resolved_via="selected_run_id_not_found"),
        requested_pipeline=pipeline,
        selected_pipelines=(pipeline,),
    )

    async def resolved(*_args, **_kwargs):
        return selected, None

    monkeypatch.setattr(routing, "resolve_evidence_scope", resolved)
    root = tmp_path / "selected"
    root.mkdir()
    resolver = EvidenceLocationResolver(
        locations=FileEvidenceLocationStore(report_root=tmp_path / "reports"),
        aliases=default_evidence_root_alias_registry(dashboard_data_root=root),
        opener=FileEvidenceReadContextFactory(),
    )
    payload = await _service_payload(
        SimpleNamespace(
            _control_plane_evidence_service=ControlPlaneEvidenceService(),
            _evidence_location_resolver=resolver,
            _run_report_store=None,
        ),
        {},
        endpoint="manifest-validation",
    )
    assert payload["rows"][0]["check"] == "scope_resolution"
    assert payload["rows"][0]["reason"] == "selected_run_id_not_found"
    assert not (tmp_path / "reports").exists()
    assert list(root.rglob("*")) == []
