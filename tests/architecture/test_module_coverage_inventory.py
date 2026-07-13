"""Architecture guardrails for committed module-level coverage inventory."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.engineering.qa.report_module_coverage_inventory import (
    _iter_source_modules,
    compute_source_tree_sha256,
    main as module_coverage_inventory_main,
)
from tests.architecture._module_coverage_inventory_support import (
    skip_if_module_coverage_inventory_is_dirty,
)
from tests.architecture._test_matrix_policy_support import load_matrix

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "reports" / "quality" / "module-coverage-inventory.json"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "tests.yml"
SCORECARD_PATH = ROOT / "configs" / "quality" / "debt_scorecard.yaml"
GATES_PATH = ROOT / "configs" / "quality" / "module_coverage_gates.yaml"
COVERAGE_TAIL_CLOSEOUT_PATH = (
    ROOT / "reports" / "quality" / "issue-5376-coverage-tail-closeout.json"
)


def _expected_hotspot_threshold_status(family_row: dict[str, object]) -> str:
    thresholds = family_row["thresholds"]
    assert isinstance(thresholds, dict)

    measured_module_count = int(family_row["measured_module_count"])
    covered_module_count = int(family_row["covered_module_count"])
    unexpected_unmeasured_module_count = int(
        family_row["unexpected_unmeasured_module_count"]
    )
    covered_line_percent = family_row["covered_line_percent"]

    threshold_status = "pass"
    if measured_module_count < int(
        thresholds.get("min_measured_module_count", measured_module_count)
    ):
        threshold_status = "fail"
    if unexpected_unmeasured_module_count > int(
        thresholds.get(
            "max_unmeasured_module_count",
            unexpected_unmeasured_module_count,
        )
    ):
        threshold_status = "fail"
    if covered_module_count < int(
        thresholds.get("min_covered_module_count", covered_module_count)
    ):
        threshold_status = "fail"

    min_covered_line_percent = thresholds.get("min_covered_line_percent")
    if (
        isinstance(min_covered_line_percent, int | float)
        and covered_line_percent is not None
        and float(covered_line_percent) < float(min_covered_line_percent)
    ):
        threshold_status = "fail"
    return threshold_status


def _skip_if_source_tree_is_dirty() -> None:
    """Committed inventory assertions require a clean source tree."""
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--", "src/bioetl"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip(
            "Committed module-coverage inventory dirty-tree guard is not "
            "authoritative on this checkout."
        )
    dirty_entries = [
        line.strip() for line in result.stdout.splitlines() if line.strip()
    ]
    if dirty_entries:
        pytest.skip(
            "Committed module-coverage inventory is only authoritative for a clean "
            "src/bioetl tree. Dirty entries: " + ", ".join(dirty_entries[:20])
        )


def _write_minimal_coverage_xml(
    path: Path,
    *,
    repo_root: Path,
    hits: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    source_root = repo_root.as_posix()
    path.write_text(
        '<?xml version="1.0" ?>\n'
        "<coverage>\n"
        "  <sources>\n"
        f"    <source>{source_root}</source>\n"
        "  </sources>\n"
        "  <packages>\n"
        '    <package name="bioetl">\n'
        "      <classes>\n"
        '        <class name="bioetl.example" filename="src/bioetl/example.py">\n'
        "          <lines>\n"
        f'            <line number="1" hits="{hits}" />\n'
        f'            <line number="2" hits="{hits}" />\n'
        "          </lines>\n"
        "        </class>\n"
        "      </classes>\n"
        "    </package>\n"
        "  </packages>\n"
        "</coverage>\n",
        encoding="utf-8",
    )


@pytest.mark.architecture
def test_module_coverage_inventory_is_committed_and_shape_is_stable() -> None:
    assert INVENTORY_PATH.exists()
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

    assert committed["schema_version"] == 1
    assert committed["generated_by"].endswith("report_module_coverage_inventory.py")
    assert committed["coverage_xml_path"] == "reports/coverage/coverage.xml"
    assert committed["measurement_mode"] == "coverage_xml"
    assert (
        isinstance(committed["coverage_xml_sha256"], str)
        and committed["coverage_xml_sha256"]
    )
    assert committed["canonical_coverage_lane"] == "coverage-verify"
    assert isinstance(committed["modules"], list) and committed["modules"]
    assert committed["rows"] == committed["modules"]
    assert committed["summary"]["coverage_xml_present"] is True
    assert isinstance(committed["summary"]["unmeasured_module_count"], int)
    assert isinstance(committed["summary"]["unmeasured_modules"], list)
    assert committed["summary"]["unmeasured_module_count"] == len(
        committed["summary"]["unmeasured_modules"]
    )
    for unmeasured in committed["summary"]["unmeasured_modules"]:
        assert str(unmeasured["module"]).startswith("bioetl")
        assert str(unmeasured["path"]).startswith("src/bioetl/")
        assert unmeasured["reason"] == "coverage_xml_has_no_class_entry"
    hotspot_family_coverage = committed["summary"]["hotspot_family_coverage"]
    assert isinstance(hotspot_family_coverage, dict) and hotspot_family_coverage

    for row in committed["modules"]:
        assert row["module"].startswith("bioetl")
        assert str(row["path"]).startswith("src/bioetl/")
        assert isinstance(row["source_lines"], int) and row["source_lines"] >= 0
        assert row["coverage_status"] in {
            "coverage_xml_missing",
            "unmeasured",
            "no_executable_lines",
            "uncovered",
            "fully_covered",
            "partially_covered",
        }
        coverage_percent = row["coverage_percent"]
        if coverage_percent is not None:
            assert 0.0 <= coverage_percent <= 100.0

    for family_row in hotspot_family_coverage.values():
        assert isinstance(family_row["module_count"], int)
        assert isinstance(family_row["measured_module_count"], int)
        assert isinstance(family_row["covered_module_count"], int)
        assert isinstance(family_row["unmeasured_module_count"], int)
        assert isinstance(family_row["allowlisted_unmeasured_module_count"], int)
        assert isinstance(family_row["unexpected_unmeasured_module_count"], int)
        assert isinstance(family_row["allowlisted_unmeasured_modules"], list)
        assert isinstance(family_row["unexpected_unmeasured_modules"], list)
        assert isinstance(family_row["measured_percent"], float)
        assert 0.0 <= family_row["measured_percent"] <= 100.0
        assert isinstance(family_row["status_counts"], dict)
        assert isinstance(family_row["thresholds"], dict)
        assert family_row["threshold_status"] in {"pass", "fail"}
        coverage_percent_min = family_row["coverage_percent_min"]
        coverage_percent_avg = family_row["coverage_percent_avg"]
        covered_line_percent = family_row["covered_line_percent"]
        if coverage_percent_min is not None:
            assert 0.0 <= coverage_percent_min <= 100.0
        if coverage_percent_avg is not None:
            assert 0.0 <= coverage_percent_avg <= 100.0
        if covered_line_percent is not None:
            assert 0.0 <= covered_line_percent <= 100.0
        assert family_row["module_count"] >= family_row["measured_module_count"]
        assert family_row["module_count"] >= family_row["covered_module_count"]
        assert family_row["module_count"] >= family_row["unmeasured_module_count"]
        assert family_row["unmeasured_module_count"] == (
            family_row["allowlisted_unmeasured_module_count"]
            + family_row["unexpected_unmeasured_module_count"]
        )


@pytest.mark.architecture
def test_module_coverage_inventory_covers_every_source_module() -> None:
    _skip_if_source_tree_is_dirty()
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    inventory_paths = {str(row["path"]) for row in committed["modules"]}
    expected_paths = {
        path.relative_to(ROOT).as_posix() for path in _iter_source_modules(ROOT)
    }

    assert inventory_paths == expected_paths


@pytest.mark.architecture
def test_module_coverage_inventory_source_tree_hash_is_current() -> None:
    # Skip on WSL and Windows due to filesystem performance causing hash computation timeout
    import sys

    if sys.platform.startswith("win"):
        pytest.skip("Skipped on Windows due to filesystem performance")
    try:
        with open("/proc/version") as f:
            if "microsoft" in f.read().lower():
                pytest.skip("Skipped on WSL due to filesystem performance")
    except OSError:
        pass

    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    assert committed["source_tree_sha256"] == compute_source_tree_sha256(repo_root=ROOT)


@pytest.mark.architecture
def test_module_coverage_inventory_check_fails_for_stale_source_tree_hash(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    source_root = repo_root / "src" / "bioetl"
    quality_root = repo_root / "configs" / "quality"
    source_root.mkdir(parents=True)
    quality_root.mkdir(parents=True)
    (repo_root / "reports" / "quality").mkdir(parents=True)

    shutil.copy2(SCORECARD_PATH, quality_root / SCORECARD_PATH.name)
    shutil.copy2(GATES_PATH, quality_root / GATES_PATH.name)

    module_path = source_root / "example.py"
    module_path.write_text(
        "def example() -> int:\n    return 1\n",
        encoding="utf-8",
    )
    json_out = repo_root / "reports" / "quality" / "module-coverage-inventory.json"
    coverage_xml = repo_root / "reports" / "coverage" / "coverage.xml"

    create_exit = module_coverage_inventory_main(
        [
            "--repo-root",
            str(repo_root),
            "--coverage-xml",
            str(coverage_xml),
            "--json-out",
            str(json_out),
            "--allow-missing-coverage-xml",
            "--snapshot-date",
            "2026-06-19",
        ]
    )
    assert create_exit == 0

    module_path.write_text(
        "def example() -> int:\n    value = 2\n    return value\n",
        encoding="utf-8",
    )

    check_exit = module_coverage_inventory_main(
        [
            "--repo-root",
            str(repo_root),
            "--coverage-xml",
            str(coverage_xml),
            "--json-out",
            str(json_out),
            "--allow-missing-coverage-xml",
            "--check",
        ]
    )
    assert check_exit == 1


@pytest.mark.architecture
def test_allow_missing_coverage_xml_preserves_existing_inventory_rows(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    source_root = repo_root / "src" / "bioetl"
    quality_root = repo_root / "configs" / "quality"
    source_root.mkdir(parents=True)
    quality_root.mkdir(parents=True)
    (repo_root / "reports" / "quality").mkdir(parents=True)

    shutil.copy2(SCORECARD_PATH, quality_root / SCORECARD_PATH.name)
    shutil.copy2(GATES_PATH, quality_root / GATES_PATH.name)

    (source_root / "example.py").write_text(
        "def example() -> int:\n    return 1\n",
        encoding="utf-8",
    )
    json_out = repo_root / "reports" / "quality" / "module-coverage-inventory.json"
    coverage_xml = repo_root / "reports" / "coverage" / "coverage.xml"
    _write_minimal_coverage_xml(coverage_xml, repo_root=repo_root, hits=1)

    create_exit = module_coverage_inventory_main(
        [
            "--repo-root",
            str(repo_root),
            "--coverage-xml",
            str(coverage_xml),
            "--json-out",
            str(json_out),
            "--snapshot-date",
            "2026-06-19",
        ]
    )
    assert create_exit == 0
    committed = json.loads(json_out.read_text(encoding="utf-8"))
    committed_row = committed["modules"][0]
    assert committed_row["coverage_status"] == "fully_covered"
    assert committed_row["coverage_percent"] == 100.0

    _write_minimal_coverage_xml(coverage_xml, repo_root=repo_root, hits=0)
    refresh_exit = module_coverage_inventory_main(
        [
            "--repo-root",
            str(repo_root),
            "--coverage-xml",
            str(coverage_xml),
            "--json-out",
            str(json_out),
            "--allow-missing-coverage-xml",
        ]
    )
    assert refresh_exit == 0

    refreshed = json.loads(json_out.read_text(encoding="utf-8"))
    assert refreshed["coverage_xml_sha256"] == committed["coverage_xml_sha256"]
    assert refreshed["measurement_mode"] == "coverage_xml"
    assert refreshed["modules"] == committed["modules"]


@pytest.mark.architecture
def test_declaration_only_modules_with_zero_hit_xml_are_not_uncovered(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    source_root = repo_root / "src" / "bioetl" / "infrastructure" / "compat"
    quality_root = repo_root / "configs" / "quality"
    source_root.mkdir(parents=True)
    quality_root.mkdir(parents=True)
    (repo_root / "reports" / "quality").mkdir(parents=True)

    shutil.copy2(SCORECARD_PATH, quality_root / SCORECARD_PATH.name)
    shutil.copy2(GATES_PATH, quality_root / GATES_PATH.name)

    (source_root / "__init__.py").write_text(
        '"""Infrastructure compatibility namespace."""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "__all__: list[str] = []\n",
        encoding="utf-8",
    )
    json_out = repo_root / "reports" / "quality" / "module-coverage-inventory.json"
    coverage_xml = repo_root / "reports" / "coverage" / "coverage.xml"
    coverage_xml.parent.mkdir(parents=True)
    coverage_xml.write_text(
        '<?xml version="1.0" ?>\n'
        "<coverage>\n"
        "  <sources>\n"
        f"    <source>{repo_root.as_posix()}</source>\n"
        "  </sources>\n"
        "  <packages>\n"
        '    <package name="bioetl.infrastructure.compat">\n'
        "      <classes>\n"
        '        <class name="__init__.py" filename="src/bioetl/infrastructure/compat/__init__.py">\n'
        "          <lines>\n"
        '            <line number="5" hits="0" />\n'
        "          </lines>\n"
        "        </class>\n"
        "      </classes>\n"
        "    </package>\n"
        "  </packages>\n"
        "</coverage>\n",
        encoding="utf-8",
    )

    create_exit = module_coverage_inventory_main(
        [
            "--repo-root",
            str(repo_root),
            "--coverage-xml",
            str(coverage_xml),
            "--json-out",
            str(json_out),
            "--snapshot-date",
            "2026-06-19",
        ]
    )
    assert create_exit == 0

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["summary"]["uncovered_module_count"] == 0
    assert payload["modules"][0]["coverage_status"] == "no_executable_lines"
    assert payload["modules"][0]["executable_lines"] == 0


@pytest.mark.architecture
def test_existing_inventory_refresh_preserves_rows_unless_xml_refresh_is_explicit(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    source_root = repo_root / "src" / "bioetl"
    quality_root = repo_root / "configs" / "quality"
    source_root.mkdir(parents=True)
    quality_root.mkdir(parents=True)
    (repo_root / "reports" / "quality").mkdir(parents=True)

    shutil.copy2(SCORECARD_PATH, quality_root / SCORECARD_PATH.name)
    shutil.copy2(GATES_PATH, quality_root / GATES_PATH.name)

    (source_root / "example.py").write_text(
        "def example() -> int:\n    return 1\n",
        encoding="utf-8",
    )
    json_out = repo_root / "reports" / "quality" / "module-coverage-inventory.json"
    coverage_xml = repo_root / "reports" / "coverage" / "coverage.xml"
    _write_minimal_coverage_xml(coverage_xml, repo_root=repo_root, hits=1)

    create_exit = module_coverage_inventory_main(
        [
            "--repo-root",
            str(repo_root),
            "--coverage-xml",
            str(coverage_xml),
            "--json-out",
            str(json_out),
            "--snapshot-date",
            "2026-06-19",
        ]
    )
    assert create_exit == 0
    committed = json.loads(json_out.read_text(encoding="utf-8"))

    _write_minimal_coverage_xml(coverage_xml, repo_root=repo_root, hits=0)
    safe_refresh_exit = module_coverage_inventory_main(
        [
            "--repo-root",
            str(repo_root),
            "--coverage-xml",
            str(coverage_xml),
            "--json-out",
            str(json_out),
        ]
    )
    assert safe_refresh_exit == 0
    safe_refreshed = json.loads(json_out.read_text(encoding="utf-8"))
    assert safe_refreshed["coverage_xml_sha256"] == committed["coverage_xml_sha256"]
    assert safe_refreshed["modules"] == committed["modules"]

    xml_refresh_exit = module_coverage_inventory_main(
        [
            "--repo-root",
            str(repo_root),
            "--coverage-xml",
            str(coverage_xml),
            "--json-out",
            str(json_out),
            "--refresh-from-coverage-xml",
        ]
    )
    assert xml_refresh_exit == 0
    xml_refreshed = json.loads(json_out.read_text(encoding="utf-8"))
    assert xml_refreshed["coverage_xml_sha256"] != committed["coverage_xml_sha256"]
    assert xml_refreshed["modules"][0]["coverage_status"] == "uncovered"


@pytest.mark.architecture
def test_existing_inventory_refresh_reconciles_source_module_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    source_root = repo_root / "src" / "bioetl"
    quality_root = repo_root / "configs" / "quality"
    source_root.mkdir(parents=True)
    quality_root.mkdir(parents=True)
    (repo_root / "reports" / "quality").mkdir(parents=True)

    shutil.copy2(SCORECARD_PATH, quality_root / SCORECARD_PATH.name)
    shutil.copy2(GATES_PATH, quality_root / GATES_PATH.name)

    (source_root / "example.py").write_text(
        "def example() -> int:\n    return 1\n",
        encoding="utf-8",
    )
    example_path = source_root / "example.py"
    json_out = repo_root / "reports" / "quality" / "module-coverage-inventory.json"
    coverage_xml = repo_root / "reports" / "coverage" / "coverage.xml"
    _write_minimal_coverage_xml(coverage_xml, repo_root=repo_root, hits=1)
    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory._iter_source_modules",
        lambda repo_root: [example_path],
    )

    create_exit = module_coverage_inventory_main(
        [
            "--repo-root",
            str(repo_root),
            "--coverage-xml",
            str(coverage_xml),
            "--json-out",
            str(json_out),
            "--snapshot-date",
            "2026-06-19",
        ]
    )
    assert create_exit == 0

    (source_root / "added.py").write_text(
        "def added() -> int:\n    return 2\n",
        encoding="utf-8",
    )
    added_path = source_root / "added.py"
    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory._iter_source_modules",
        lambda repo_root: [added_path, example_path],
    )
    refresh_exit = module_coverage_inventory_main(
        [
            "--repo-root",
            str(repo_root),
            "--coverage-xml",
            str(coverage_xml),
            "--json-out",
            str(json_out),
        ]
    )
    assert refresh_exit == 0

    refreshed = json.loads(json_out.read_text(encoding="utf-8"))
    paths = {str(row["path"]) for row in refreshed["modules"]}
    assert paths == {"src/bioetl/added.py", "src/bioetl/example.py"}
    added_row = next(
        row for row in refreshed["modules"] if row["path"] == "src/bioetl/added.py"
    )
    assert added_row["coverage_status"] == "no_executable_lines"


@pytest.mark.architecture
def test_module_coverage_inventory_reports_measured_hotspot_family_evidence() -> None:
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    hotspot_family_coverage = committed["summary"]["hotspot_family_coverage"]
    assert isinstance(hotspot_family_coverage, dict)

    for family_name in (
        "application_core",
        "composition_bootstrap_runtime",
        "composition_factories_pipeline",
        "application_services_control_plane",
        "composition_runtime_builders",
    ):
        family_row = hotspot_family_coverage.get(family_name)
        assert isinstance(family_row, dict), family_name
        assert family_row["module_count"] > 0, family_name
        assert family_row["unexpected_unmeasured_module_count"] == 0, family_name
        assert family_row["unexpected_unmeasured_modules"] == [], family_name
        assert (
            family_row["measured_module_count"]
            + family_row["allowlisted_unmeasured_module_count"]
            == family_row["module_count"]
        ), family_name
        assert family_row["threshold_status"] == _expected_hotspot_threshold_status(
            family_row
        ), family_name


@pytest.mark.architecture
def test_retained_entrypoint_modules_have_measured_coverage() -> None:
    """Retained module entrypoints must not silently remain coverage-unmeasured."""
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    rows_by_path = {str(row["path"]): row for row in committed["modules"]}

    retained_entrypoint_paths = {
        "src/bioetl/__main__.py",
        "src/bioetl/interfaces/cli/__main__.py",
    }
    missing = sorted(retained_entrypoint_paths - set(rows_by_path))
    assert not missing, (
        "Retained entrypoint modules must be present in module coverage inventory:\n"
        + "\n".join(missing)
    )

    unmeasured = [
        path
        for path in sorted(retained_entrypoint_paths)
        if rows_by_path[path]["coverage_status"] == "unmeasured"
    ]
    assert not unmeasured, (
        "Retained entrypoint modules must be measured by coverage-verify or "
        "explicitly owner-exempted before they can remain retained:\n"
        + "\n".join(unmeasured)
    )


@pytest.mark.architecture
def test_hotspot_refactor_targets_have_authoritative_module_coverage_gates() -> None:
    """Hotspot refactor families must have an explicit module-level coverage gate."""
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    hotspot_family_coverage = committed["summary"]["hotspot_family_coverage"]
    scorecard = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    gate = scorecard["hotspot_family_coverage_thresholds"]

    assert gate["mode"] == "fail-fast"
    assert gate["enforcement_issue"] == "#5036"
    assert gate["authoritative_for_hotspot_refactor_readiness"] is True
    assert gate["authoritative_artifact"] == (
        "reports/quality/module-coverage-inventory.json"
    )
    assert gate["canonical_lane"] == "coverage-verify"
    assert isinstance(gate["readiness_policy"], str) and gate["readiness_policy"]

    gated_families = gate["families"]
    assert set(gated_families) == set(hotspot_family_coverage)
    for family_name, thresholds in gated_families.items():
        family_row = hotspot_family_coverage[family_name]
        assert family_row["thresholds"] == thresholds
        assert family_row["threshold_status"] == _expected_hotspot_threshold_status(
            family_row
        ), family_name


@pytest.mark.architecture
def test_issue_5376_coverage_tail_closeout_matches_live_inventory() -> None:
    """#5376 preserves historical shard evidence while exposing current regressions."""
    skip_if_module_coverage_inventory_is_dirty(root=ROOT, inventory_path=INVENTORY_PATH)
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    closeout = json.loads(COVERAGE_TAIL_CLOSEOUT_PATH.read_text(encoding="utf-8"))

    below_85 = [
        row
        for row in committed["modules"]
        if row["coverage_percent"] is not None and row["coverage_percent"] < 85
    ]
    below_85_paths = {row["path"] for row in below_85}
    historical_delta = closeout["historical_coverage_inventory_delta"]
    current_live = closeout["current_live_metrics"]
    delta = int(historical_delta["after_below_85_module_count"]) - int(
        historical_delta["before_below_85_module_count"]
    )
    tracked_path = closeout["removed_low_tail_module"]["path"]
    tracked_row = next(
        row for row in committed["modules"] if row["path"] == tracked_path
    )

    assert closeout["issue"]["number"] == 5376
    assert historical_delta["after_below_85_module_count"] == 104
    assert historical_delta["below_85_module_count_delta"] == delta
    assert delta < 0
    assert current_live["below_85_module_count"] == len(below_85)
    assert (
        current_live["uncovered_module_count"]
        == committed["summary"]["uncovered_module_count"]
    )
    assert (
        current_live["unmeasured_module_count"]
        == committed["summary"]["unmeasured_module_count"]
    )
    assert (
        tracked_row["coverage_percent"]
        == current_live["tracked_module_coverage_percent"]
    )
    assert tracked_row["coverage_status"] == current_live["tracked_module_status"]
    assert closeout["closeout"]["status"] == "regressed_after_closeout"
    assert tracked_path not in below_85_paths


@pytest.mark.architecture
def test_module_coverage_inventory_check_requires_coverage_xml_by_default(
    tmp_path: Path,
) -> None:
    missing_coverage_xml = tmp_path / "coverage.xml"
    artifact = tmp_path / "module-coverage-inventory.json"
    artifact.write_text("{}", encoding="utf-8")

    rc = module_coverage_inventory_main(
        [
            "--repo-root",
            str(ROOT),
            "--coverage-xml",
            str(missing_coverage_xml),
            "--json-out",
            str(artifact),
            "--check",
        ]
    )

    assert rc == 1


@pytest.mark.architecture
def test_module_coverage_inventory_generation_requires_coverage_xml_by_default(
    tmp_path: Path,
) -> None:
    missing_coverage_xml = tmp_path / "coverage.xml"
    artifact = tmp_path / "module-coverage-inventory.json"

    rc = module_coverage_inventory_main(
        [
            "--repo-root",
            str(ROOT),
            "--coverage-xml",
            str(missing_coverage_xml),
            "--json-out",
            str(artifact),
        ]
    )

    assert rc == 1
    assert not artifact.exists()


@pytest.mark.architecture
def test_coverage_verify_workflow_generates_module_coverage_inventory() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "coverage xml -o reports/coverage/coverage.xml" in workflow
    assert "check-branch-coverage" in workflow
    assert "report-module-coverage" in workflow
    assert "reports/quality/module-coverage-inventory.json" in workflow
    assert "--refresh-from-coverage-xml" in workflow


@pytest.mark.architecture
def test_module_coverage_gates_policy_is_committed() -> None:
    assert GATES_PATH.exists()
    gates = yaml.safe_load(GATES_PATH.read_text(encoding="utf-8"))
    assert gates["schema_version"] == 1
    assert gates["enforcement"]["default_mode"] == "block-regression"
    assert gates["branch_coverage"]["measurement"] == "enabled"
    assert gates["branch_coverage"]["policy"] == "blocking"
    assert gates["branch_coverage"]["hard_gate_threshold_percent"] == 85
    assert "check-branch-coverage" in gates["branch_coverage"]["enforcement_command"]
    assert (
        gates["branch_coverage"]["source"]
        == "reports/coverage/coverage.xml#branch-rate"
    )
    assert "aggregates_and_contracts" in gates["tiers"]
    assert gates["tiers"]["aggregates_and_contracts"]["line_min_percent"] == 95


@pytest.mark.architecture
def test_module_coverage_tail_targets_are_ranked_and_owner_anchored() -> None:
    gates = yaml.safe_load(GATES_PATH.read_text(encoding="utf-8"))
    targets = gates["coverage_tail"]["ranked_targets"]

    assert [target["rank"] for target in targets] == list(range(1, len(targets) + 1))
    first_slice = targets[0]
    assert first_slice["path"] == "src/bioetl/application/core/wiring/__init__.py"
    assert first_slice["status"] == "focused_owner_tests_added"
    assert first_slice["owner_tests"] == [
        "tests/unit/application/core/test_wiring_api_facades.py"
    ]
    for target in targets:
        assert Path(target["path"]).exists()


@pytest.mark.architecture
def test_test_matrix_declares_module_coverage_inventory_contract() -> None:
    matrix = load_matrix()
    inventory = matrix["module_coverage_inventory"]
    coverage_lane = matrix["test_lanes"]["lanes"]["coverage-verify"]

    assert inventory["enabled"] is True
    assert inventory["canonical_lane"] == "coverage-verify"
    assert inventory["generator"] == (
        "scripts/engineering/qa/report_module_coverage_inventory.py"
    )
    assert inventory["command"] == (
        "python -m scripts.engineering.qa report-module-coverage "
        "--refresh-from-coverage-xml"
    )
    assert inventory["authoritative_status_source"] == "live_ci_coverage_verify"
    assert (
        inventory["committed_artifact_refresh_policy"]
        == "green_coverage_verify_run_only"
    )
    assert inventory["artifact"] == "reports/quality/module-coverage-inventory.json"
    assert inventory["coverage_xml"] == "reports/coverage/coverage.xml"
    assert inventory["canonical_generation_requires_coverage_xml"] is True
    per_module_gates = inventory["per_module_gates"]
    assert per_module_gates["enabled"] is True
    assert per_module_gates["enforcement_mode"] == "block-regression"
    assert per_module_gates["policy"] == "configs/quality/module_coverage_gates.yaml"
    assert (
        coverage_lane["expected_artifacts"]["module_coverage_inventory"]
        == (inventory["artifact"])
    )
