"""Socket-free behavior tests for control-plane selector record helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from bioetl.domain.control_plane import (
    RunLedgerEntry,
    RunManifest,
    WorkflowManifest,
    WorkflowManifestStep,
)
from bioetl.domain.control_plane.run_ledger import (
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_SHUTDOWN_EVENT,
    RUN_STARTED_EVENT,
)
from bioetl.domain.types import RunID, RunType
from bioetl.interfaces.http import _control_plane_selector_records as subject
from bioetl.interfaces.http import control_plane_selector_context as selector_context

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 8, 10, 8, 30, tzinfo=UTC)


def _run_id(index: int) -> RunID:
    return RunID(UUID(int=index))


def _manifest(
    index: int,
    *,
    pipeline: str = "chembl_activity",
    run_type: RunType = RunType.INCREMENTAL,
    launch_context: dict[str, object] | None = None,
    runtime_config: dict[str, object] | None = None,
    resolved_config: dict[str, object] | None = None,
) -> RunManifest:
    provider, entity = pipeline.split("_", 1)
    return RunManifest(
        manifest_id=f"manifest-{index}",
        execution_fingerprint=f"fingerprint-{index}",
        schema_version="1.0",
        created_at=_NOW + timedelta(minutes=index),
        run_id=_run_id(index),
        run_type=run_type,
        pipeline_name=pipeline,
        provider=provider,
        entity=entity,
        launch_context=launch_context or {},
        runtime_config=runtime_config or {},
        resolved_config=resolved_config or {},
    )


def _entry(
    manifest: RunManifest,
    entry_id: str,
    event_type: str,
    *,
    offset: int,
    status: str | None = None,
) -> RunLedgerEntry:
    return RunLedgerEntry(
        entry_id=entry_id,
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        event_type=event_type,
        occurred_at=manifest.created_at + timedelta(minutes=offset),
        status=status,
    )


class _Ledger:
    def __init__(self, entries: dict[RunID, list[RunLedgerEntry]]) -> None:
        self._entries = entries
        self.lookups: list[RunID] = []

    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]:
        self.lookups.append(run_id)
        return list(self._entries.get(run_id, ()))


@pytest.mark.parametrize("token", ("All", "ALL", "all", " $__all ", "__all", "*"))
def test_selected_pipeline_scope_treats_grafana_all_tokens_as_unfiltered(
    token: str,
) -> None:
    assert subject.selected_pipeline_scope((), token) == ()


def test_all_scope_classifier_rejects_absent_blank_and_normal_values() -> None:
    assert subject._is_all_scope_token(None) is False
    assert subject._is_all_scope_token("   ") is False
    assert subject._is_all_scope_token("chembl_activity") is False


def test_selected_pipeline_scope_preserves_explicit_and_non_token_scopes() -> None:
    assert subject.selected_pipeline_scope(("chembl_activity",), "ignored") == (
        "chembl_activity",
    )
    assert subject.selected_pipeline_scope((), None) == ()
    assert subject.selected_pipeline_scope((), "   ") == ("   ",)
    assert subject.selected_pipeline_scope((), "pubchem_compound") == (
        "pubchem_compound",
    )


def test_narrow_manifest_catalog_applies_each_scope_and_fail_open_policy() -> None:
    chembl = _manifest(1, launch_context={"workflow": "daily-load"})
    pubchem = _manifest(
        2,
        pipeline="pubchem_compound",
        run_type=RunType.BACKFILL,
    )
    manifests = (chembl, pubchem)
    aliases: subject.WorkflowAliasMap = {
        ("pubchem_compound", "backfill"): ("warehouse-load",)
    }

    # An exact run selection intentionally wins over the other selector dimensions.
    assert subject.narrow_manifest_catalog(
        manifests,
        selected_workflows=("missing",),
        selected_pipelines=("missing",),
        selected_run_types=("missing",),
        selected_run_id=str(pubchem.run_id),
        workflow_aliases=aliases,
    ) == (pubchem,)
    assert subject.narrow_manifest_catalog(
        manifests,
        selected_workflows=(),
        selected_pipelines=("chembl_activity",),
        selected_run_types=(),
        selected_run_id=None,
    ) == (chembl,)
    assert subject.narrow_manifest_catalog(
        manifests,
        selected_workflows=(),
        selected_pipelines=(),
        selected_run_types=("backfill",),
        selected_run_id=None,
    ) == (pubchem,)
    assert subject.narrow_manifest_catalog(
        manifests,
        selected_workflows=("warehouse-load",),
        selected_pipelines=(),
        selected_run_types=(),
        selected_run_id=None,
        workflow_aliases=aliases,
    ) == (pubchem,)
    assert (
        subject.narrow_manifest_catalog(
            manifests,
            selected_workflows=("ALL",),
            selected_pipelines=("$__all",),
            selected_run_types=("*",),
            selected_run_id=None,
        )
        == manifests
    )

    assert (
        subject.narrow_manifest_catalog(
            manifests,
            selected_workflows=("missing",),
            selected_pipelines=(),
            selected_run_types=(),
            selected_run_id=None,
        )
        == manifests
    )
    assert (
        subject.narrow_manifest_catalog(
            manifests,
            selected_workflows=("missing",),
            selected_pipelines=(),
            selected_run_types=(),
            selected_run_id=None,
            fail_open_when_empty=False,
        )
        == ()
    )


def test_build_workflow_aliases_honors_selection_defaults_and_deduplication() -> None:
    selected = WorkflowManifest(
        manifest_id="workflow-manifest-selected",
        workflow_run_id=_run_id(20),
        execution_fingerprint="workflow-fingerprint-selected",
        schema_version="1.0",
        created_at=_NOW,
        workflow_name="curated-load",
        workflow_version="1",
        launch_context={},
        defaults={"run_type": " backfill "},
        selected_step_ids=("explicit", "blank", "duplicate"),
        steps=(
            WorkflowManifestStep(
                step_id="ignored",
                kind="pipeline",
                pipeline_name="ignored_pipeline",
            ),
            WorkflowManifestStep(
                step_id="explicit",
                kind="pipeline",
                pipeline_name=" chembl_activity ",
                run_options={"run_type": " incremental "},
            ),
            WorkflowManifestStep(
                step_id="blank",
                kind="pipeline",
                pipeline_name="   ",
            ),
            WorkflowManifestStep(
                step_id="duplicate",
                kind="pipeline",
                pipeline_name="chembl_activity",
                run_options={"run_type": "incremental"},
            ),
        ),
    )
    all_steps = WorkflowManifest(
        manifest_id="workflow-manifest-all",
        workflow_run_id=_run_id(21),
        execution_fingerprint="workflow-fingerprint-all",
        schema_version="1.0",
        created_at=_NOW,
        workflow_name="raw-load",
        workflow_version="1",
        launch_context={},
        defaults={"run_type": "backfill"},
        selected_step_ids=(),
        steps=(
            WorkflowManifestStep(
                step_id="defaulted",
                kind="pipeline",
                pipeline_name="pubchem_compound",
                run_options=None,
            ),
            WorkflowManifestStep(
                step_id="no-run-type",
                kind="pipeline",
                pipeline_name="chembl_assay",
                run_options={"run_type": " "},
            ),
            WorkflowManifestStep(
                step_id="no-pipeline",
                kind="transform",
                pipeline_name=None,
            ),
        ),
    )

    assert subject.build_workflow_aliases((selected, all_steps)) == {
        ("chembl_activity", "incremental"): ("curated-load",),
        ("pubchem_compound", "backfill"): ("raw-load",),
        ("chembl_assay", "backfill"): ("raw-load",),
    }
    assert subject.build_workflow_aliases(()) == {}


def test_build_selector_records_uses_ledger_order_and_candidate_precedence() -> None:
    manifest = _manifest(
        3,
        launch_context={"workflow_name": None, "workflow": " primary "},
        runtime_config={"workflow_name": "primary", "workflow": " "},
        resolved_config={"workflow_name": 7, "workflow": "resolved"},
    )
    entries = [
        _entry(manifest, "started-z", RUN_STARTED_EVENT, offset=2),
        _entry(manifest, "started-b", RUN_STARTED_EVENT, offset=1),
        _entry(manifest, "started-a", RUN_STARTED_EVENT, offset=1),
        _entry(manifest, "finished-a", RUN_FINISHED_EVENT, offset=4, status="ok"),
        _entry(manifest, "failed-a", RUN_FAILED_EVENT, offset=5, status="failed"),
        _entry(manifest, "shutdown-z", RUN_SHUTDOWN_EVENT, offset=5, status=""),
    ]
    ledger = _Ledger({manifest.run_id: entries})
    aliases: subject.WorkflowAliasMap = {
        (manifest.pipeline_name, manifest.run_type.value): (
            "primary",
            "exact-alias",
        ),
        (manifest.pipeline_name, None): ("generic-alias", "exact-alias"),
    }

    (record,) = subject.build_selector_records((manifest,), ledger, aliases)

    assert ledger.lookups == [manifest.run_id]
    assert record.workflow == "primary"
    assert record.workflow_candidates == (
        "primary",
        "7",
        "resolved",
        "exact-alias",
        "generic-alias",
        "chembl_activity",
        "workflow_chembl_activity",
    )
    assert record.started_at == manifest.created_at + timedelta(minutes=1)
    assert record.started_at_source == "run_ledger_started_event"
    assert record.completed_at == manifest.created_at + timedelta(minutes=5)
    assert record.completed_at_source == "run_ledger_terminal_event"
    assert record.run_status == "unknown"
    assert record.terminal_event_type == RUN_SHUTDOWN_EVENT


def test_build_selector_records_falls_back_without_ledger_events() -> None:
    manifest = _manifest(4)

    (without_port,) = subject.build_selector_records((manifest,), None)
    ledger = _Ledger({})
    (without_events,) = subject.build_selector_records((manifest,), ledger, {})

    assert without_port == without_events
    assert ledger.lookups == [manifest.run_id]
    assert without_port.workflow_candidates == (
        "chembl_activity",
        "workflow_chembl_activity",
    )
    assert without_port.started_at == manifest.created_at
    assert without_port.started_at_source == "manifest_created_at_fallback"
    assert without_port.completed_at == manifest.created_at
    assert without_port.completed_at_source == "manifest_created_at_fallback"
    assert without_port.run_status == "unknown"
    assert without_port.terminal_event_type is None


def test_build_selector_record_preserves_terminal_status_when_present() -> None:
    manifest = _manifest(5)
    terminal = _entry(
        manifest,
        "finished",
        RUN_FINISHED_EVENT,
        offset=1,
        status="success",
    )
    ledger = _Ledger({manifest.run_id: [terminal]})

    (record,) = subject.build_selector_records((manifest,), ledger)

    assert record.run_status == "success"
    assert record.terminal_event_type == RUN_FINISHED_EVENT


def test_selector_context_uses_matches_but_keeps_catalog_options_on_empty_scope() -> (
    None
):
    successful = _manifest(6)
    unstarted = _manifest(7, pipeline="pubchem_compound")
    terminal = _entry(
        successful,
        "finished",
        RUN_FINISHED_EVENT,
        offset=1,
        status="success",
    )
    ledger = _Ledger({successful.run_id: [terminal]})

    matched = selector_context.build_selector_context_payload(
        manifests=(successful, unstarted),
        ledger_port=ledger,
        selected_run_statuses=("success",),
    )
    empty_scope = selector_context.build_selector_context_payload(
        manifests=(successful, unstarted),
        ledger_port=ledger,
        selected_run_statuses=("failed",),
    )
    matched_selected = cast(dict[str, object], matched["selected"])
    matched_options = cast(dict[str, list[str]], matched["options"])
    empty_selected = cast(dict[str, object], empty_scope["selected"])
    empty_options = cast(dict[str, list[str]], empty_scope["options"])

    assert matched["resolved_via"] == "latest_terminal_run_for_scope"
    assert matched_selected["run_id"] == str(successful.run_id)
    assert matched_options["run_status"] == ["success"]
    assert empty_scope["resolved_via"] == "no_manifest_for_scope"
    assert empty_selected["run_id"] == "-"
    assert empty_options["pipeline"] == [
        "pubchem_compound",
        "chembl_activity",
    ]


def test_run_id_filter_options_avoid_unneeded_ledger_lookup() -> None:
    manifest = _manifest(8)
    ledger = _Ledger(
        {
            manifest.run_id: [
                _entry(
                    manifest,
                    "finished",
                    RUN_FINISHED_EVENT,
                    offset=1,
                    status="success",
                )
            ]
        }
    )

    payload = selector_context.build_selector_filter_options_payload(
        manifests=(manifest,),
        ledger_port=ledger,
        dimension="run_id",
        response_shape="list",
        requested_pipeline=None,
    )

    assert ledger.lookups == []
    assert payload == {"items": ["-", str(manifest.run_id)]}


def test_status_filter_options_use_ledger_and_return_contract_shape() -> None:
    manifest = _manifest(9)
    terminal = _entry(
        manifest,
        "finished",
        RUN_FINISHED_EVENT,
        offset=1,
        status="success",
    )
    ledger = _Ledger({manifest.run_id: [terminal]})

    payload = selector_context.build_selector_filter_options_payload(
        manifests=(manifest,),
        ledger_port=ledger,
        dimension="run_status",
        response_shape="contract",
        requested_pipeline="chembl_activity",
        selected_run_statuses=("success",),
    )

    assert ledger.lookups == [manifest.run_id]
    assert payload == {
        "contract": "control_plane_selector_context_v1",
        "dimension": "run_status",
        "pipeline": "chembl_activity",
        "run_type": [],
        "items": ["success"],
    }


def test_filter_options_apply_exact_run_fallback_and_validate_dimension() -> None:
    fallback = selector_context.build_selector_filter_options_payload(
        manifests=(),
        ledger_port=None,
        dimension="run_id",
        response_shape="list",
        requested_pipeline=None,
        exact_run_only=True,
        fallback_value=" fallback-run ",
    )
    no_fallback_value = selector_context.build_selector_filter_options_payload(
        manifests=(),
        ledger_port=None,
        dimension="run_id",
        response_shape="list",
        requested_pipeline=None,
        selected_run_id="missing-run",
        exact_run_only=True,
        fallback_value=None,
    )
    manifest = _manifest(10)
    selected = selector_context.build_selector_filter_options_payload(
        manifests=(manifest,),
        ledger_port=None,
        dimension="run_id",
        response_shape="list",
        requested_pipeline=None,
        selected_run_id=str(manifest.run_id),
        exact_run_only=True,
        fallback_value="unused-fallback",
    )

    assert fallback == {"items": ["-", "fallback-run"]}
    assert no_fallback_value == {"items": ["-"]}
    assert selected == {"items": ["-", str(manifest.run_id)]}

    with pytest.raises(ValueError, match="Unsupported control-plane filter dimension"):
        selector_context.build_selector_filter_options_payload(
            manifests=(),
            ledger_port=None,
            dimension="unsupported",
            response_shape="list",
            requested_pipeline=None,
        )
