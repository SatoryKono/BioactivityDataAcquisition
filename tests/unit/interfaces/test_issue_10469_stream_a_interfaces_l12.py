"""Stream A L12 interface residuals for #10469 / #10516."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.interfaces.http.control_plane_identity.payload import (
    _copy_fields,
    _identity_graph_status_text,
    _summary_overall_status,
    build_control_plane_identity_evidence_payload,
)
from bioetl.interfaces.http.run_report_ops import (
    _classify_index_state,
    _safe_segment,
    load_pipeline_run_report_artifact,
)


pytestmark = pytest.mark.unit


def test_identity_graph_complete_and_ok_summary_status() -> None:
    assert _identity_graph_status_text([], 0, True) == "complete"
    assert "gaps: run_id" in _identity_graph_status_text([{"name": "run_id"}], 0, None)
    assert _summary_overall_status([], manifest=object()) == "OK"
    assert _copy_fields(
        copy_flag=True, present=True, applicable=True, value_full="abc"
    ) == (True, "full_value", "abc")


def test_unresolved_checkpoint_compare_falls_back_to_identity_row() -> None:
    payload = build_control_plane_identity_evidence_payload(
        requested_pipeline="chembl_assay",
        resolved_manifest=None,
        selected_pipelines=("chembl_assay",),
        selected_run_id=None,
        selected_run_types=(),
        resolved_via="selection_required",
        ledger_port=None,
        view="checkpoint_compare",
    )
    assert payload["rows"][0]["ui_status"] == "SELECT RUN"
    assert payload["summary"]["overall_status"] == "SELECT RUN"


def test_safe_segment_rejects_parent_traversal() -> None:
    with pytest.raises(ValueError, match="invalid path segment"):
        _safe_segment("..")
    with pytest.raises(ValueError, match="invalid path segment"):
        _safe_segment("../secret")


def test_classify_index_state_uses_fallback_unhealthy_messages(tmp_path: Path) -> None:
    (tmp_path / "pipeline").mkdir()
    layout_state, layout_message = _classify_index_state(
        kind="pipeline",
        entry_count=0,
        root=tmp_path,
        diagnostics={"layout_status": "unhealthy"},
    )
    assert layout_state == "layout_unhealthy"
    assert "Report-root layout is unhealthy." in layout_message

    identity_state, identity_message = _classify_index_state(
        kind="pipeline",
        entry_count=0,
        root=tmp_path,
        diagnostics={
            "layout_status": "healthy",
            "source_identity_status": "unhealthy",
        },
    )
    assert identity_state == "identity_unhealthy"
    assert "Report-root source identity is unhealthy." in identity_message


def test_pipeline_report_artifact_rejects_unsupported_format_and_identity(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="unsupported report artifact format"):
        load_pipeline_run_report_artifact(
            pipeline="chembl_activity",
            run_id="run-1",
            artifact_format="html",
            root=tmp_path,
        )
    with pytest.raises(ValueError, match="invalid pipeline or run_id"):
        load_pipeline_run_report_artifact(
            pipeline="chembl activity",
            run_id="run-1",
            artifact_format="pipeline_run_report_json",
            root=tmp_path,
        )
