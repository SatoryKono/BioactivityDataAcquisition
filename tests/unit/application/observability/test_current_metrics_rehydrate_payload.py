"""Focused branch coverage for workflow rehydrate payload helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.observability import current_metrics_rehydrate_payload as subject
from bioetl.application.observability.rehydrate_models import WorkflowPipelineScopeInfo
from bioetl.application.services.run_reports.query import ReportIndexEntry

pytestmark = pytest.mark.unit


def _entry(path: Path, *, status: str | None = "success") -> ReportIndexEntry:
    return ReportIndexEntry(
        kind="workflow",
        owner="fallback-workflow",
        run_id="fallback-run",
        json_path=path,
        markdown_path=None,
        status=status,
        started_at=None,
        completed_at=None,
        mtime=0.0,
        workflow_id="fallback-id",
        workflow_run_id="fallback-workflow-run",
    )


def test_load_report_payload_rejects_io_invalid_json_and_non_mapping(tmp_path: Path) -> None:
    store = MagicMock()
    store.read_text.side_effect = OSError("missing")
    assert subject.load_report_payload(tmp_path / "missing.json", store=store) is None

    store.read_text.side_effect = None
    store.read_text.return_value = "{"
    assert subject.load_report_payload(tmp_path / "bad.json", store=store) is None
    store.read_text.return_value = "[]"
    assert subject.load_report_payload(tmp_path / "list.json", store=store) is None


@pytest.mark.parametrize(
    "payload",
    [None, {}, {"identity": {"workflow_name": "wf", "status": "running"}}],
)
def test_anchor_rejects_missing_identity_or_nonterminal_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: object
) -> None:
    monkeypatch.setattr(subject, "load_report_payload", lambda *_args, **_kwargs: payload)
    assert (
        subject.anchor_from_workflow_entry(
            _entry(tmp_path / "workflow.json"), root=tmp_path, store=MagicMock()
        )
        is None
    )


def test_anchor_can_skip_pipeline_scopes_and_use_fallback_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        subject,
        "load_report_payload",
        lambda *_args, **_kwargs: {
            "identity": {},
            "plan": {"steps": [{"pipeline_name": "chembl_assay"}]},
        },
    )
    anchor = subject.anchor_from_workflow_entry(
        _entry(tmp_path / "workflow.json"),
        root=tmp_path,
        store=MagicMock(),
        include_pipeline_scopes=False,
    )
    assert anchor is not None
    assert (anchor.workflow, anchor.run_id, anchor.provider, anchor.pipelines) == (
        "fallback-workflow",
        "fallback-workflow-run",
        "chembl",
        (),
    )


def test_workflow_provider_and_pipeline_names_cover_fallbacks() -> None:
    scope = WorkflowPipelineScopeInfo(
        pipeline="chembl_assay", run_type="backfill", provider="chembl"
    )
    assert subject.workflow_provider({}, (scope,)) == "chembl"
    assert subject.workflow_provider({}, ()) == "unknown"
    assert subject.provider_from_pipeline_name("custom") == "custom"
    assert subject.provider_from_pipeline_name("") == "unknown"
    assert subject.pipeline_names_from_payload(
        {
            "execution": [None, {"pipeline_name": ""}, {"pipeline_name": "chembl_assay"}],
            "plan": {
                "steps": [
                    {"pipeline_name": "chembl_assay"},
                    {"pipeline_name": "pubchem_compound"},
                ]
            },
        }
    ) == ("chembl_assay", "pubchem_compound")
    assert subject.pipeline_names_from_payload({"execution": object(), "plan": []}) == ()


def test_pipeline_scopes_skip_invalid_rows_and_deduplicate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        subject,
        "load_pipeline_report",
        lambda **_kwargs: {"identity": {"run_type": "incremental"}},
    )
    payload = {
        "execution": [
            None,
            {},
            {"pipeline_name": "chembl_assay"},
            {"pipeline_name": "chembl_assay", "run_type": "backfill"},
            {"pipeline_name": "chembl_assay", "run_type": "backfill"},
            {"pipeline_name": "pubchem_compound", "pipeline_run_id": "child"},
        ]
    }
    scopes = subject.pipeline_scopes_from_payload(
        payload, root=tmp_path, store=MagicMock()
    )
    assert [(item.pipeline, item.run_type, item.provider) for item in scopes] == [
        ("chembl_assay", "backfill", "chembl"),
        ("pubchem_compound", "incremental", "pubchem"),
    ]
    assert subject.pipeline_scopes_from_payload({}, root=tmp_path, store=MagicMock()) == ()


def test_run_type_child_report_failure_shapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MagicMock()
    assert (
        subject.run_type_from_execution_row(
            {"run_type": "backfill"}, pipeline="p", root=None, store=store
        )
        == "backfill"
    )
    assert (
        subject.run_type_from_execution_row({}, pipeline="p", root=None, store=store)
        == ""
    )
    for child in (None, {}, {"identity": []}):
        monkeypatch.setattr(subject, "load_pipeline_report", lambda **_kwargs: child)
        assert (
            subject.run_type_from_execution_row(
                {"pipeline_run_id": "child"}, pipeline="p", root=None, store=store
            )
            == ""
        )
