"""Unit coverage for the Phase-2 Grafana dashboard linter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana import lint_dashboard_phase2 as lint
from scripts.ops.observability.grafana.apply_phase25_srs_prr_budget import (
    _assert_donor_jsonata_balanced,
    _CP_DONOR,
    _jsonata_brackets_balanced,
    _DONOR_SCHEMA,
    _ensure_exclusions_crit_color,
    _MERGED_PRR,
    _OV_DONOR,
    _OV_EXCL,
    _DQ_DONOR,
    _INC_DONOR,
    _OV_PROVIDER,
)


pytestmark = pytest.mark.repo_backed


def test_prr_only_stage_fields_are_not_emitted_by_shared_donor() -> None:
    """Avoid null duplicates when the Overview panel joins its PRR target."""
    prr_fields = (
        "quarantined",
        "excluded",
        "deduplicated",
        "filtered_out",
        "excluded_pct",
        "saved_pct",
    )
    for field in prr_fields:
        assert f"'{field}': null" not in _DONOR_SCHEMA
        assert f"'{field}'" in _MERGED_PRR


def test_phase2_linter_passes_on_provisioned_dashboards() -> None:
    assert lint.main(["--profile", "phase2"]) == 0


def test_phase4_linter_passes_on_provisioned_dashboards() -> None:
    # Default profile is phase4 (CI/unit gate for full acceptance checks).
    assert lint.main([]) == 0
    assert lint.main(["--profile", "phase4"]) == 0


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
        'href="/d/bioetl-run-explorer-v1/1-run-explorer">1. Run Explorer</a>'
        '<a class="bioetl-nav-link" style="width:19.5%" '
        'href="/d/bioetl-control-plane-v1/2-replay-readiness">2. Replay Readiness</a>'
        '<span class="bioetl-nav-current" style="width:19.5%">3. Run Overview</span>'
        '<a class="bioetl-nav-link" style="width:19.5%" '
        'href="/d/bioetl-dq-v2/4-data-quality">4. Data Quality</a>'
        '<a class="bioetl-nav-link" style="width:19.5%" '
        'href="/d/bioetl-incident-v1/5-incident-workspace">'
        "5. Incident Workspace</a></div>"
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
        "/d/bioetl-dq-v2/4-data-quality"
        "?${workflow:queryparam}&${pipeline:queryparam}"
        "&viewPanel=9460&${__url_time_range}"
    )
    assert uid == "bioetl-dq-v2"
    assert panel == 9460


def test_parse_dashboard_view_panel_first_param_and_amp_entities() -> None:
    uid, panel = lint.parse_dashboard_view_panel(
        "/d/bioetl-overview-v2/3-run-overview?viewPanel=9300&amp;var-run_id=abc"
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
                        "Data Quality 6. Incident Workspace"
                        "</div>"
                    )
                },
                "links": [
                    {
                        "title": "broken mid-query",
                        "url": (
                            "/d/bioetl-dq-v2/4-data-quality"
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


def test_phase25_donors_normalize_columns_before_frame_conversion() -> None:
    for donor in (_OV_DONOR, _DQ_DONOR, _INC_DONOR, _CP_DONOR):
        assert "$schema :=" in donor
        assert "_bioetl_frame" in donor
        assert "'parameter': null" in donor
        assert "'stage_id': null" in donor


def test_provider_table_formats_result_without_mutating_stat_value() -> None:
    assert "'check_result_display':" in _OV_PROVIDER
    assert "'check_result': $cached" not in _OV_PROVIDER


def test_nav_lint_requires_real_chip_elements() -> None:
    findings = lint._nav_content_findings(
        "bioetl-overview-v2.json",
        (
            '<div class="bioetl-nav">'
            '<span class="bioetl-nav-current">x</span>'
            "19.5% 19.5% 19.5% 19.5% 19.5%"
            "Run Explorer Replay Readiness Run Overview "
            "Data Quality 6. Incident Workspace"
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


def test_non_digit_mapping_requires_status_token() -> None:
    assert not lint._non_digit_mapping_is_status("data_quality", "DQ")
    assert lint._non_digit_mapping_is_status("SELECT RUN", "")
    assert lint._non_digit_mapping_is_status("x", "UNKNOWN")
    assert not lint._mapping_has_status_token(
        {
            "type": "value",
            "options": {"data_quality": {"text": "DQ"}},
        }
    )
    assert lint._mapping_has_status_token(
        {
            "type": "value",
            "options": {
                "data_quality": {"text": "DQ"},
                "OK": {"text": "OK", "color": "green"},
            },
        }
    )


def test_overview_exclusions_status_preserves_select_run() -> None:
    """A1 SELECT RUN and A2 empty catalog must not collapse into UNKNOWN."""
    assert "verdict='SELECT RUN' or verdict='НЕТ ЗАПУСКОВ'" in _OV_EXCL
    assert "verdict='SELECT RUN' ? 'Choose a run'" in _OV_EXCL
    assert "verdict='НЕТ ЗАПУСКОВ' ? 'No runs in scope'" in _OV_EXCL
    assert _OV_EXCL in _OV_DONOR


def test_exclusions_canvas_keeps_select_run_value_mapping() -> None:
    panel: dict = {
        "fieldConfig": {
            "defaults": {
                "mappings": [
                    {
                        "type": "value",
                        "options": {
                            "UNKNOWN": {"text": "UNKNOWN", "color": "gray"},
                        },
                    }
                ]
            }
        }
    }
    _ensure_exclusions_crit_color(panel)
    mappings = panel["fieldConfig"]["defaults"]["mappings"]
    value_options = next(
        item["options"] for item in mappings if item.get("type") == "value"
    )
    assert value_options["SELECT RUN"] == {"text": "SELECT RUN", "color": "gray"}
    assert value_options["НЕТ ЗАПУСКОВ"] == {
        "text": "НЕТ ЗАПУСКОВ",
        "color": "gray",
    }
    assert value_options["UNKNOWN"] == {"text": "UNKNOWN", "color": "gray"}
    assert any(
        item.get("type") == "regex"
        and (item.get("options") or {}).get("pattern") == "^CRIT.*"
        for item in mappings
    )


def _panel_by_id(dashboard: dict, panel_id: int) -> dict:
    def walk(panels: list) -> dict | None:
        for panel in panels or []:
            if not isinstance(panel, dict):
                continue
            if panel.get("id") == panel_id:
                return panel
            found = walk(panel.get("panels") or [])
            if found is not None:
                return found
        return None

    panel = walk(dashboard.get("panels") or [])
    assert panel is not None, f"missing panel id={panel_id}"
    return panel


def _organize_rename(panel: dict) -> dict[str, str]:
    for transform in panel.get("transformations") or []:
        if transform.get("id") == "organize":
            rename = (transform.get("options") or {}).get("renameByName") or {}
            return {str(k): str(v) for k, v in rename.items()}
    return {}


def test_f15_status_columns_unified_on_overview_dq_incident() -> None:
    """F-15: Review Selected Run Status titles match across OV/DQ/Incident."""
    expected = {
        "Processing",
        "Overall verdict",
        "Trust",
        "Reason",
    }
    cases = (
        ("grafana/dashboards/bioetl-overview-v2.json", 9603),
        ("grafana/dashboards/bioetl-dq-v2.json", 9406),
        ("grafana/dashboards/bioetl-incident-v1.json", 2101),
    )
    for path, panel_id in cases:
        panel = _panel_by_id(
            json.loads(Path(path).read_text(encoding="utf-8")), panel_id
        )
        titles = set(_organize_rename(panel).values())
        assert expected <= titles, f"{path}:{panel_id} titles={titles}"


def test_f03_overview_provider_check_maps_query_error() -> None:
    """F-03 / §1.2: Overview 9481 must map QUERY ERROR (and Cached Bronze —)."""
    panel = _panel_by_id(
        json.loads(Path("grafana/dashboards/bioetl-overview-v2.json").read_text()),
        9481,
    )
    mappings = panel["fieldConfig"]["defaults"]["mappings"]
    value_options = next(
        item["options"] for item in mappings if item.get("type") == "value"
    )
    assert "QUERY ERROR" in value_options
    assert value_options["QUERY ERROR"]["color"] == "red"
    assert "—" in value_options


def test_f05_canvas_halves_do_not_overlap() -> None:
    """F-05 / §1.3: Canvas 9482 status/detail occupy non-overlapping top halves."""
    panel = _panel_by_id(
        json.loads(Path("grafana/dashboards/bioetl-overview-v2.json").read_text()),
        9482,
    )
    assert panel.get("type") == "canvas"
    elements = panel["options"]["root"]["elements"]
    by_name = {element["name"]: element for element in elements}
    status = by_name["status"]["placement"]
    detail = by_name["detail"]["placement"]
    assert by_name["status"]["constraint"]["vertical"] == "top"
    assert by_name["detail"]["constraint"]["vertical"] == "top"
    assert status["top"] < detail["top"]
    assert status["top"] + status["height"] <= detail["top"]


def test_f30_domains_panel_heights_are_compact() -> None:
    """F-30 / §4.3: domains tables use h in 7–8 at limitField 6."""
    cases = (
        ("grafana/dashboards/bioetl-overview-v2.json", 9002),
        ("grafana/dashboards/bioetl-dq-v2.json", 9451),
        ("grafana/dashboards/bioetl-incident-v1.json", 9451),
    )
    for path, panel_id in cases:
        panel = _panel_by_id(
            json.loads(Path(path).read_text(encoding="utf-8")), panel_id
        )
        height = int(panel["gridPos"]["h"])
        assert 7 <= height <= 8, f"{path}:{panel_id} h={height}"


def test_seed_dc6_pipeline_run_report_writes_matching_identity(
    tmp_path: Path,
) -> None:
    """DC-6 helper materializes a v1 report whose identity matches the seed."""
    from scripts.ops.observability.seed_dc6_pipeline_run_report import main

    assert main(["--root", str(tmp_path)]) == 0
    run_id = "00000000-0000-4000-8000-000000000942"
    path = tmp_path / "pipeline" / "chembl_assay" / run_id / "pipeline-run-report.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "pipeline_run_report_v1"
    assert payload["identity"]["run_id"] == run_id
    assert payload["identity"]["pipeline_name"] == "chembl_assay"
    assert payload["identity"]["workflow_id"] == "chembl_baseline"
    assert (tmp_path / "pipeline" / "chembl_assay" / "_latest.json").is_file()
