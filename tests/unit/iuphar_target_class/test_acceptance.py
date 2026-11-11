"""TC-15 records PASS only for checks this process actually ran."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from iuphar_target_class.acceptance import NOT_RUN_REASONS, build_acceptance_report
from iuphar_target_class.comparison import Stage0Reference, compare_stage0
from iuphar_target_class.evidence import (
    EvidenceTable,
    StoredRun,
    content_equal,
    local_only_violation,
    match_id_violation,
)
from iuphar_target_class.models import ClassificationResult, RunProvenance

pytestmark = pytest.mark.unit

_NODE_IDS = (
    "tests/unit/iuphar_target_class/test_resolution.py::test_resolution_matrix",
    "tests/unit/iuphar_target_class/test_evidence.py::test_evidence_reference_integrity",
    "tests/unit/iuphar_target_class/test_evidence.py::test_evidence_unresolvable_reference",
    "tests/unit/iuphar_target_class/test_snapshot.py::test_snapshot_immutability",
    "tests/unit/iuphar_target_class/test_delivery.py::test_rerun_new_file",
    "tests/unit/iuphar_target_class/test_delivery.py::test_name_collision_blocked",
    "tests/unit/iuphar_target_class/test_w153.py::test_w153_join_receives_computed_rows",
)


def _row() -> ClassificationResult:
    return ClassificationResult(
        input_row_id="row-1",
        snapshot_id="snap",
        input_validation_status="valid",
        input_errors=(),
        match_status="not_found",
        matched_target_id=None,
        candidate_target_ids=("2", "1"),
        iuphar_annotation_status=None,
        iuphar_class=None,
        iuphar_subclass=None,
        iuphar_class_candidates=(),
        iuphar_type_raw=None,
        iuphar_mapping_rule_id=None,
        iuphar_mapping_version=None,
        local_status="supported",
        local_class="Enzyme",
        local_subclasses=(),
        local_rule_ids=("ec:3",),
        effective_class="Enzyme",
        effective_subclasses=(),
        effective_source="local_rule",
        decision_status="resolved",
        conflict_codes=("direct_not_found",),
        match_evidence_ids=(),
        local_evidence_ids=("row-1/local_rule/ec:3/0001",),
        row_sha256="abc",
        provenance=RunProvenance("snap", None, "plan-v1-r8", None, "t", "t"),
    )


def test_acceptance_report_marks_only_executed_checks() -> None:
    root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", *_NODE_IDS, "-q", "--tb=line"],
        cwd=root,
        check=False,
        env=env,
    )
    batch = "PASS" if completed.returncode == 0 else "FAIL"
    executed = {node_id.rsplit("::", 1)[-1]: batch for node_id in _NODE_IDS}
    row = _row()
    table = EvidenceTable("run-1", (), (), ())
    later = RunProvenance("snap", None, "plan-v1-r8", None, "other", "other")
    executed["invariant_1_local_only"] = (
        "PASS" if not local_only_violation(row) else "FAIL"
    )
    executed["invariant_4_candidates_kept"] = (
        "PASS" if row.candidate_target_ids == ("2", "1") else "FAIL"
    )
    executed["invariant_8_match_id"] = "PASS" if not match_id_violation(row) else "FAIL"
    same = content_equal(
        StoredRun("plan-v1-r8", row.provenance, table, b"{}"),
        StoredRun("plan-v1-r8", later, table, b"{}"),
    )
    executed["invariant_5_rerun"] = "PASS" if same else "FAIL"
    empty = compare_stage0(Stage0Reference("stage0", 0, ()), ())
    executed["stage5_empty_reference"] = "PASS" if empty.metrics is None else "FAIL"
    report = build_acceptance_report(executed)
    checks = report["checks"]
    assert isinstance(checks, list)
    by_name = {item["name"]: item for item in checks}
    assert report["biological_accuracy_accepted"] is False
    assert report["mapping_version"] is None
    assert report["snapshot_id"] is None
    for name, reason in NOT_RUN_REASONS.items():
        assert by_name[name]["status"] == "NOT_RUN"
        assert by_name[name]["reason"] == reason
    for name in (
        *(node_id.rsplit("::", 1)[-1] for node_id in _NODE_IDS),
        "invariant_1_local_only",
        "invariant_4_candidates_kept",
        "invariant_8_match_id",
        "invariant_5_rerun",
        "stage5_empty_reference",
    ):
        assert by_name[name]["status"] == "PASS", name
    assert by_name["w153_integration"]["status"] == "NOT_RUN"
    assert "не принимается" in str(report["statement"])


@pytest.mark.parametrize(
    "failed_check",
    (
        "invariant_4_candidates_kept",
        "invariant_5_rerun",
        "stage5_empty_reference",
    ),
)
def test_acceptance_rejects_failed_computed_invariant(
    monkeypatch: pytest.MonkeyPatch, failed_check: str
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0),
    )
    module = sys.modules[__name__]
    if failed_check == "invariant_4_candidates_kept":
        row = replace(_row(), candidate_target_ids=("1", "2"))
        monkeypatch.setattr(module, "_row", lambda: row)
    elif failed_check == "invariant_5_rerun":
        monkeypatch.setattr(module, "content_equal", lambda left, right: False)
    else:
        empty = compare_stage0(Stage0Reference("stage0", 0, ()), ())
        monkeypatch.setattr(
            module,
            "compare_stage0",
            lambda reference, python_rows: replace(empty, metrics={}),
        )
    with pytest.raises(AssertionError) as failure:
        test_acceptance_report_marks_only_executed_checks()
    assert failed_check in str(failure.value)
