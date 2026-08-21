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
"""Fail-closed pytest coverage for incomplete DASH-* rules (#9204 / #9238)."""

from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest
import yaml

from tests.integration._dashboard_requirement_coverage import (
    assert_data_panels_name_empty_state,
    assert_first_screen_decision_contract,
    assert_forensic_rows_collapsed_and_below_fold,
    assert_grafana_optional_on_default_runtime,
    assert_http_empty_state_copy,
    assert_infinity_parser_backend_for_rows,
    assert_no_write_urls,
    assert_ops_http_paths_allowlisted,
    assert_processing_status_distinct_from_trust,
    assert_promql_uses_shipped_series,
    assert_shipped_json_is_read_only,
    assert_synthetic_zero_policy,
    assert_unique_primary_cta,
    assert_verdict_mappings_and_palette_text,
    coverage_allowlist,
    data_panel_empty_state_violations,
    first_screen_decision_violations,
    forensic_first_window_violations,
    http_empty_state_violations,
    infinity_parser_violations,
    invented_metric_violations,
    load_synthetic_zero_allowlist,
    ops_http_path_violations,
    processing_trust_violations,
    synthetic_zero_violations,
    trust_display_state,
    write_url_violations,
)
from tests.integration._grafana_test_support import (
    get_all_valid_metric_names,
    load_dashboard,
)

pytestmark = pytest.mark.integration

_CONTROL_PLANE = Path("grafana/dashboards/bioetl-control-plane-v1.json")
_RUNTIME = Path("grafana/dashboards/bioetl-runtime.json")
_OVERVIEW = Path("grafana/dashboards/bioetl-overview-v2.json")


def _panel_by_id(dashboard: dict[str, object], panel_id: int) -> dict[str, object]:
    for panel in dashboard.get("panels") or []:
        if isinstance(panel, dict) and panel.get("id") == panel_id:
            return panel
        if isinstance(panel, dict) and panel.get("type") == "row":
            for child in panel.get("panels") or []:
                if isinstance(child, dict) and child.get("id") == panel_id:
                    return child
    raise AssertionError(f"panel id={panel_id} not found")


def test_dash_arch_001_grafana_is_optional_and_read_only() -> None:
    """#9216: default runtime does not require Grafana; JSON is read-only."""
    assert_grafana_optional_on_default_runtime()
    assert_shipped_json_is_read_only()


def test_dash_arch_001_fails_closed_on_write_admin_url() -> None:
    dashboard = copy.deepcopy(load_dashboard(_CONTROL_PLANE))
    panel = _panel_by_id(dashboard, 9401)
    defaults = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
    links = list(defaults.get("links") or [])
    links.append({"title": "Grafana admin", "url": "/api/admin/users"})
    defaults["links"] = links
    with pytest.raises(AssertionError, match="write/admin"):
        assert_no_write_urls("bioetl-control-plane-v1.json", dashboard)
    assert (
        write_url_violations(
            "bioetl-control-plane-v1.json", load_dashboard(_CONTROL_PLANE)
        )
        == []
    )


def test_dash_data_001_ops_http_and_recording_rules_cover_seven_uids() -> None:
    """#9218: all seven UIDs stay on Ops HTTP paths and shipped series."""
    assert_ops_http_paths_allowlisted()
    assert_promql_uses_shipped_series()


def test_dash_data_001_fails_closed_on_invented_series_and_off_allowlist_url() -> None:
    dashboard = copy.deepcopy(load_dashboard(_RUNTIME))
    panel = _panel_by_id(dashboard, 9401)
    targets = list(panel.get("targets") or [])
    assert targets, "runtime 9401 must have PromQL targets"
    mutated_target = copy.deepcopy(targets[0])
    mutated_target["expr"] = "bioetl_invented_metric_total"
    panel["targets"] = [mutated_target]
    valid = get_all_valid_metric_names()
    with pytest.raises(AssertionError, match="invented series"):
        violations = invented_metric_violations("bioetl-runtime.json", dashboard, valid)
        assert not violations, "\n".join(violations)

    http_dashboard = copy.deepcopy(load_dashboard(_CONTROL_PLANE))
    http_panel = _panel_by_id(http_dashboard, 9418)
    http_target = copy.deepcopy((http_panel.get("targets") or [])[0])
    http_target["url"] = "/api/grafana/write"
    http_panel["targets"] = [http_target]
    with pytest.raises(AssertionError, match="url="):
        path_violations = ops_http_path_violations(
            "bioetl-control-plane-v1.json", http_dashboard
        )
        assert not path_violations, "\n".join(path_violations)


def test_dash_state_001_zero_001_synthetic_zero_allowlist() -> None:
    """#9215: verdict/status/trust panels must not mask absence as zero."""
    allowlist = load_synthetic_zero_allowlist()
    assert allowlist, "DASH-ZERO-001 allowlist must be non-empty and governed"
    assert_synthetic_zero_policy()


def test_dash_state_001_fails_closed_on_verdict_synthetic_zero() -> None:
    dashboard = copy.deepcopy(load_dashboard(_CONTROL_PLANE))
    panel = _panel_by_id(dashboard, 9401)
    targets = list(panel.get("targets") or [])
    mutated = copy.deepcopy(targets[0])
    mutated["expr"] = f"{mutated.get('expr')} or vector(0)"
    panel["targets"] = [mutated]
    with pytest.raises(AssertionError, match="synthetic zero"):
        violations = synthetic_zero_violations(
            "bioetl-control-plane-v1.json", dashboard
        )
        assert not violations, "\n".join(violations)


def test_dash_state_004_processing_status_distinct_from_trust() -> None:
    """#9217: processing success is not trust OK / replay-ready."""
    assert_processing_status_distinct_from_trust()
    payload = {
        "processing_status": "success",
        "trust_status": "INCOMPLETE",
        "reasons": ["missing_manifest"],
    }
    assert trust_display_state(payload) == "INCOMPLETE"
    assert trust_display_state({"processing_status": "success"}) == "UNKNOWN"


def test_dash_state_004_fails_closed_when_success_is_labeled_ok_trust() -> None:
    dashboard = copy.deepcopy(load_dashboard(_CONTROL_PLANE))
    panel = _panel_by_id(dashboard, 9418)
    panel["description"] = (
        "processing_status=success means trust_status=OK and replay-ready"
    )
    with pytest.raises(AssertionError, match="conflates processing success"):
        violations = processing_trust_violations(
            "bioetl-control-plane-v1.json", dashboard
        )
        assert not violations, "\n".join(violations)


def test_dash_first_001_operator_question_contract() -> None:
    """#9214: each UID answers one §7 question through first-window tokens."""
    assert_first_screen_decision_contract()


def test_dash_first_001_fails_closed_when_next_action_token_drifts() -> None:
    dashboard = copy.deepcopy(load_dashboard(_OVERVIEW))
    for panel in dashboard.get("panels") or []:
        if not isinstance(panel, dict):
            continue
        for key in ("title", "description"):
            value = panel.get(key)
            if isinstance(value, str):
                panel[key] = value.replace(
                    "Review First Action", "Review Something Else"
                )
        defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
        if isinstance(defaults, dict):
            for link in defaults.get("links") or []:
                if isinstance(link, dict) and isinstance(link.get("title"), str):
                    link["title"] = link["title"].replace(
                        "Review First Action", "Review Something Else"
                    )
    with pytest.raises(AssertionError, match="next_action token"):
        violations = first_screen_decision_violations(
            "bioetl-overview-v2.json", dashboard
        )
        assert not violations, "\n".join(violations)


def test_dash_first_002_forensic_rows_collapsed() -> None:
    """#9214: Inspect forensic tables stay allowlisted or below the fold."""
    coverage_allowlist("first_window_inspect_tables")
    assert_forensic_rows_collapsed_and_below_fold()


def test_dash_first_002_fails_closed_on_uncollapsed_or_unallowlisted_inspect() -> None:
    dashboard = copy.deepcopy(load_dashboard(_RUNTIME))
    for panel in dashboard.get("panels") or []:
        if isinstance(panel, dict) and panel.get("type") == "row":
            panel["collapsed"] = False
            break
    with pytest.raises(AssertionError, match="must ship collapsed"):
        violations = forensic_first_window_violations("bioetl-runtime.json", dashboard)
        assert not violations, "\n".join(violations)

    overview = copy.deepcopy(load_dashboard(_OVERVIEW))
    table = _panel_by_id(overview, 9603)
    table["title"] = "Inspect Forensic Dump"
    table["type"] = "table"
    table["gridPos"] = {"x": 0, "y": 8, "w": 24, "h": 8}
    with pytest.raises(AssertionError, match="not allowlisted"):
        violations = forensic_first_window_violations(
            "bioetl-overview-v2.json", overview
        )
        assert not violations, "\n".join(violations)


def test_dash_action_001_copy_001_state_002_cta_empty_state_and_palette() -> None:
    """#9213: unique CTA, HTTP empty-vs-unavailable copy, mappings plus text."""
    assert_unique_primary_cta()
    assert_http_empty_state_copy()
    assert_verdict_mappings_and_palette_text()


def test_dash_copy_001_fails_closed_without_unavailable_wording() -> None:
    dashboard = copy.deepcopy(load_dashboard(_CONTROL_PLANE))
    panel = _panel_by_id(dashboard, 9418)
    panel["description"] = "Valid empty when no rows."
    defaults = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
    defaults["noValue"] = "empty"
    with pytest.raises(AssertionError, match="unavailable=False"):
        violations = http_empty_state_violations(
            "bioetl-control-plane-v1.json", dashboard
        )
        assert not violations, "\n".join(violations)


def test_dash_data_001_infinity_parser_backend_on_ops_http_rows() -> None:
    """#9212: root_selector rows must use Infinity parser=backend."""
    assert_infinity_parser_backend_for_rows()


def test_dash_data_001_fails_closed_on_parser_simple_rows_table() -> None:
    dashboard = copy.deepcopy(load_dashboard(_CONTROL_PLANE))
    panel = _panel_by_id(dashboard, 9416)
    target = copy.deepcopy((panel.get("targets") or [])[0])
    target["parser"] = "simple"
    target["root_selector"] = "rows"
    panel["targets"] = [target]
    with pytest.raises(AssertionError, match="parser='simple'"):
        violations = infinity_parser_violations(
            "bioetl-control-plane-v1.json", dashboard
        )
        assert not violations, "\n".join(violations)


_COVERAGE_PATH = Path(
    "docs/03-guides/dashboards/contracts/requirement-test-coverage.yaml"
)
_REQUIREMENTS_PATH = Path("docs/01-requirements/DASHBOARD_REQUIREMENTS.md")
_DASH_ID_RE = re.compile(r"`(DASH-[A-Z]+-[0-9]{3})`")
_HEURISTIC_KEYS = ("owner", "remainder", "retire_when")


def test_requirement_coverage_matrix_lists_every_dash_id_and_nodeids() -> None:
    """#9238: yaml is a named nodeid lock, not a whole-module citation."""
    req_ids = set(_DASH_ID_RE.findall(_REQUIREMENTS_PATH.read_text(encoding="utf-8")))
    payload = yaml.safe_load(_COVERAGE_PATH.read_text(encoding="utf-8"))
    assert payload.get("canonical_module") == (
        "tests/integration/test_dashboard_requirement_coverage.py"
    )
    rows = payload["requirements"]
    covered = {str(row["id"]) for row in rows}
    missing = sorted(req_ids - covered)
    extra_ids = sorted(covered - req_ids)
    assert not missing, f"coverage matrix missing {missing}"
    assert not extra_ids, f"coverage matrix extra {extra_ids}"
    for row in rows:
        gate = str(row.get("gate") or "")
        tests = row.get("tests") or []
        prompt = row.get("prompt")
        if "manual" in gate:
            assert isinstance(prompt, str) and prompt.startswith("prompt.")
        else:
            assert tests, f"{row['id']} needs tests"
        for nodeid in tests:
            assert "::" in str(nodeid), (
                f"{row['id']} must cite path::test_name, got {nodeid}"
            )
            path_str, name = str(nodeid).split("::", 1)
            source = Path(path_str).read_text(encoding="utf-8")
            assert f"def {name}(" in source, f"missing {nodeid}"
        heuristic = row.get("heuristic")
        if heuristic:
            missing_keys = [
                key
                for key in _HEURISTIC_KEYS
                if not str(heuristic.get(key) or "").strip()
            ]
            assert not missing_keys, f"{row['id']} heuristic missing {missing_keys}"


def test_dash_copy_001_data_panels_name_empty_state() -> None:
    """#9237: data-bearing panels name empty / UNKNOWN / SELECT RUN."""
    assert_data_panels_name_empty_state()


def test_dash_copy_001_fails_closed_without_empty_state_copy() -> None:
    dashboard = copy.deepcopy(load_dashboard(_RUNTIME))
    panel = _panel_by_id(dashboard, 9401)
    panel["description"] = "Pipeline status."
    defaults = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
    defaults["noValue"] = ""
    violations = data_panel_empty_state_violations("bioetl-runtime.json", dashboard)
    assert violations, "mutated runtime 9401 must fail DASH-COPY-001 empty-state copy"


def test_requirement_coverage_module_is_wired_as_required_dashboard_check() -> None:
    tests_workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    pre_commit = Path(".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "tests/integration/test_dashboard_requirement_coverage.py" in tests_workflow
    assert "check-dashboard-requirement-coverage" in pre_commit
    assert "test_dashboard_requirement_gaps.py" not in tests_workflow
    assert "test_dashboard_requirement_gaps.py" not in pre_commit
