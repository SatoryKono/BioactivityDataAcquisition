"""TC-15 records PASS only for checks this process actually ran."""

from __future__ import annotations

import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

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
from iuphar_target_class.resolution import (
    Resolution,
    ResolutionInput,
    select_effective_class,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("remaining", [(), ("2",), ("1", "2")])
def test_acceptance_rejects_candidates_changed_by_resolution(
    monkeypatch: pytest.MonkeyPatch, remaining: tuple[str, ...]
) -> None:
    monkeypatch.setattr(
        sys.modules[__name__],
        "_run_requested_checks",
        lambda: {node.rsplit("::", 1)[-1]: "PASS" for node in _NODE_IDS},
    )
    resolve = select_effective_class
    seen: list[tuple[str, ...]] = []

    def corrupt(row: ResolutionInput) -> Resolution:
        seen.append(row.candidate_target_ids)
        return replace(resolve(row), candidate_target_ids=remaining)

    monkeypatch.setattr(sys.modules[__name__], "select_effective_class", corrupt)
    with pytest.raises(AssertionError, match="invariant_4_candidates_kept"):
        test_acceptance_report_marks_only_executed_checks()
    assert seen == [("2", "1")]


_NODE_IDS = (
    "tests/unit/iuphar_target_class/test_resolution.py::test_resolution_matrix",
    "tests/unit/iuphar_target_class/test_evidence.py::test_evidence_reference_integrity",
    "tests/unit/iuphar_target_class/test_evidence.py::test_evidence_unresolvable_reference",
    "tests/unit/iuphar_target_class/test_snapshot.py::test_snapshot_immutability",
    "tests/unit/iuphar_target_class/test_delivery.py::test_rerun_new_file",
    "tests/unit/iuphar_target_class/test_delivery.py::test_name_collision_blocked",
    "tests/unit/iuphar_target_class/test_w153.py::test_w153_join_receives_computed_rows",
)


def _case_status(case: ET.Element) -> str:
    if case.find("failure") is not None or case.find("error") is not None:
        return "FAIL"
    return "NOT_RUN" if case.find("skipped") is not None else "PASS"


def _requested_status(outcomes: Sequence[str]) -> str:
    if "FAIL" in outcomes:
        return "FAIL"
    return (
        "PASS"
        if outcomes and all(status == "PASS" for status in outcomes)
        else "NOT_RUN"
    )


def _run_requested_checks() -> dict[str, str]:
    root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    with TemporaryDirectory(prefix="iuphar-acceptance-") as directory:
        receipt = Path(directory) / "junit.xml"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                *_NODE_IDS,
                "-q",
                "--tb=line",
                "-k",
                "",
                "-m",
                "",
                f"--junitxml={receipt}",
            ],
            cwd=root,
            check=False,
            env=env,
            timeout=120,
        )
        assert completed.returncode == 0, "child pytest failed"
        cases: dict[tuple[str, str], list[str]] = {}
        for case in ET.parse(receipt).getroot().iter("testcase"):
            key = (case.get("classname", ""), case.get("name", "").split("[", 1)[0])
            cases.setdefault(key, []).append(_case_status(case))
    executed: dict[str, str] = {}
    for node in _NODE_IDS:
        path, name = node.split("::", 1)
        outcomes = cases.get((path.removesuffix(".py").replace("/", "."), name), [])
        executed[name] = _requested_status(outcomes)
    return executed


@pytest.mark.parametrize("name", sorted(NOT_RUN_REASONS))
@pytest.mark.parametrize("result", [None, "PASS", "FAIL"])
def test_blocked_checks_preserve_observed_failures(
    name: str, result: str | None
) -> None:
    report = build_acceptance_report({} if result is None else {name: result})
    checks = report["checks"]
    assert isinstance(checks, list)
    check = next(item for item in checks if item["name"] == name)
    assert check["status"] == ("FAIL" if result == "FAIL" else "NOT_RUN")
    if result != "FAIL":
        assert check["reason"] == NOT_RUN_REASONS[name]
    assert report["biological_accuracy_accepted"] is False


def _trace_child_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[set[str], dict[str, str]]:
    run = subprocess.run
    build = build_acceptance_report
    observed: set[str] = set()
    reported: dict[str, str] = {}

    def observe(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        options = [arg for arg in command if arg.startswith("--junitxml=")]
        receipt = (
            Path(options[-1].partition("=")[2])
            if options
            else tmp_path / "observed.xml"
        )
        actual = command if options else [*command, f"--junitxml={receipt}"]
        completed = run(actual, **kwargs)
        assert receipt.is_file()
        observed.update(
            case.attrib["name"].split("[", 1)[0]
            for case in ET.parse(receipt).getroot().iter("testcase")
            if case.find("skipped") is None
        )
        return completed

    def capture(executed: Mapping[str, str]) -> dict[str, object]:
        reported.update(executed)
        return build(executed)

    monkeypatch.setattr(subprocess, "run", observe)
    monkeypatch.setattr(sys.modules[__name__], "build_acceptance_report", capture)
    return observed, reported


def test_filtered_child_cannot_publish_unexecuted_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTEST_ADDOPTS", "-k snapshot_immutability")
    observed, reported = _trace_child_results(tmp_path, monkeypatch)
    test_acceptance_report_marks_only_executed_checks()
    requested = {node.rsplit("::", 1)[-1] for node in _NODE_IDS}
    passed = {name for name in requested if reported[name] == "PASS"}
    # Explicit node selection cancels the inherited -k filter: all requested
    # checks must really execute, rather than passing an empty subset check.
    assert observed == requested
    assert passed == requested


def test_deselected_child_is_not_reported_as_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTEST_ADDOPTS", f"--deselect={_NODE_IDS[0]}")
    observed, reported = _trace_child_results(tmp_path, monkeypatch)
    with pytest.raises(AssertionError, match="test_resolution_matrix"):
        test_acceptance_report_marks_only_executed_checks()
    assert "test_resolution_matrix" not in observed
    assert reported["test_resolution_matrix"] != "PASS"


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
    executed = _run_requested_checks()
    row = _row()
    table = EvidenceTable("run-1", (), (), ())
    later = RunProvenance("snap", None, "plan-v1-r8", None, "other", "other")
    executed["invariant_1_local_only"] = (
        "PASS" if not local_only_violation(row) else "FAIL"
    )
    candidate_input = ResolutionInput(
        match_status=row.match_status,
        iuphar_annotation_status=row.iuphar_annotation_status,
        local_status=row.local_status,
        iuphar_class=row.iuphar_class,
        local_class=row.local_class,
        candidate_target_ids=row.candidate_target_ids,
    )
    resolved = select_effective_class(candidate_input)
    executed["invariant_4_candidates_kept"] = (
        "PASS"
        if resolved.candidate_target_ids == candidate_input.candidate_target_ids
        else "FAIL"
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
        sys.modules[__name__],
        "_run_requested_checks",
        lambda: {node.rsplit("::", 1)[-1]: "PASS" for node in _NODE_IDS},
    )
    module = sys.modules[__name__]
    if failed_check == "invariant_4_candidates_kept":
        resolve = select_effective_class
        monkeypatch.setattr(
            module,
            "select_effective_class",
            lambda row: replace(resolve(row), candidate_target_ids=()),
        )
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
