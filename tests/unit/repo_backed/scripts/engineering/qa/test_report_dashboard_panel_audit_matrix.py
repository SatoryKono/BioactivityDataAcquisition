from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.engineering.qa import report_dashboard_panel_audit_matrix as subject

pytestmark = pytest.mark.repo_backed


def test_shipped_dashboard_panel_matrix_matches_baseline(tmp_path: Path) -> None:
    output = tmp_path / "panel-audit.csv"

    assert subject.main(["--check", "--output", str(output)]) == 0

    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == subject.EXPECTED_PANEL_COUNT
    assert {row["dashboard_uid"] for row in rows} == {
        "bioetl-control-plane-v1",
        "bioetl-dq-v2",
        "bioetl-incident-v1",
        "bioetl-overview-v2",
        "bioetl-provider-health-v2",
        "bioetl-run-explorer-v1",
        "bioetl-runtime",
    }
    keys = [(row["dashboard_uid"], row["panel_id"]) for row in rows]
    assert len(keys) == len(set(keys))


def test_dashboard_panel_matrix_check_fails_closed_on_count_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        subject,
        "_collect_rows",
        lambda: [{}] * (subject.EXPECTED_PANEL_COUNT - 1),
    )

    assert subject.main(["--check", "--output", str(tmp_path / "out.csv")]) == 1
    assert "panel count mismatch" in capsys.readouterr().err
