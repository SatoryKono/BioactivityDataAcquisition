from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa.check_branch_coverage import (
    evaluate_branch_coverage,
    main,
)

pytestmark = pytest.mark.unit


def _write_coverage_xml(
    path: Path,
    *,
    branches_valid: int,
    branches_covered: int,
) -> None:
    path.write_text(
        (
            '<?xml version="1.0" ?>\n'
            '<coverage version="7.14.1" '
            'lines-valid="10" lines-covered="10" line-rate="1" '
            f'branches-valid="{branches_valid}" '
            f'branches-covered="{branches_covered}" '
            'branch-rate="0.0" complexity="0" />\n'
        ),
        encoding="utf-8",
    )


def test_branch_coverage_passes_at_threshold_using_counts(tmp_path: Path) -> None:
    coverage_xml = tmp_path / "coverage.xml"
    _write_coverage_xml(coverage_xml, branches_valid=20_256, branches_covered=17_218)

    result = evaluate_branch_coverage(
        coverage_xml,
        min_percent=85,
        repo_root=tmp_path,
    )

    assert result.status == "pass"
    assert result.branch_rate_percent == 85.002
    assert result.required_branch_covered == 17_218
    assert result.threshold_margin == 0


def test_branch_coverage_fails_below_threshold(tmp_path: Path) -> None:
    coverage_xml = tmp_path / "coverage.xml"
    _write_coverage_xml(coverage_xml, branches_valid=100, branches_covered=84)

    result = evaluate_branch_coverage(
        coverage_xml,
        min_percent=85,
        repo_root=tmp_path,
    )

    assert result.status == "fail"
    assert result.branch_rate_percent == 84.0
    assert result.required_branch_covered == 85
    assert result.threshold_margin == -1


def test_branch_coverage_rejects_missing_branch_measurement(tmp_path: Path) -> None:
    coverage_xml = tmp_path / "coverage.xml"
    _write_coverage_xml(coverage_xml, branches_valid=0, branches_covered=0)

    with pytest.raises(ValueError, match="does not contain branch measurement"):
        evaluate_branch_coverage(coverage_xml, repo_root=tmp_path)


def test_branch_coverage_cli_writes_json_evidence(tmp_path: Path) -> None:
    coverage_xml = tmp_path / "coverage.xml"
    json_out = tmp_path / "evidence.json"
    _write_coverage_xml(coverage_xml, branches_valid=10, branches_covered=9)

    rc = main(
        [
            "--coverage-xml",
            str(coverage_xml),
            "--min-percent",
            "85",
            "--json-out",
            str(json_out),
        ]
    )

    assert rc == 0
    assert '"branch_rate_percent": 90.0' in json_out.read_text(encoding="utf-8")
