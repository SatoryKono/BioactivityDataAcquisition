"""Generated artifact and subtraction routing tests for CI lanes."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import (
    OWNER_STEPS,
    affected_pytest_targets,
    assert_step_outcomes,
    build_results,
    build_shadow_compare,
    main as lane_main,
    plan_affected_subtraction,
)

pytestmark = pytest.mark.unit

HEAD = "a" * 40


def test_generated_artifact_sibling_uses_canonical_test_registry(
    tmp_path: Path,
) -> None:
    """Route a generated sibling through its registered artifact test."""
    test_path = "tests/architecture/test_generated_report.py"
    target = tmp_path / test_path
    target.parent.mkdir(parents=True)
    target.write_text("def test_report():\n    assert True\n", encoding="utf-8")
    registry = tmp_path / "configs/quality/generated_artifact_tests.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "tests": [
                    {
                        "node": f"{test_path}::test_report",
                        "artifacts": ["reports/quality/report.json"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (registry.parent / "generated_artifact_routing.yaml").write_text(
        "routes:\n"
        "  - id: report\n"
        "    outputs:\n"
        "      - reports/quality/report.json\n"
        "      - reports/quality/report.md\n",
        encoding="utf-8",
    )

    report = build_shadow_compare(
        ["reports/quality/report.md"],
        repo_root=tmp_path,
    )

    assert report["selected"] == [test_path]


def test_generated_artifact_route_unions_direct_and_sibling_tests(
    tmp_path: Path,
) -> None:
    """A direct artifact match must not hide tests owned by its sibling."""
    json_test = "tests/architecture/test_generated_json.py"
    markdown_test = "tests/architecture/test_generated_markdown.py"
    for test_path in (json_test, markdown_test):
        target = tmp_path / test_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("def test_report():\n    assert True\n", encoding="utf-8")
    registry = tmp_path / "configs/quality/generated_artifact_tests.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "tests": [
                    {
                        "node": f"{json_test}::test_report",
                        "artifacts": ["reports/quality/report.json"],
                    },
                    {
                        "node": f"{markdown_test}::test_report",
                        "artifacts": ["reports/quality/report.md"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (registry.parent / "generated_artifact_routing.yaml").write_text(
        "routes:\n"
        "  - id: report\n"
        "    outputs:\n"
        "      - reports/quality/report.json\n"
        "      - reports/quality/report.md\n",
        encoding="utf-8",
    )

    report = build_shadow_compare(
        ["reports/quality/report.json"],
        repo_root=tmp_path,
    )

    assert report["selected"] == [json_test, markdown_test]


def test_static_mapping_unions_generated_registry_tests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A static path mapping must not suppress generated-registry owners."""
    from scripts.engineering.ci import pr_lane_results as lane

    artifact = "reports/quality/report.json"
    static_test = "tests/architecture/test_static_owner.py"
    generated_test = "tests/architecture/test_generated_owner.py"
    for test_path in (static_test, generated_test):
        target = tmp_path / test_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("def test_report():\n    assert True\n", encoding="utf-8")
    monkeypatch.setitem(lane.AFFECTED_TESTS_BY_PATH, artifact, (static_test,))
    registry = tmp_path / "configs/quality/generated_artifact_tests.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "tests": [
                    {
                        "node": f"{generated_test}::test_report",
                        "artifacts": [artifact],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_shadow_compare([artifact], repo_root=tmp_path)

    assert report["selected"] == [static_test, generated_test]


def test_generated_artifact_directory_output_routes_descendants(
    tmp_path: Path,
) -> None:
    """A tracked output directory owns generated files below it."""
    test_path = "tests/architecture/test_generated_directory.py"
    target = tmp_path / test_path
    target.parent.mkdir(parents=True)
    target.write_text("def test_report():\n    assert True\n", encoding="utf-8")
    registry = tmp_path / "configs/quality/generated_artifact_tests.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "tests": [
                    {
                        "node": f"{test_path}::test_report",
                        "artifacts": ["docs/generated/"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (registry.parent / "generated_artifact_routing.yaml").write_text(
        "routes:\n  - id: docs\n    outputs:\n      - docs/generated/\n",
        encoding="utf-8",
    )

    report = build_shadow_compare(
        ["docs/generated/nested/report.json"],
        repo_root=tmp_path,
    )

    assert report["selected"] == [test_path]


def _reject_collection(
    targets: Sequence[str], *, marker: str | None = None
) -> set[str]:
    raise AssertionError((targets, marker))


def test_subtraction_keeps_disjoint_targets_without_collection() -> None:
    """A target outside the fixed lane is not collected or rewritten."""
    plan = plan_affected_subtraction(
        ["tests/unit/test_sample.py"],
        ["tests/architecture"],
        collect_nodeids=_reject_collection,
    )
    assert plan.execution_targets == ("tests/unit/test_sample.py",)
    assert plan.ignore_paths == ()
    assert plan.intersection == ()


def test_subtraction_drops_fixed_lane_files_and_reports_nodeids() -> None:
    """Selectors already owned by the fixed lane are omitted, not re-run."""
    seen: list[tuple[tuple[str, ...], str | None]] = []

    def collect(targets: Sequence[str], *, marker: str | None = None) -> set[str]:
        seen.append((tuple(targets), marker))
        return {f"{targets[0]}::test_covered"}

    plan = plan_affected_subtraction(
        ["tests/unit/test_sample.py", "tests/architecture/test_ci.py"],
        ["tests/architecture"],
        collect_nodeids=collect,
    )
    assert plan.execution_targets == ("tests/unit/test_sample.py",)
    assert plan.ignore_paths == ()
    assert plan.intersection == ("tests/architecture/test_ci.py::test_covered",)
    assert seen == [
        (
            ("tests/architecture/test_ci.py",),
            "not slow and not benchmark and not memory",
        ),
        (("tests/architecture/test_ci.py",), None),
    ]


def test_subtraction_ignores_fixed_root_when_parent_is_selected() -> None:
    """The full suite stays one target and ignores the fixed lane."""

    def collect(targets: Sequence[str], *, marker: str | None = None) -> set[str]:
        assert tuple(targets) == ("tests/architecture",)
        assert marker in (None, "not slow and not benchmark and not memory")
        return {
            "tests/architecture/test_ci.py::test_one",
            "tests/architecture/test_ci.py::test_two",
        }

    plan = plan_affected_subtraction(
        ["tests"],
        ["tests/architecture"],
        collect_nodeids=collect,
    )
    assert plan.execution_targets == ("tests",)
    assert plan.ignore_paths == ("tests/architecture",)
    assert plan.intersection == (
        "tests/architecture/test_ci.py::test_one",
        "tests/architecture/test_ci.py::test_two",
    )


def test_subtraction_keeps_tests_the_fixed_lane_skips() -> None:
    """Slow architecture tests stay in the affected run."""

    def collect(targets: Sequence[str], *, marker: str | None = None) -> set[str]:
        assert tuple(targets) == ("tests/architecture/test_ci.py",)
        if marker:
            return {"tests/architecture/test_ci.py::test_fast"}
        return {
            "tests/architecture/test_ci.py::test_fast",
            "tests/architecture/test_ci.py::test_slow",
        }

    plan = plan_affected_subtraction(
        ["tests/architecture/test_ci.py"],
        ["tests/architecture"],
        collect_nodeids=collect,
    )
    assert plan.execution_targets == ("tests/architecture/test_ci.py::test_slow",)
    assert plan.ignore_paths == ()
    assert plan.intersection == ("tests/architecture/test_ci.py::test_fast",)


def test_subtraction_fails_closed_on_empty_selection() -> None:
    """An empty affected file is a broken selector, not an empty success."""
    with pytest.raises(ValueError, match="no affected pytest target"):
        plan_affected_subtraction(
            [],
            ["tests/architecture"],
            collect_nodeids=_reject_collection,
        )


def test_subtract_command_writes_plan_and_intersection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI records covered nodeids and the ignore used at execution time."""
    from scripts.engineering.ci import pr_lane_results as lane

    affected = tmp_path / "affected.txt"
    affected.write_text("tests\n", encoding="utf-8")
    output = tmp_path / "deduped.txt"
    ignore = tmp_path / "ignores.txt"

    def collect(
        root: Path, targets: Sequence[str], *, marker: str | None = None
    ) -> set[str]:
        assert root == tmp_path
        assert tuple(targets) == ("tests/architecture",)
        assert marker in (None, "not slow and not benchmark and not memory")
        return {"tests/architecture/test_ci.py::test_one"}

    monkeypatch.setattr(lane, "_collect_nodeids", collect)
    assert (
        lane_main(
            [
                "subtract-affected",
                "--repo-root",
                str(tmp_path),
                "--fixed-targets",
                "tests/architecture",
                "--affected-file",
                str(affected),
                "--output",
                str(output),
                "--ignore-file",
                str(ignore),
            ]
        )
        == 0
    )
    assert output.read_text(encoding="utf-8") == "tests\n"
    assert ignore.read_text(encoding="utf-8") == "tests/architecture\n"
    captured = capsys.readouterr()
    assert "tests/architecture/test_ci.py::test_one" in captured.err
    assert "fixed-lane ignores: tests/architecture" in captured.err


def test_subtract_command_fail_closed_does_not_write_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken selector must not leave a runnable target file behind."""
    from scripts.engineering.ci import pr_lane_results as lane

    affected = tmp_path / "affected.txt"
    affected.write_text("tests/architecture/test_missing.py\n", encoding="utf-8")
    output = tmp_path / "deduped.txt"

    def collect(
        _root: Path, _targets: Sequence[str], *, marker: str | None = None
    ) -> set[str]:
        raise ValueError(f"pytest collection failed (4) {marker}")

    monkeypatch.setattr(lane, "_collect_nodeids", collect)
    assert (
        lane_main(
            [
                "subtract-affected",
                "--repo-root",
                str(tmp_path),
                "--fixed-targets",
                "tests/architecture",
                "--affected-file",
                str(affected),
                "--output",
                str(output),
                "--ignore-file",
                str(tmp_path / "ignores.txt"),
            ]
        )
        == 1
    )
    assert not output.exists()
    assert not (tmp_path / "ignores.txt").exists()


def test_subtract_command_writes_empty_plan_when_lane_covers_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Full overlap is a successful skip, not a failed tests gate."""
    from scripts.engineering.ci import pr_lane_results as lane

    affected = tmp_path / "affected.txt"
    affected.write_text("tests/architecture/test_ci.py\n", encoding="utf-8")
    output = tmp_path / "deduped.txt"
    ignore = tmp_path / "ignores.txt"

    def collect(
        _root: Path, targets: Sequence[str], *, marker: str | None = None
    ) -> set[str]:
        assert marker in (None, "not slow and not benchmark and not memory")
        return {f"{targets[0]}::test_covered"}

    monkeypatch.setattr(lane, "_collect_nodeids", collect)
    assert (
        lane_main(
            [
                "subtract-affected",
                "--repo-root",
                str(tmp_path),
                "--fixed-targets",
                "tests/architecture",
                "--affected-file",
                str(affected),
                "--output",
                str(output),
                "--ignore-file",
                str(ignore),
            ]
        )
        == 0
    )
    assert output.read_text(encoding="utf-8") == ""
    assert ignore.read_text(encoding="utf-8") == ""


def test_collect_nodeids_parses_pytest_collection(tmp_path: Path) -> None:
    """Collection keeps real nodeids and rejects a missing selector."""
    from scripts.engineering.ci.pr_lane_results import _collect_nodeids

    test_file = tmp_path / "tests" / "test_sample.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_one():\n    assert True\n", encoding="utf-8")
    assert _collect_nodeids(tmp_path, ["tests/test_sample.py"]) == {
        "tests/test_sample.py::test_one"
    }
    with pytest.raises(ValueError, match="pytest collection failed"):
        _collect_nodeids(tmp_path, ["tests/missing.py"])


@pytest.mark.parametrize(
    "changed_file",
    [
        "configs/quality/external_resource_inventory.json",
        *[
            f"configs/quality/external_resource_inventory/part-{index:02}.json"
            for index in range(1, 6)
        ],
        "reports/quality/external-resource-inventory.md",
        "scripts/engineering/qa/README.md",
    ],
)
def test_resource_inventory_files_select_integrity_controls(changed_file: str) -> None:
    """Every inventory input and projection retains its owning integrity suite."""
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([changed_file], repo_root=root)
    assert (
        "tests/unit/scripts/engineering/qa/test_external_resource_inventory.py"
        in report["selected"]
    )
    catalog_test = "tests/architecture/test_external_resource_inventory_catalog.py"
    assert catalog_test in report["selected"]
    assert (root / catalog_test).is_file()
    assert report["activation"] == "not_applied"
