"""LF-06: UUID catalog resolution without guessing, and not-found presentation."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.domain.control_plane.run_manifest import RunManifest
from bioetl.domain.types import RunID
from bioetl.interfaces.http._run_id_resolver import resolve_unique_scope
from bioetl.interfaces.http._selected_run_live import active_run_diagnostics

pytestmark = pytest.mark.unit

_STAMP = "20261102T181217"
_RUN_ID = "ee3ce1ed-9487-572f-ae24-c98c6f6e3a37"
_OTHER = "d7cdb35b-e37a-5767-b30e-aa8dfb60d775"


def _manifest(
    run_id: str,
    *,
    pipeline: str = "uniprot_protein",
    workflow: str = "uniprot_support_pack",
    run_type: str = "backfill",
) -> SimpleNamespace:
    return SimpleNamespace(
        run_id=RunID(UUID(run_id)),
        pipeline_name=pipeline,
        workflow_name=workflow,
        run_type=SimpleNamespace(value=run_type),
    )


def test_unique_scope_refuses_an_ambiguous_catalog() -> None:
    resolution = resolve_unique_scope(
        (_manifest(_RUN_ID), _manifest(_OTHER, pipeline="uniprot_idmapping")),
        pipelines=(".*",),
        run_types=("backfill",),
        workflows=("uniprot_support_pack",),
    )
    assert resolution.status == "ambiguous"
    assert resolution.run_id is None
    assert resolution.reason == "ambiguous_scope"


def test_nested_workflow_declaration_does_not_drop_the_second_run() -> None:
    top_level = RunManifest(
        run_id=RunID(UUID(_RUN_ID)),
        pipeline_name="uniprot_protein",
        workflow_name="wf",
    )
    launch_context = RunManifest(
        run_id=RunID(UUID(_OTHER)),
        pipeline_name="uniprot_protein",
        launch_context={"workflow_name": "wf"},
    )

    resolution = resolve_unique_scope(
        (top_level, launch_context),
        pipelines=("uniprot_protein",),
        workflows=("wf",),
    )

    assert resolution.status == "ambiguous"
    assert resolution.run_id is None
    assert resolution.reason == "ambiguous_scope"


def test_runtime_and_resolved_workflow_keys_are_both_matches() -> None:
    runtime = RunManifest(
        run_id=RunID(UUID(_RUN_ID)),
        pipeline_name="uniprot_protein",
        runtime_config={"workflow": "wf"},
    )
    resolved = RunManifest(
        run_id=RunID(UUID(_OTHER)),
        pipeline_name="uniprot_protein",
        resolved_config={"workflow": "wf"},
    )

    resolution = resolve_unique_scope(
        (runtime, resolved),
        pipelines=("uniprot_protein",),
        workflows=("wf",),
    )

    assert resolution.status == "ambiguous"
    assert resolution.run_id is None
    assert resolution.reason == "ambiguous_scope"


def test_unique_scope_returns_the_successor_manifest() -> None:
    run_id = RunID(UUID(_RUN_ID))
    predecessor = RunManifest(
        manifest_id="pred",
        run_id=run_id,
        pipeline_name="uniprot_protein",
        workflow_name="wf",
        execution_fingerprint="stale-fingerprint",
    )
    successor = RunManifest(
        manifest_id="succ",
        predecessor_manifest_id="pred",
        run_id=run_id,
        pipeline_name="uniprot_protein",
        workflow_name="wf",
        execution_fingerprint="current-fingerprint",
    )

    resolution = resolve_unique_scope(
        (predecessor, successor),
        pipelines=("uniprot_protein",),
        workflows=("wf",),
    )

    assert resolution.status == "resolved"
    assert resolution.run_id == _RUN_ID
    assert resolution.manifest is successor


def test_two_current_manifests_for_one_run_are_not_chosen() -> None:
    run_id = RunID(UUID(_RUN_ID))
    first = RunManifest(
        manifest_id="one",
        run_id=run_id,
        pipeline_name="uniprot_protein",
        workflow_name="wf",
        execution_fingerprint="one",
    )
    second = RunManifest(
        manifest_id="two",
        run_id=run_id,
        pipeline_name="uniprot_protein",
        workflow_name="wf",
        execution_fingerprint="two",
    )

    resolution = resolve_unique_scope((first, second), workflows=("wf",))

    assert resolution.status == "ambiguous"
    assert resolution.run_id is None
    assert resolution.manifest is None


def test_compact_stamp_is_not_a_catalog_uuid() -> None:
    resolution = resolve_unique_scope(
        (_manifest(_RUN_ID),),
        pipelines=("uniprot_protein",),
    )
    assert resolution.status == "resolved"
    assert resolution.run_id == _RUN_ID
    assert resolution.reason == "unique_scope"


def test_non_uuid_token_does_not_raise_into_live_diagnostics() -> None:
    host = MagicMock()
    host._run_manifest_port = MagicMock()
    host._run_ledger_port = None

    assert active_run_diagnostics(host, "uniprot_protein", _STAMP) is None
    host._run_manifest_port.get_by_run_id.assert_not_called()


def test_stamp_not_found_payload_is_not_query_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.interfaces.http import selected_run_status as selected
    from bioetl.interfaces.http._selected_run_unavailable import unavailable_status

    host = MagicMock()
    host._run_manifest_port = MagicMock()
    host._run_ledger_port = None
    host._evidence_location_resolver = None
    host._runtime_source_id = None

    def _missing(**kwargs: object) -> dict[str, object]:
        return unavailable_status(
            str(kwargs["pipeline"]),
            str(kwargs["run_id"]),
            "UNKNOWN",
            "run_not_found",
        )

    monkeypatch.setattr(selected, "load_selected_run_status", _missing)
    payload = selected._load_selected_with_live_fallback(
        host,
        pipeline="uniprot_protein",
        run_id=_STAMP,
        query={"pipeline": "uniprot_protein", "run_type": "backfill"},
        skip_scope_check=True,
    )

    assert payload["reason"] == "run_not_found"
    assert payload["verdict"] == "UNKNOWN"
    assert payload["verdict"] != "QUERY ERROR"
    domains = payload["domains"]
    assert isinstance(domains, list)
    assert domains
    assert all(row["verdict"] != "QUERY ERROR" for row in domains)
    assert all(row["reason"] == "run_not_found" for row in domains)
    assert all(row["reason_display"] == "Run not found" for row in domains)
