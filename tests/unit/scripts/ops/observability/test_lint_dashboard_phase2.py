"""Unit coverage for the Phase-2 Grafana dashboard linter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana import lint_dashboard_phase2 as lint
from scripts.ops.observability.grafana.apply_phase25_srs_prr_budget import (
    _assert_donor_jsonata_balanced,
    _jsonata_brackets_balanced,
    _OV_DONOR,
    _DQ_DONOR,
    _INC_DONOR,
)


pytestmark = pytest.mark.unit


def test_phase2_linter_passes_on_provisioned_dashboards() -> None:
    assert lint.main(["--profile", "phase2"]) == 0


def test_phase4_linter_passes_on_provisioned_dashboards() -> None:
    # Default profile is phase4 (CI/unit gate for full acceptance checks).
    assert lint.main([]) == 0
    assert lint.main(["--profile", "phase4"]) == 0


def test_dead_rename_keys_use_exclude_not_index_membership() -> None:
    """indexByName is order-only; excluded fields are the dead-rename signal."""
    assert lint._dead_rename_keys(
        {
            "id": "organize",
            "options": {
                "indexByName": {"kept": 0},
                "excludeByName": {"hidden": True},
                "renameByName": {
                    "kept": "Kept",
                    "unordered": "Still Valid",
                    "hidden": "Gone",
                },
            },
        }
    ) == ["hidden"]
    assert (
        lint._dead_rename_keys(
            {
                "id": "organize",
                "options": {
                    "indexByName": {"a": 0},
                    "renameByName": {"a": "A", "b": "B"},
                },
            }
        )
        == []
    )


def test_phase2_linter_flags_missing_nav_and_index_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dash = {
        "uid": "bioetl-overview-v2",
        "panels": [
            {
                "id": 42,
                "type": "table",
                "transformations": [
                    {
                        "id": "organize",
                        "options": {"indexByName": {"a": 0, "b": 0}},
                    }
                ],
            }
        ],
    }
    path = tmp_path / "bioetl-overview-v2.json"
    path.write_text(json.dumps(dash), encoding="utf-8")
    monkeypatch.setattr(lint, "DASH_DIR", tmp_path)
    monkeypatch.setattr(lint, "FILES", ("bioetl-overview-v2.json",))
    findings = lint.lint_dashboard(path)
    assert any("missing navigation panel id=1000" in item for item in findings)
    assert any("indexByName collision" in item for item in findings)


def test_nav_linter_checks_real_elements_and_destinations() -> None:
    content = (
        '<div class="bioetl-nav">'
        '<a class="bioetl-nav-link" style="width:19.5%" '
        'href="/d/bioetl-run-explorer-v1/run-explorer">Run Explorer</a>'
        '<a class="bioetl-nav-link" style="width:19.5%" '
        'href="/d/bioetl-control-plane-v1/1-trust">Replay Readiness</a>'
        '<span class="bioetl-nav-current" style="width:19.5%">Run Overview</span>'
        '<a class="bioetl-nav-link" style="width:19.5%" '
        'href="/d/bioetl-dq-v2/5-data-quality">Data Quality</a>'
        '<a class="bioetl-nav-link" style="width:19.5%" '
        'href="/d/bioetl-incident-v1/6-incident-workspace">'
        "Incident Workspace</a></div>"
    )
    assert lint._nav_content_findings("fixture.json", content) == []

    fake_content = "19.5% " * 5 + " ".join(lint._NAV_CHIP_TITLES)
    findings = lint._nav_content_findings("fixture.json", fake_content)
    assert any("expected five navigation elements" in item for item in findings)


def test_value_mapping_status_text_is_recognized() -> None:
    assert lint._mapping_has_status_token(
        {"type": "value", "options": {"0": {"text": "UNKNOWN"}}}
    )


def test_parse_dashboard_view_panel_when_not_first_query_param() -> None:
    uid, panel = lint.parse_dashboard_view_panel(
        "/d/bioetl-dq-v2/5-data-quality"
        "?${workflow:queryparam}&${pipeline:queryparam}"
        "&viewPanel=9460&${__url_time_range}"
    )
    assert uid == "bioetl-dq-v2"
    assert panel == 9460


def test_parse_dashboard_view_panel_first_param_and_amp_entities() -> None:
    uid, panel = lint.parse_dashboard_view_panel(
        "/d/bioetl-overview-v2/2-overview?viewPanel=9300&amp;var-run_id=abc"
    )
    assert uid == "bioetl-overview-v2"
    assert panel == 9300


def test_lint_flags_broken_view_panel_mid_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dash = {
        "uid": "bioetl-overview-v2",
        "panels": [
            {
                "id": 1000,
                "type": "text",
                "options": {
                    "content": (
                        '<div class="bioetl-nav">'
                        '<span class="bioetl-nav-current">x</span>'
                        "19.5% 19.5% 19.5% 19.5% 19.5%"
                        "Run Explorer Replay Readiness Run Overview "
                        "Data Quality Incident Workspace"
                        "</div>"
                    )
                },
                "links": [
                    {
                        "title": "broken mid-query",
                        "url": (
                            "/d/bioetl-dq-v2/5-data-quality"
                            "?var-pipeline=chembl&viewPanel=99999"
                        ),
                    }
                ],
            }
        ],
    }
    path = tmp_path / "bioetl-overview-v2.json"
    path.write_text(json.dumps(dash), encoding="utf-8")
    dq = {
        "uid": "bioetl-dq-v2",
        "panels": [{"id": 9460, "type": "table"}],
    }
    (tmp_path / "bioetl-dq-v2.json").write_text(json.dumps(dq), encoding="utf-8")
    monkeypatch.setattr(lint, "DASH_DIR", tmp_path)
    monkeypatch.setattr(
        lint,
        "FILES",
        ("bioetl-overview-v2.json", "bioetl-dq-v2.json"),
    )
    monkeypatch.setattr(
        lint,
        "UID_BY_FILE",
        {
            "bioetl-overview-v2.json": "bioetl-overview-v2",
            "bioetl-dq-v2.json": "bioetl-dq-v2",
        },
    )
    findings = lint.lint_dashboard(path)
    assert any("broken viewPanel=99999 on bioetl-dq-v2" in item for item in findings)


def test_phase25_donor_jsonata_brackets_are_balanced() -> None:
    _assert_donor_jsonata_balanced()
    assert _jsonata_brackets_balanced(_OV_DONOR)
    assert _jsonata_brackets_balanced(_DQ_DONOR)
    assert _jsonata_brackets_balanced(_INC_DONOR)


def test_nav_lint_requires_real_chip_elements() -> None:
    findings = lint._nav_content_findings(
        "bioetl-overview-v2.json",
        (
            '<div class="bioetl-nav">'
            '<span class="bioetl-nav-current">x</span>'
            "19.5% 19.5% 19.5% 19.5% 19.5%"
            "Run Explorer Replay Readiness Run Overview "
            "Data Quality Incident Workspace"
            "</div>"
        ),
    )
    assert any("expected five navigation elements" in item for item in findings)


def test_mapping_value_text_tokens_count_as_status() -> None:
    assert lint._mapping_has_status_token(
        {
            "type": "value",
            "options": {
                "0": {"text": "UNKNOWN"},
                "1": {"text": "OK"},
            },
        }
    )
