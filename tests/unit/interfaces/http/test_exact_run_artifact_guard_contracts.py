"""Exact-run readers reject incomplete identity and changed child artifacts."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from bioetl.interfaces.http import _selected_run_artifact_probes as probes
from bioetl.interfaces.http import _selected_run_report_assessment as assessment
from bioetl.interfaces.http import _report_selector_options as options

pytestmark = pytest.mark.unit


def test_plain_selector_shape_returns_the_checked_identity_value(tmp_path):
    entry = SimpleNamespace(
        owner="chembl_assay",
        run_id="run",
        schema_version="pipeline_run_report_v2",
        identity_snapshot={
            "pipeline_name": "chembl_assay",
            "run_id": "run",
            "provider": "chembl",
        },
    )
    assert (
        options._maybe_report_option(
            entry=entry,
            dimension="provider",
            response_shape="values",
            scopes={},
            root=tmp_path,
            timezone="UTC",
            seen=set(),
        )
        == "chembl"
    )


@pytest.mark.parametrize("identity", [None, "..", "a/b"])
def test_current_child_path_requires_concrete_identity_components(tmp_path, identity):
    root = tmp_path / "pipeline" / "parent" / "run"
    root.mkdir(parents=True)
    assert probes._current_child_path(
        {"pipeline_name": identity, "run_id": "child"}, root
    ) == (None, "child_identity_invalid")


def test_child_reference_cannot_escape_the_identity_bound_path(tmp_path):
    root = tmp_path / "pipeline" / "parent" / "run"
    root.mkdir(parents=True)
    assert probes._current_child_path(
        {"pipeline_name": "chembl_assay", "run_id": "child", "ref": "../../outside"},
        root,
    ) == (None, "artifact_path_escape")


def test_changed_child_digest_is_rejected_even_when_child_status_is_green(
    tmp_path, monkeypatch
):
    root = tmp_path / "pipeline" / "parent" / "run"
    child = (
        tmp_path / "pipeline" / "chembl_assay" / "child" / "pipeline-run-report.json"
    )
    root.mkdir(parents=True)
    child.parent.mkdir(parents=True)
    child.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        assessment,
        "_load_report_assessment",
        lambda *args: (
            {},
            {"status": "success"},
            {"verdict": "OK", "evidence_completeness": "COMPLETE"},
            "AVAILABLE",
            "revision",
        ),
    )
    item = {
        "pipeline_name": "chembl_assay",
        "run_id": "child",
        "ref": "pipeline/chembl_assay/child/pipeline-run-report.json",
        "sha256": "different",
    }
    assert probes._probe_composite_child(item, root) == "child_digest_mismatch"


def test_child_removed_between_path_probe_and_read_is_reported_missing(
    tmp_path, monkeypatch
):
    root = tmp_path / "pipeline" / "parent" / "run"
    child = (
        tmp_path / "pipeline" / "chembl_assay" / "child" / "pipeline-run-report.json"
    )
    root.mkdir(parents=True)
    child.parent.mkdir(parents=True)
    child.write_text("{}", encoding="utf-8")

    def vanished(*args):
        raise FileNotFoundError("child vanished")

    monkeypatch.setattr(assessment, "_load_report_assessment", vanished)
    assert probes.probe_child_artifact(
        root,
        "pipeline/chembl_assay/child/pipeline-run-report.json",
        {"pipeline_name": "chembl_assay", "run_id": "child"},
    ) == ("fail", "artifact_missing")


@pytest.mark.parametrize("uri", ["file://", "file:///absent/source.jsonl"])
def test_file_snapshot_uri_is_checked_instead_of_treated_as_verified(uri):
    result = assessment._snapshot_file_verified(uri)
    assert result is None if uri == "file://" else result is False


def test_manifest_without_a_run_index_cannot_supply_identity():
    assert (
        assessment._manifest_snapshot(object(), "12345678-1234-5678-1234-567812345678")
        is None
    )


def test_invalid_assessment_shape_is_rejected_after_revision_read(
    tmp_path, monkeypatch
):
    path = tmp_path / "pipeline-run-report.json"
    snapshot = {"revision": "revision", "evidence": {}, "assessment": []}
    revisions = tmp_path / "status-revisions"
    revisions.mkdir()
    (revisions / "revision.json").write_text(json.dumps(snapshot), encoding="utf-8")
    monkeypatch.setattr(assessment, "verify_snapshot", lambda value: True)
    with pytest.raises(ValueError, match="assessment_invalid"):
        assessment._snapshot_assessment({}, snapshot, path)


@pytest.mark.parametrize("provider", [None, ""])
def test_selector_does_not_manufacture_an_option_for_missing_identity_field(
    tmp_path, provider
):
    entry = SimpleNamespace(
        owner="chembl_assay",
        run_id="run",
        schema_version="pipeline_run_report_v2",
        identity_snapshot={
            "pipeline_name": "chembl_assay",
            "run_id": "run",
            "provider": provider,
        },
    )
    assert (
        options._maybe_report_option(
            entry=entry,
            dimension="provider",
            response_shape="options",
            scopes={},
            root=tmp_path,
            timezone="UTC",
            seen=set(),
        )
        is None
    )
