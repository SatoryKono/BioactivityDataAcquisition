"""Incomplete workflow evidence cannot certify child ownership or measured totals."""

from __future__ import annotations

import pytest

from bioetl.domain.run_reports import workflow_reasons as reasons
from bioetl.domain.run_reports import workflow_totals as totals

pytestmark = pytest.mark.unit

PARENT = {"workflow_name": "workflow", "workflow_run_id": "parent"}
CHILD = {"pipeline_name": "chembl_assay", "run_id": "child"}
STEP = {
    "step_id": "extract",
    "pipeline_run_id": "child",
    "pipeline_name": "chembl_assay",
}


@pytest.mark.parametrize(
    "parent, child, step, gap",
    [
        (None, CHILD, "extract", "binding_not_recorded"),
        (
            {"workflow_name": None, "workflow_run_id": "parent"},
            CHILD,
            "extract",
            "identity_not_recorded",
        ),
        (
            {"workflow_name": "workflow", "workflow_run_id": None},
            CHILD,
            "extract",
            "identity_not_recorded",
        ),
        (PARENT, CHILD, None, "child_identity_not_recorded"),
        (
            PARENT,
            {"pipeline_name": "chembl_assay", "run_id": None},
            "extract",
            "child_identity_not_recorded",
        ),
        (
            PARENT,
            {"pipeline_name": None, "run_id": "child"},
            "extract",
            "child_identity_not_recorded",
        ),
    ],
)
def test_incomplete_child_evidence_has_a_specific_gap(parent, child, step, gap):
    assert reasons.resolve_child_workflow_binding(parent, child, step) == gap


def test_raw_coordinate_parsers_reject_non_mapping_evidence():
    assert reasons._workflow_binding_coordinates([]) is None
    assert reasons._child_binding_coordinates([], "extract") is None


@pytest.mark.parametrize(
    "parent, execution, gap",
    [
        (None, [STEP], "identity_mismatch"),
        ({**PARENT, "workflow_name": "other"}, [STEP], "identity_mismatch"),
        (PARENT, None, "child_binding_mismatch"),
        (PARENT, [None], "child_binding_mismatch"),
        (PARENT, [{**STEP, "step_id": "other"}], "child_binding_mismatch"),
        (PARENT, [{**STEP, "pipeline_run_id": "other"}], "child_binding_mismatch"),
        (PARENT, [{**STEP, "pipeline_name": "other"}], "child_binding_mismatch"),
        (PARENT, [STEP], None),
    ],
)
def test_parent_must_bind_the_exact_child_coordinates(parent, execution, gap):
    assert (
        reasons.parent_binding_gap(
            workflow_name="workflow",
            workflow_run_id="parent",
            parent_identity=parent,
            parent_execution=execution,
            step_id="extract",
            child_run_id="child",
            child_pipeline_name="chembl_assay",
        )
        == gap
    )


@pytest.mark.parametrize("snapshots, measured", [(None, {}), ({}, None), ([], [])])
def test_unmeasured_snapshot_cannot_certify_selected_version(snapshots, measured):
    assert not totals._selected_version_matches(
        {
            "selected_snapshots": snapshots,
            "source_snapshot": measured,
            "source_table": "chembl.assay",
        }
    )


@pytest.mark.parametrize(
    "snapshot, expected",
    [
        (None, None),
        ([], None),
        ({"physical_rows": "4", "current_rows": 2}, None),
        ({"physical_rows": 4, "current_rows": None}, None),
        ({"physical_rows": 4, "current_rows": 2}, 2),
    ],
)
def test_historical_totals_require_measured_integer_counters(snapshot, expected):
    assert totals._historical_snapshot_delta({"source_snapshot": snapshot}) == expected
