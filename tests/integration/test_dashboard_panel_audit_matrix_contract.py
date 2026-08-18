from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from scripts.engineering.qa import report_dashboard_panel_audit_matrix as subject

pytestmark = pytest.mark.integration


def test_shipped_dashboard_panel_matrix_matches_baseline(tmp_path: Path) -> None:
    output = tmp_path / "panel-audit.csv"

    assert subject.main(["--check", "--output", str(output)]) == 0

    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == subject.EXPECTED_PANEL_COUNT
    assert subject.EXPECTED_PANEL_COUNT == subject.expected_panel_count_from_inventory()
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
    contract = yaml.safe_load(subject.CONTENT_CONTRACT.read_text(encoding="utf-8"))
    assert isinstance(contract, dict)
    dashboards = contract.get("dashboards")
    assert isinstance(dashboards, dict)
    content_records = {
        (uid, panel_id)
        for uid, dashboard in dashboards.items()
        if isinstance(uid, str) and isinstance(dashboard, dict)
        for panel_id, record in dashboard.get("panels", {}).items()
        if isinstance(panel_id, str) and isinstance(record, dict)
    }
    assert content_records
    covered_rows = {
        (row["dashboard_uid"], row["panel_id"]): row
        for row in rows
        if row["content_contract_status"] == "covered"
    }
    assert set(covered_rows) == content_records
    for row in covered_rows.values():
        assert row["content_role"]
        assert row["content_tier"] in {"1", "2", "3", "4"}
        assert row["content_scope"]
        assert row["content_state_model"]
        assert int(row["fixture_case_count"]) > 0
        assert int(row["render_profile_count"]) > 0


def test_dashboard_panel_matrix_check_fails_closed_when_contract_cannot_load(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        subject,
        "_content_contract_by_panel",
        lambda: (_ for _ in ()).throw(ValueError("invalid contract")),
    )

    assert subject.main(["--check", "--output", str(tmp_path / "out.csv")]) == 1
    assert "panel audit matrix error: invalid contract" in capsys.readouterr().err


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
