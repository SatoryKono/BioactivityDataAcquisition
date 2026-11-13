"""Exact-run accounting must follow the trusted detail locator, not global totals."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.application.services.evidence_location.resolver import (
    EvidenceLocationResolver,
)
from bioetl.application.services.evidence_location.resolver_types import (
    EvidenceLocationResolveResult,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.run_evidence_location import (
    EvidenceLocationLookupCode,
    EvidenceLocationLookupResult,
)
from bioetl.domain.types import RunID, RunType
from bioetl.interfaces.http import _health_server_records_table as subject

pytestmark = pytest.mark.unit
RUN = RunID(UUID("d890477d-0906-5e56-a673-a4de31b2110e"))


@pytest.mark.asyncio
async def test_missing_selected_manifest_never_reads_any_ledger(route):
    route[1]["manifest"] = None
    status, payload = await _call(route)
    assert status == 404 and payload["reason"] == "manifest_missing"
    assert route[1]["bound_reads"] == 0


@pytest.mark.parametrize("case", ["all_scope", "invalid_uuid", "missing_ports"])
def test_validation_binding_checks_selector_and_port_capabilities(route, case):
    from bioetl.application.observability.control_plane_evidence import (
        ControlPlaneEvidenceService,
    )
    from bioetl.interfaces.http._health_server_control_plane_evidence_routing import (
        _bind_selected_validation,
    )
    from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope

    host, seen = route
    service = ControlPlaneEvidenceService()
    seen["context"] = SimpleNamespace(
        get_manifest_by_run_id=lambda _: seen["manifest"],
        get_validation_service=lambda: None if case == "missing_ports" else service,
    )
    scope = _IdentityScope(
        ".*" if case == "all_scope" else "chembl_activity",
        (),
        ("backfill",),
        "not-a-uuid" if case == "invalid_uuid" else str(RUN),
        seen["manifest"],
        "selected_run_id",
    )
    if case == "all_scope":
        resolved, bound = _bind_selected_validation(host, scope, service)
        assert resolved.resolved_manifest is seen["manifest"]
        assert bound is service
        assert seen["resolve_args"]["owner"] == "chembl_activity"
    else:
        reason = (
            "identity does not match"
            if case == "invalid_uuid"
            else "ports are unavailable"
        )
        with pytest.raises(ValueError, match=reason):
            _bind_selected_validation(host, scope, service)
    assert seen["global_reads"] == seen["bound_reads"] == 0


def test_selected_ledger_chain_preserves_run_and_after_cursor(tmp_path):
    from bioetl.composition.control_plane_paths import _SelectedRootLedgerPort

    base = tmp_path / "output/control/run_ledger/_predecessors"
    base.mkdir(parents=True)
    (base / "current.txt").write_text("previous", encoding="utf-8")
    (base / "previous.txt").write_text("current", encoding="utf-8")
    entry = _entry()
    seen = []
    entries = [entry]

    def by_run(run_id):
        seen.append(("run", run_id))
        return (entry,)

    def after(manifest_id, cursor):
        seen.append(("after", manifest_id, cursor))
        return [entry]

    context = SimpleNamespace(
        data_root=tmp_path,
        ledger_port=SimpleNamespace(
            list_entries=lambda _: entries,
            list_entries_after=after,
        ),
        get_ledger_entries_by_run_id=by_run,
    )
    port = _SelectedRootLedgerPort(context)
    assert port.list_entries("current") == [entry]
    assert seen == [("run", RUN)]
    assert port.list_entries_after("current", "last-entry") == [entry]
    assert seen[-1] == ("after", "current", "last-entry")
    entries.clear()
    assert port.list_entries("empty") == []
    assert len(seen) == 2


def test_read_context_accepts_manifest_port_without_raw_inspection(
    tmp_path, monkeypatch
):
    from bioetl.composition import control_plane_paths as paths

    monkeypatch.setattr(paths, "FileRunManifestStore", lambda **_: SimpleNamespace())
    context = paths.FileEvidenceReadContextFactory().open(
        tmp_path / "selected", trusted_alias_base=tmp_path
    )
    service = context.get_validation_service()
    assert service is not None
    assert service.manifest_inspector is None


def test_retention_uses_selected_config_and_terminal_ledger(route, tmp_path):
    """A live catalog manifest must not redirect isolated validation to global files."""
    import json
    from dataclasses import replace

    from bioetl.application.observability.control_plane_evidence import (
        ControlPlaneEvidenceService,
    )
    from bioetl.composition.control_plane_paths import FileEvidenceReadContextFactory
    from bioetl.domain.control_plane import RunCodeProvenance
    from bioetl.interfaces.http._health_server_control_plane_evidence_routing import (
        _bind_selected_validation,
    )
    from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope
    from bioetl.interfaces.http._health_server_control_plane_evidence_scope import (
        to_evidence_scope,
    )

    host, seen = route
    root = tmp_path / "isolated"
    control = root / "output/control"
    config = control / "effective_config/saved-config.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"artifact_id": "saved-config"}))
    manifest = replace(
        seen["manifest"],
        code_provenance=RunCodeProvenance(effective_config_artifact_id="saved-config"),
        launch_context={"required_persistence_profile": "replay_ready"},
    )
    # Use the actual file factory, then pass it through the actual route binder.
    context = FileEvidenceReadContextFactory().open(root, trusted_alias_base=tmp_path)
    context.manifest_port.save(manifest)
    context.ledger_port.append(_entry())
    seen["context"] = context
    scope = _IdentityScope(
        requested_pipeline="chembl_activity",
        selected_pipelines=("chembl_activity",),
        selected_run_types=("backfill",),
        selected_run_id=str(RUN),
        resolved_manifest=seen["manifest"],
        resolved_via="selected_run_id",
    )
    resolved, service = _bind_selected_validation(
        host, scope, ControlPlaneEvidenceService()
    )
    result = service.retention_compliance(
        scope=to_evidence_scope(resolved),
        now=datetime(2026, 11, 12, tzinfo=UTC),
    )
    required = next(r for r in result["rows"] if r["check"] == "required_evidence")
    assert required["status"] == "OK"
    assert result["processing_status"] == "success"
    assert any(a["surface"] == "effective_config" for a in result["artifacts"])


@pytest.mark.parametrize(
    "code",
    [
        EvidenceLocationLookupCode.IDENTITY_CONFLICT,
        EvidenceLocationLookupCode.LOCATION_INVALID,
        EvidenceLocationLookupCode.FOUND,
    ],
)
def test_validation_refuses_foreign_or_unbound_sources(route, code):
    from bioetl.application.observability.control_plane_evidence import (
        ControlPlaneEvidenceService,
    )
    from bioetl.interfaces.http._health_server_control_plane_evidence_routing import (
        _bind_selected_validation,
    )
    from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope

    host, seen = route
    seen["code"] = code
    scope = _IdentityScope(
        "chembl_activity",
        ("chembl_activity",),
        ("backfill",),
        str(RUN),
        seen["manifest"],
        "selected_run_id",
    )
    with pytest.raises(ValueError, match="unavailable"):
        _bind_selected_validation(host, scope, ControlPlaneEvidenceService())


def _entry(run_id=RUN):
    return RunLedgerEntry(
        entry_id="terminal",
        manifest_id="manifest",
        run_id=run_id,
        event_type="run_finished",
        occurred_at=datetime(2026, 11, 12, tzinfo=UTC),
        status="success",
        metrics_snapshot={
            "records_bronze": 1000,
            "records_silver": 924,
            "records_gold": 910,
        },
    )


@pytest.fixture
def route(monkeypatch):
    seen = {"global_reads": 0, "bound_reads": 0, "responses": []}

    def global_read(_run_id):
        seen["global_reads"] += 1
        raise AssertionError("a resolved run must never use the global ledger")

    def bound_read(_run_id):
        seen["bound_reads"] += 1
        return seen["entries"]

    seen["entries"] = (_entry(),)
    seen["manifest"] = RunManifest(
        manifest_id="manifest",
        run_id=RUN,
        pipeline_name="chembl_activity",
        run_type=RunType.BACKFILL,
    )
    context = SimpleNamespace(
        data_root=Path("bound"),
        get_manifest_by_run_id=lambda _: seen["manifest"],
        get_ledger_entries_by_run_id=bound_read,
    )
    seen["code"] = EvidenceLocationLookupCode.FOUND

    def resolve(_self, **kwargs):
        seen["resolve_args"] = kwargs
        return EvidenceLocationResolveResult(
            lookup=EvidenceLocationLookupResult(code=seen["code"]),
            context=seen.get("context", context)
            if seen["code"] is EvidenceLocationLookupCode.FOUND
            else None,
            data_root=Path("bound"),
        )

    monkeypatch.setattr(EvidenceLocationResolver, "resolve", resolve)
    monkeypatch.setattr(subject, "load_pipeline_run_report_payload", lambda **_: None)

    async def send(_writer, status, payload):
        seen["responses"].append((status, payload))

    host = SimpleNamespace(
        _evidence_location_resolver=EvidenceLocationResolver(
            locations=None, aliases=None, opener=None
        ),
        _runtime_source_id="a" * 64,
        _run_ledger_port=SimpleNamespace(list_entries_by_run_id=global_read),
        _forensic_endpoint_limiter=asyncio.Semaphore(1),
        _read_required_param=lambda query, name: query[name],
        _read_optional_param=lambda query, name: query.get(name),
        _send_payload_response=send,
    )
    return host, seen


async def _call(route):
    host, seen = route
    await subject.handle_processed_records_table(
        host,
        None,
        {"pipeline": "chembl_activity", "run_id": str(RUN), "run_type": "backfill"},
    )
    assert seen["global_reads"] == 0
    return seen["responses"][-1]


@pytest.mark.asyncio
async def test_accounting_comes_from_the_resolved_run_and_checks_runtime_identity(
    route,
):
    status, payload = await _call(route)
    assert status == 200
    values = {row["parameter"]: row["value"] for row in payload["rows"]}
    assert int("".join(values["01 bronze_records"].split())) == 1000
    assert int("".join(values["02 silver_valid_records"].split())) == 924
    assert int("".join(values["07 gold_written_records"].split())) == 910
    assert route[1]["resolve_args"]["expected_runtime_source_id"] == "a" * 64


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code",
    [
        EvidenceLocationLookupCode.IDENTITY_CONFLICT,
        EvidenceLocationLookupCode.LOCATION_INVALID,
    ],
)
async def test_locator_refusal_cannot_fall_back_to_global_evidence(route, code):
    route[1]["code"] = code
    status, payload = await _call(route)
    assert status == 409 and payload["reason"] == code.value
    assert route[1]["bound_reads"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["pipeline", "run_type", "run_id"])
async def test_manifest_must_match_requested_scope_before_any_ledger_read(
    route, change
):
    changes = {
        "pipeline": {"pipeline_name": "other_pipeline"},
        "run_type": {"run_type": RunType.INCREMENTAL},
        "run_id": {"run_id": RunID(UUID(int=2))},
    }[change]
    route[1]["manifest"] = RunManifest(
        manifest_id="manifest",
        run_id=changes.get("run_id", RUN),
        pipeline_name=changes.get("pipeline_name", "chembl_activity"),
        run_type=changes.get("run_type", RunType.BACKFILL),
    )
    status, payload = await _call(route)
    assert status == 409 and payload["reason"] == "selector_context_mismatch"
    assert route[1]["bound_reads"] == 0


@pytest.mark.asyncio
async def test_missing_resolved_ledger_stays_unknown_instead_of_using_other_roots(
    route,
):
    route[1]["entries"] = ()
    status, payload = await _call(route)
    assert status == 200 and payload["contract"] == "processed_records_table_v2"
    assert all(row["value"] == "UNKNOWN" for row in payload["rows"])


@pytest.mark.asyncio
async def test_foreign_ledger_identity_is_rejected(route):
    route[1]["entries"] = (_entry(RunID(UUID(int=2))),)
    status, payload = await _call(route)
    assert status == 409 and payload["reason"] == "ledger_identity_conflict"


def test_validation_rejects_a_foreign_pipeline_before_resolving(route):
    from bioetl.application.observability.control_plane_evidence import (
        ControlPlaneEvidenceService,
    )
    from bioetl.interfaces.http._health_server_control_plane_evidence_routing import (
        _bind_selected_validation,
    )
    from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope

    host, seen = route
    scope = _IdentityScope(
        "uniprot_protein",
        ("uniprot_protein",),
        (),
        str(RUN),
        seen["manifest"],
        "selected_run_id",
    )
    with pytest.raises(ValueError, match="identity does not match"):
        _bind_selected_validation(host, scope, ControlPlaneEvidenceService())
    assert "resolve_args" not in seen


def test_validation_accepts_equivalent_uppercase_uuid(route):
    from bioetl.application.observability.control_plane_evidence import (
        ControlPlaneEvidenceService,
    )
    from bioetl.interfaces.http._health_server_control_plane_evidence_routing import (
        _bind_selected_validation,
    )
    from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope

    host, seen = route
    service = ControlPlaneEvidenceService()
    seen["context"] = SimpleNamespace(
        get_manifest_by_run_id=lambda _: seen["manifest"],
        get_validation_service=lambda: service,
    )
    scope = _IdentityScope(
        "chembl_activity",
        ("chembl_activity",),
        ("backfill",),
        str(RUN).upper(),
        seen["manifest"],
        "selected_run_id",
    )
    resolved, bound = _bind_selected_validation(
        host, scope, ControlPlaneEvidenceService()
    )
    assert resolved.resolved_manifest is seen["manifest"]
    assert bound is service


def test_selected_validation_ledger_refuses_outside_file(tmp_path, monkeypatch):
    from bioetl.composition.control_plane_paths import (
        FileEvidenceReadContextFactory,
        _SelectedRootLedgerPort,
    )
    from bioetl.domain.control_plane.run_evidence_location import (
        EvidenceLocationInvalidError,
    )

    root = tmp_path / "selected"
    context = FileEvidenceReadContextFactory().open(root, trusted_alias_base=tmp_path)
    foreign = tmp_path / "foreign.jsonl"
    foreign.write_text("must not be read", encoding="utf-8")
    original = Path.read_text
    reads = []

    def read_text(path, *args, **kwargs):
        reads.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    with pytest.raises(EvidenceLocationInvalidError):
        _SelectedRootLedgerPort(context).list_entries("../../../../foreign")
    assert foreign not in reads


@pytest.mark.parametrize("has_manifest", [True, False])
def test_report_catalog_run_checks_selected_root_for_manifest(route, has_manifest):
    from bioetl.application.observability.control_plane_evidence import (
        ControlPlaneEvidenceService,
    )
    from bioetl.interfaces.http._health_server_control_plane_evidence_scope import (
        _bind_selected_validation,
        to_evidence_scope,
    )
    from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope

    host, seen = route
    original = ControlPlaneEvidenceService()
    selected = ControlPlaneEvidenceService()
    manifest = seen["manifest"] if has_manifest else None
    seen["context"] = SimpleNamespace(
        get_manifest_by_run_id=lambda _: manifest,
        get_validation_service=lambda: selected,
    )
    scope = _IdentityScope(
        "chembl_activity",
        ("chembl_activity",),
        ("backfill",),
        str(RUN),
        None,
        "resolved_without_manifest",
    )
    resolved, bound = _bind_selected_validation(host, scope, original)
    assert resolved.resolved_manifest is manifest
    assert bound is (selected if has_manifest else original)
    result = bound.manifest_validation(scope=to_evidence_scope(resolved))
    reasons = {row["reason"] for row in result["rows"]}
    assert ("manifest_not_recorded" in reasons) is not has_manifest
    assert seen["resolve_args"]["run_id"] == str(RUN)
    if has_manifest:
        assert any(
            row["check"] == "schema_version" and row["status"] == "OK"
            for row in result["rows"]
        )
