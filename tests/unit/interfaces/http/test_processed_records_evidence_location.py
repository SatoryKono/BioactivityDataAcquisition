"""Exact-run accounting must follow the trusted detail locator, not global totals."""

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
