# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for deterministic flaky-test burndown review generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.engineering.qa.report_flaky_test_burndown_review import (
    build_empirical_payload,
    build_payload,
    compute_replay_tree_sha256,
    main,
)

pytestmark = pytest.mark.unit
REPLAY_SHA = "b" * 64


def _write_inputs(
    repo_root: Path,
    *,
    entries: list[dict[str, Any]] | None = None,
) -> None:
    inventory = {
        "schema_version": 1,
        "reviewed_on": "2026-07-17",
        "linked_issues": [6351, 5514],
        "evidence_scope": "Curated review bound to static test evidence.",
        "flaky_test_definition": ["intermittent pass/fail outcome"],
        "remediation_workflow": ["stabilize the deterministic seam"],
        "dimensions": {
            "layers": ["application", "domain"],
            "categories": ["Data", "State"],
            "severities": ["P1", "P2"],
            "triage_statuses": ["fixed", "needs-triage"],
            "alert_levels": ["critical", "warning"],
        },
        "reviewed_flaky_tests": entries or [],
        "review_notes": ["Review note."],
    }
    governance = {
        "source_tree_sha256": "a" * 64,
        "budget_violations": [],
        "report": {
            "total_test_functions": 7,
            "total_test_files": 2,
        },
    }
    inventory_path = repo_root / "configs" / "quality" / "flaky_test_inventory.yaml"
    governance_path = repo_root / "reports" / "quality" / "test-governance-current.json"
    inventory_path.parent.mkdir(parents=True)
    governance_path.parent.mkdir(parents=True)
    inventory_path.write_text(
        yaml.safe_dump(inventory, sort_keys=False),
        encoding="utf-8",
    )
    governance_path.write_text(json.dumps(governance), encoding="utf-8")


def _entry(
    nodeid: str,
    *,
    layer: str,
    category: str,
    severity: str,
    triage_status: str,
    alert_level: str,
) -> dict[str, str]:
    return {
        "nodeid": nodeid,
        "owner": "quality-team",
        "cause": "deterministic test cause",
        "remediation": "replace the unstable seam",
        "layer": layer,
        "category": category,
        "severity": severity,
        "triage_status": triage_status,
        "alert_level": alert_level,
    }


def _write_empirical_run(
    run_dir: Path,
    *,
    run_id: str,
    seed: int,
    outcomes: list[tuple[str, str]],
    source_sha: str = "abc123",
    replay_sha: object = REPLAY_SHA,
    include_replay_sha: bool = True,
    write_junit: bool = True,
) -> None:
    metadata: dict[str, object] = {
        "run_id": run_id,
        "seed": seed,
        "source_sha": source_sha,
        "order_mode": "seeded-random",
        "shard_id": "determinism-critical",
    }
    if include_replay_sha:
        metadata["replay_tree_sha256"] = replay_sha
    (run_dir / f"run-{run_id}.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )
    if not write_junit:
        return
    cases = []
    result_elements = {
        "passed": "",
        "failed": "<failure/>",
        "error": "<error/>",
        "skipped": "<skipped/>",
    }
    for nodeid, status in outcomes:
        classname, name = nodeid.split("::", maxsplit=1)
        cases.append(
            f'<testcase classname="{classname}" name="{name}">'
            f"{result_elements[status]}</testcase>"
        )
    (run_dir / f"junit-{run_id}.xml").write_text(
        f'<testsuite tests="{len(outcomes)}">{"".join(cases)}</testsuite>',
        encoding="utf-8",
    )


def _write_stable_empirical_runs(
    tmp_path: Path,
    *,
    source_shas: tuple[str, str, str] = ("abc123", "abc123", "abc123"),
    replay_shas: tuple[object, object, object] = (
        REPLAY_SHA,
        REPLAY_SHA,
        REPLAY_SHA,
    ),
) -> Path:
    _write_inputs(tmp_path)
    run_dir = tmp_path / "runs"
    run_dir.mkdir()
    for index, (seed, source_sha, replay_sha) in enumerate(
        zip((17, 73, 113), source_shas, replay_shas, strict=True),
        start=1,
    ):
        _write_empirical_run(
            run_dir,
            run_id=f"r{index}",
            seed=seed,
            outcomes=[("tests.test_x::test_stable", "passed")],
            source_sha=source_sha,
            replay_sha=replay_sha,
        )
    return run_dir


def test_build_payload__unsorted_entries__renders_stable_counts_and_order(
    tmp_path: Path,
) -> None:
    _write_inputs(
        tmp_path,
        entries=[
            _entry(
                "tests/unit/test_z.py::test_z",
                layer="domain",
                category="State",
                severity="P2",
                triage_status="needs-triage",
                alert_level="warning",
            ),
            _entry(
                "tests/unit/test_a.py::test_a",
                layer="application",
                category="Data",
                severity="P1",
                triage_status="fixed",
                alert_level="critical",
            ),
        ],
    )

    payload = build_payload(tmp_path)

    assert [row["nodeid"] for row in payload["reviewed_flaky_tests"]] == [
        "tests/unit/test_a.py::test_a",
        "tests/unit/test_z.py::test_z",
    ]
    assert payload["summary"]["total_flaky"] == 2
    assert payload["summary"]["by_layer"] == {"application": 1, "domain": 1}
    assert payload["summary"]["by_triage"] == {
        "fixed": 1,
        "needs-triage": 1,
    }
    assert payload["summary"]["total_tests_analyzed"] == 7
    assert payload["decision"] == "remediation_required"


def test_build_payload__duplicate_nodeid__fails_closed(tmp_path: Path) -> None:
    duplicate = _entry(
        "tests/unit/test_dup.py::test_dup",
        layer="domain",
        category="State",
        severity="P2",
        triage_status="needs-triage",
        alert_level="warning",
    )
    _write_inputs(tmp_path, entries=[duplicate, duplicate])

    with pytest.raises(ValueError, match="Duplicate nodeid"):
        build_payload(tmp_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("reviewed_on", "17 July 2026", "Expected ISO date"),
        ("linked_issues", [5514, 5514], "Duplicate values"),
    ],
)
def test_build_payload__invalid_inventory_metadata__fails_closed(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    _write_inputs(tmp_path)
    inventory_path = tmp_path / "configs" / "quality" / "flaky_test_inventory.yaml"
    inventory = yaml.safe_load(inventory_path.read_text(encoding="utf-8"))
    assert isinstance(inventory, dict)
    inventory[field] = value
    inventory_path.write_text(
        yaml.safe_dump(inventory, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=message):
        build_payload(tmp_path)


def test_main__tracked_artifact_lifecycle__detects_missing_current_and_stale(
    tmp_path: Path,
) -> None:
    _write_inputs(tmp_path)
    check_args = ["--repo-root", str(tmp_path), "--check"]

    assert main(check_args) == 1
    assert main(["--repo-root", str(tmp_path)]) == 0
    assert main(check_args) == 0

    output = tmp_path / "reports" / "quality" / "flaky-test-burndown-review.json"
    output.write_text("{}\n", encoding="utf-8")
    assert main(check_args) == 1


def test_main__missing_canonical_input__returns_input_error(tmp_path: Path) -> None:
    assert main(["--repo-root", str(tmp_path)]) == 2


def test_empirical_payload_persists_seeds_and_reconciles_stable_runs(
    tmp_path: Path,
) -> None:
    run_dir = _write_stable_empirical_runs(tmp_path)

    payload = build_empirical_payload(tmp_path, run_dir=Path("runs"))

    assert payload["run_count"] == 3
    assert [run["seed"] for run in payload["runs"]] == [17, 73, 113]
    assert [
        run["artifact_hashes"]["replay_tree_sha256"] for run in payload["runs"]
    ] == [REPLAY_SHA, REPLAY_SHA, REPLAY_SHA]
    assert payload["comparison"]["unstable_node_count"] == 0
    assert payload["comparison"]["replay_fingerprint_stable"] is True
    assert payload["curated_inventory_reconciliation"]["untriaged_count"] == 0
    assert run_dir.is_dir()


def test_compute_replay_tree_sha256__same_tree__is_deterministic(
    tmp_path: Path,
) -> None:
    replay_dir = tmp_path / "tests" / "fixtures" / "vcr" / "provider"
    replay_dir.mkdir(parents=True)
    (replay_dir / "b.yaml").write_text("b: 2\n", encoding="utf-8")
    (replay_dir / "a.yaml").write_text("a: 1\n", encoding="utf-8")

    first = compute_replay_tree_sha256(tmp_path)
    second = compute_replay_tree_sha256(tmp_path)
    (replay_dir / "b.yaml").write_text("b: 3\n", encoding="utf-8")
    changed = compute_replay_tree_sha256(tmp_path)

    assert first == second
    assert len(first) == 64
    assert changed != first


def test_empirical_payload__outcome_changes__surfaces_unstable_node(
    tmp_path: Path,
) -> None:
    run_dir = _write_stable_empirical_runs(tmp_path)
    _write_empirical_run(
        run_dir,
        run_id="r2",
        seed=73,
        outcomes=[("tests.test_x::test_stable", "failed")],
    )

    payload = build_empirical_payload(tmp_path, run_dir=Path("runs"))

    assert payload["comparison"]["unstable_node_count"] == 1
    assert payload["comparison"]["unstable_nodes"] == {
        "tests.test_x::test_stable": ["failed", "passed"]
    }
    assert payload["comparison"]["untriaged_unstable_nodes"] == [
        "tests.test_x::test_stable"
    ]
    assert payload["curated_inventory_reconciliation"]["untriaged_count"] == 1


def test_empirical_payload__testcase_order_changes__keeps_identical_coverage(
    tmp_path: Path,
) -> None:
    _write_inputs(tmp_path)
    run_dir = tmp_path / "runs"
    run_dir.mkdir()
    nodeids = [
        ("tests.test_x::test_alpha", "passed"),
        ("tests.test_x::test_beta", "passed"),
    ]
    for index, seed in enumerate((17, 73, 113), start=1):
        _write_empirical_run(
            run_dir,
            run_id=f"r{index}",
            seed=seed,
            outcomes=nodeids if index % 2 else list(reversed(nodeids)),
        )

    payload = build_empirical_payload(tmp_path, run_dir=Path("runs"))

    assert payload["comparison"]["unstable_node_count"] == 0


@pytest.mark.parametrize(
    ("reference_outcomes", "outcomes", "expected_delta"),
    [
        (
            [
                ("tests.test_x::test_stable", "passed"),
                ("tests.test_x::test_required", "passed"),
            ],
            [("tests.test_x::test_stable", "passed")],
            "r2: missing=['tests.test_x::test_required'], extra=[]",
        ),
        (
            [("tests.test_x::test_stable", "passed")],
            [
                ("tests.test_x::test_stable", "passed"),
                ("tests.test_x::test_extra", "passed"),
            ],
            "r2: missing=[], extra=['tests.test_x::test_extra']",
        ),
    ],
)
def test_empirical_payload__node_coverage_differs__fails_with_stable_delta(
    tmp_path: Path,
    reference_outcomes: list[tuple[str, str]],
    outcomes: list[tuple[str, str]],
    expected_delta: str,
) -> None:
    run_dir = _write_stable_empirical_runs(tmp_path)
    _write_empirical_run(
        run_dir,
        run_id="r1",
        seed=17,
        outcomes=reference_outcomes,
    )
    _write_empirical_run(
        run_dir,
        run_id="r2",
        seed=73,
        outcomes=outcomes,
    )
    _write_empirical_run(
        run_dir,
        run_id="r3",
        seed=113,
        outcomes=reference_outcomes,
    )

    with pytest.raises(ValueError) as exc_info:
        build_empirical_payload(tmp_path, run_dir=Path("runs"))

    assert expected_delta in str(exc_info.value)


def test_empirical_payload__replay_fingerprint_differs__reports_unstable(
    tmp_path: Path,
) -> None:
    _write_stable_empirical_runs(
        tmp_path,
        replay_shas=(REPLAY_SHA, REPLAY_SHA, "c" * 64),
    )

    payload = build_empirical_payload(tmp_path, run_dir=Path("runs"))

    assert payload["comparison"]["replay_fingerprint_stable"] is False
    assert (
        main(
            [
                "--repo-root",
                str(tmp_path),
                "--empirical-run-dir",
                "runs",
            ]
        )
        == 1
    )


@pytest.mark.parametrize("replay_sha", [None, "not-a-sha256", "G" * 64])
def test_empirical_payload__malformed_replay_fingerprint__fails_closed(
    tmp_path: Path,
    replay_sha: object,
) -> None:
    _write_stable_empirical_runs(
        tmp_path,
        replay_shas=(REPLAY_SHA, replay_sha, REPLAY_SHA),
    )

    with pytest.raises(ValueError, match="Invalid SHA-256 at .*replay_tree_sha256"):
        build_empirical_payload(tmp_path, run_dir=Path("runs"))


def test_empirical_payload__missing_replay_fingerprint__fails_closed(
    tmp_path: Path,
) -> None:
    run_dir = _write_stable_empirical_runs(tmp_path)
    _write_empirical_run(
        run_dir,
        run_id="r2",
        seed=73,
        outcomes=[("tests.test_x::test_stable", "passed")],
        include_replay_sha=False,
    )

    with pytest.raises(ValueError, match="Invalid SHA-256 at .*replay_tree_sha256"):
        build_empirical_payload(tmp_path, run_dir=Path("runs"))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("run_id", "", "Invalid run_id"),
        ("seed", True, "Invalid seed"),
        ("source_sha", "", "Invalid source_sha"),
    ],
)
def test_empirical_payload__invalid_run_metadata__fails_closed(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    run_dir = _write_stable_empirical_runs(tmp_path)
    metadata_path = run_dir / "run-r2.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata[field] = value
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        build_empirical_payload(tmp_path, run_dir=Path("runs"))


def test_empirical_payload__fewer_than_three_runs__fails_closed(
    tmp_path: Path,
) -> None:
    run_dir = _write_stable_empirical_runs(tmp_path)
    (run_dir / "run-r3.json").unlink()
    (run_dir / "junit-r3.xml").unlink()

    with pytest.raises(ValueError, match="requires at least three runs"):
        build_empirical_payload(tmp_path, run_dir=Path("runs"))


def test_empirical_payload__mismatched_source_sha__fails_closed(
    tmp_path: Path,
) -> None:
    _write_stable_empirical_runs(
        tmp_path,
        source_shas=("abc123", "different", "abc123"),
    )

    with pytest.raises(ValueError, match="must use one source SHA"):
        build_empirical_payload(tmp_path, run_dir=Path("runs"))


def test_empirical_payload__missing_junit__fails_closed(tmp_path: Path) -> None:
    run_dir = _write_stable_empirical_runs(tmp_path)
    (run_dir / "junit-r2.xml").unlink()

    with pytest.raises(ValueError, match="Missing JUnit for r2"):
        build_empirical_payload(tmp_path, run_dir=Path("runs"))


def test_empirical_payload__zero_outcome_run__fails_closed(tmp_path: Path) -> None:
    run_dir = _write_stable_empirical_runs(tmp_path)
    _write_empirical_run(
        run_dir,
        run_id="r2",
        seed=73,
        outcomes=[],
    )

    with pytest.raises(ValueError, match="executed zero tests: r2"):
        build_empirical_payload(tmp_path, run_dir=Path("runs"))
