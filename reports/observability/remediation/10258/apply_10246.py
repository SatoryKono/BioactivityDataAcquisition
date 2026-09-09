#!/usr/bin/env python3
"""Idempotent re-apply of #10246 (H1 Provider Health empty-state semantics).

Parallel #10258 agents have hard-reset the worktree at least once; keep this
script so the #10246 surface can be restored without re-deriving the edits.

Run from the repository root:
    .venv-win\\Scripts\\python.exe reports/observability/remediation/10258/apply_10246.py
"""

from __future__ import annotations

from pathlib import Path

DASHBOARD = Path("grafana/dashboards/bioetl-provider-health-v2.json")
CONTRACT = Path("docs/03-guides/dashboards/contracts/panel-content-contract.yaml")
QA_CHECK = Path("scripts/engineering/qa/check_dashboard_visual_semantics.py")
TESTS = Path("tests/integration/test_grafana_dashboard_metric_semantics.py")

COVERAGE_GUARD = (
    "(count(max by (provider) (bioetl_provider_current_status)) > bool 0)"
    " * (count(max by (provider) (bioetl_provider_current_cause)) > bool 0)"
    " * absent(max by (provider) (bioetl_provider_current_status) != 0)"
    " * absent(max by (provider) (bioetl_provider_current_status)"
    " unless on(provider) max by (provider) (bioetl_provider_health_status))"
    " * absent(max by (provider, cause) (bioetl_provider_current_cause) > 0)"
)
VALID_EMPTY_LABEL = "VALID EMPTY - FLEET coverage proven, no active provider causes"
UNKNOWN_LABEL = "UNKNOWN - FLEET cause coverage unproven, restore provider telemetry"
FLEET_VERDICT_BRANCHES = (
    f' or label_replace(({COVERAGE_GUARD}), \\"cause\\", \\"{VALID_EMPTY_LABEL}\\",'
    ' \\"\\", \\"\\")'
    " or label_replace((absent(max by (provider, cause)"
    f" (bioetl_provider_current_cause) > 0) unless ({COVERAGE_GUARD})),"
    f' \\"cause\\", \\"{UNKNOWN_LABEL}\\", \\"\\", \\"\\")'
)

CAUSES = "max by (provider, cause) (bioetl_provider_current_cause) > 0"

DASHBOARD_EDITS: tuple[tuple[str, str], ...] = (
    # 9103 Inspect Top Provider Causes — bounded first-lane copy.
    (
        f'"expr": "topk(4, {CAUSES})",',
        f'"expr": "topk(4, {CAUSES}){FLEET_VERDICT_BRANCHES}",',
    ),
    # 9113 Inspect Full Provider Causes — unbounded forensic copy.
    (
        f'"expr": "{CAUSES}",',
        f'"expr": "({CAUSES}){FLEET_VERDICT_BRANCHES}",',
    ),
    # 9103 noValue (trailing comma distinguishes it from 9102).
    (
        '"noValue": "UNKNOWN \u2014 missing/stale provider telemetry, or VALID'
        " EMPTY if the fleet has no matching rows. Not a selected-run"
        ' verdict.",',
        '"noValue": "UNKNOWN \u2014 cause evidence unavailable. Verify the'
        ' Prometheus datasource, then Monitor Telemetry Presence.",',
    ),
    # 9102 noValue.
    (
        '"noValue": "UNKNOWN \u2014 missing/stale provider telemetry, or VALID'
        " EMPTY if the fleet has no matching rows. Not a selected-run"
        ' verdict."',
        '"noValue": "UNKNOWN \u2014 no non-OK evidence and no coverage proof.'
        ' Check Monitor Telemetry Presence before calling the fleet healthy."',
    ),
    # 9107 noValue.
    (
        '"noValue": "UNKNOWN \u2014 missing health_status for this provider, or'
        ' VALID EMPTY if the selected provider has no universe row."',
        '"noValue": "UNKNOWN \u2014 no status-reason evidence for this provider'
        ' scope. Check Monitor Telemetry Presence, then Inspect Raw Health'
        ' Status."',
    ),
    # 9103 description.
    (
        '"description": "TIME RANGE \u00b7 CURRENT \u00b7 Top current causes of'
        " provider degradation, bounded to the worst four rows, such as raw"
        " health, failures, retry exhaustion, latency, HTTP errors, or rate"
        " limiting. Scope: fleet; not filtered by run ID. If fleet severity is"
        " non-OK and this table is empty, check scrape and recording-rule"
        " health. Complete cause evidence remains in Inspect Full Fleet"
        ' Evidence. TELEMETRY MISSING is not a zero and not VALID EMPTY.",',
        '"description": "TIME RANGE \u00b7 CURRENT \u00b7 Top current causes of'
        " provider degradation, bounded to the worst four rows, such as raw"
        " health, failures, retry exhaustion, latency, HTTP errors, or rate"
        " limiting. Scope: fleet; not filtered by run ID. This table renders"
        " exactly one state: active-cause rows, or a single FLEET verdict row."
        " VALID EMPTY needs proven coverage \u2014 recorded status for every"
        " provider, no provider above OK, present health telemetry, present"
        " cause series, and no active cause. Unproven coverage stays UNKNOWN"
        " and means restore provider telemetry; it is never a healthy empty."
        " Datasource or query failure is QUERY ERROR, never an empty table."
        " Complete cause evidence remains in Inspect Full Fleet Evidence."
        ' TELEMETRY MISSING is not a zero and not VALID EMPTY.",',
    ),
    # 9113 description.
    (
        '"description": "TIME RANGE \u00b7 Complete current cause evidence.'
        " First-screen Inspect Top Provider Causes is the four-row summary."
        ' TELEMETRY MISSING is not a zero and not VALID EMPTY.",',
        '"description": "TIME RANGE \u00b7 Complete current cause evidence,'
        " unbounded copy of Inspect Top Provider Causes. Same one-state rule:"
        " active-cause rows, or a single FLEET verdict row. VALID EMPTY needs"
        " proven coverage \u2014 recorded status for every provider, no"
        " provider above OK, present health telemetry, present cause series,"
        " and no active cause. Unproven coverage stays UNKNOWN and means"
        " restore provider telemetry. TELEMETRY MISSING is not a zero and not"
        ' VALID EMPTY.",',
    ),
    # 9103 diagnostic handoff for the UNKNOWN fleet verdict row.
    (
        """          "id": 9103,
          "options": {
            "cellHeight": "sm",
            "dataLinks": [
              {
                "targetBlank": true,
                "title": "Open Provider Incident Runbook",""",
        """          "id": 9103,
          "options": {
            "cellHeight": "sm",
            "dataLinks": [
              {
                "targetBlank": false,
                "title": "Diagnose provider telemetry coverage",
                "url": "/d/bioetl-provider-health-v2/bioetl-provider-health-v2?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&viewPanel=9104&${__url_time_range}"
              },
              {
                "targetBlank": true,
                "title": "Open Provider Incident Runbook",""",
    ),
)

CONTRACT_EDITS: tuple[tuple[str, str], ...] = (
    (
        """      '9103':
        title: Inspect Top Provider Causes
        role: causes_table
        tier: 1
        scope: current
        scope_class: current
        evidence_source: prometheus
        empty_state_class: telemetry_missing
        state_model:
        - VALID_EMPTY
        - ERROR
        required_copy:
        - evidence_scope
        - no_data
        - next_action
        fixture_cases:
        - populated
        - valid_empty
        - backend_error
""",
        """      '9103':
        title: Inspect Top Provider Causes
        role: causes_table
        tier: 1
        scope: current
        scope_class: current
        evidence_source: prometheus
        empty_state_class: telemetry_missing
        state_model:
        - VALID_EMPTY
        - UNKNOWN
        - ERROR
        - TELEMETRY_ABSENT
        required_copy:
        - evidence_scope
        - no_data
        - next_action
        fixture_cases:
        - populated
        - valid_empty
        - telemetry_absent
        - backend_error
""",
    ),
    (
        """      '9113':
        title: Inspect Full Provider Causes
        role: forensic_table
        tier: 3
        scope: time_range
        scope_class: time_range
        evidence_source: prometheus
        empty_state_class: telemetry_missing
        state_model:
        - VALID_EMPTY
        - ERROR
        - TELEMETRY_ABSENT
""",
        """      '9113':
        title: Inspect Full Provider Causes
        role: forensic_table
        tier: 3
        scope: time_range
        scope_class: time_range
        evidence_source: prometheus
        empty_state_class: telemetry_missing
        state_model:
        - VALID_EMPTY
        - UNKNOWN
        - ERROR
        - TELEMETRY_ABSENT
""",
    ),
    (
        """      '9107':
        title: Inspect Status Reason
        role: forensic_table
        tier: 3
        scope: current
        scope_class: current
        evidence_source: prometheus
        empty_state_class: telemetry_missing
        state_model:
        - VALID_EMPTY
        - ERROR
        - TELEMETRY_ABSENT
        required_copy:
        - evidence_scope
        - no_data
        fixture_cases:
        - populated
        - valid_empty
        - telemetry_absent
        - backend_error
""",
        """      '9107':
        title: Inspect Status Reason
        role: forensic_table
        tier: 3
        scope: current
        scope_class: current
        evidence_source: prometheus
        empty_state_class: telemetry_missing
        state_model:
        - UNKNOWN
        - ERROR
        - TELEMETRY_ABSENT
        required_copy:
        - evidence_scope
        - no_data
        fixture_cases:
        - populated
        - telemetry_absent
        - backend_error
""",
    ),
    (
        """      '9102':
        title: Inspect Non-OK Providers
        role: forensic_table
        tier: 3
        scope: time_range
        scope_class: time_range
        evidence_source: prometheus
        empty_state_class: telemetry_missing
        state_model:
        - VALID_EMPTY
        - ERROR
        - TELEMETRY_ABSENT
        required_copy:
        - evidence_scope
        - no_data
        fixture_cases:
        - populated
        - valid_empty
        - telemetry_absent
        - backend_error
""",
        """      '9102':
        title: Inspect Non-OK Providers
        role: forensic_table
        tier: 3
        scope: time_range
        scope_class: time_range
        evidence_source: prometheus
        empty_state_class: telemetry_missing
        state_model:
        - UNKNOWN
        - ERROR
        - TELEMETRY_ABSENT
        required_copy:
        - evidence_scope
        - no_data
        fixture_cases:
        - populated
        - telemetry_absent
        - backend_error
""",
    ),
)

QA_EDITS: tuple[tuple[str, str], ...] = (
    (
        """import json
from pathlib import Path
from typing import Any, cast
""",
        """import json
import re
from pathlib import Path
from typing import Any, cast
""",
    ),
    (
        """REQUIRED_TRUST_MARKER_PANELS = {
    DASHBOARD_RUNTIME: {PANEL_METRICS_EVIDENCE},
    DASHBOARD_CONTROL_PLANE_V1: {PANEL_INSPECT_TELEMETRY_MISSING},
}
""",
        """REQUIRED_TRUST_MARKER_PANELS = {
    DASHBOARD_RUNTIME: {PANEL_METRICS_EVIDENCE},
    DASHBOARD_CONTROL_PLANE_V1: {PANEL_INSPECT_TELEMETRY_MISSING},
}

# DASH-STATE-001/003 (#10246): operator copy must confirm one empty state.
# Offering UNKNOWN and VALID EMPTY as alternatives for the same render leaves
# the operator unable to choose between "restore telemetry" and "nothing to do".
# A negation list ("not a healthy zero or VALID EMPTY") teaches the taxonomy and
# stays allowed; only alternatives offered for the same render are rejected.
HEDGED_EMPTY_STATE_PATTERNS = (
    re.compile(r"\\bor\\s+VALID\\s+EMPTY\\s+if\\b", re.IGNORECASE),
    re.compile(r"\\bor\\s+UNKNOWN\\s+if\\b", re.IGNORECASE),
    re.compile(r"\\bor\\s+TELEMETRY\\s+MISSING\\s+if\\b", re.IGNORECASE),
    re.compile(r"\\bUNKNOWN\\b[^.;]{0,80}?\\bor\\s+VALID\\s+EMPTY\\b", re.IGNORECASE),
    re.compile(
        r"\\bTELEMETRY\\s+MISSING\\b[^.;]{0,80}?\\bor\\s+VALID\\s+EMPTY\\b",
        re.IGNORECASE,
    ),
    re.compile(r"\\bVALID\\s+EMPTY\\b[^.;]{0,80}?\\bor\\s+UNKNOWN\\b", re.IGNORECASE),
    re.compile(r"\\bUNKNOWN\\s*/\\s*VALID\\s+EMPTY\\b", re.IGNORECASE),
    re.compile(r"\\bVALID\\s+EMPTY\\s*/\\s*UNKNOWN\\b", re.IGNORECASE),
)
""",
    ),
    (
        """def _panel_errors(dashboard_path: Path, panel: JsonObject) -> list[str]:
""",
        '''def _override_no_value_texts(panel: JsonObject) -> list[str]:
    return [
        prop["value"]
        for override in panel.get("fieldConfig", {}).get("overrides", [])
        if isinstance(override, dict)
        for prop in override.get("properties", [])
        if isinstance(prop, dict)
        and prop.get("id") == "noValue"
        and isinstance(prop.get("value"), str)
    ]


def _empty_state_copy_texts(panel: JsonObject) -> list[tuple[str, str]]:
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    texts: list[tuple[str, str]] = []
    for field, value in (
        ("noValue", defaults.get("noValue")),
        ("description", panel.get("description")),
    ):
        if isinstance(value, str):
            texts.append((field, value))
    texts.extend(("override noValue", text) for text in _override_no_value_texts(panel))
    return texts


def _empty_state_hedge_errors(dashboard_path: Path, panel: JsonObject) -> list[str]:
    """Reject copy that offers two empty states as alternatives (DASH-STATE-001)."""
    title = str(panel.get("title", UNTITLED_PANEL_TITLE))
    errors: list[str] = []
    for field, text in _empty_state_copy_texts(panel):
        hedge = next(
            (
                pattern.pattern
                for pattern in HEDGED_EMPTY_STATE_PATTERNS
                if pattern.search(text)
            ),
            None,
        )
        if hedge is not None:
            errors.append(
                f"{dashboard_path}: panel \'{title}\' {field} must confirm one empty "
                f"state, not offer alternatives (matched {hedge!r})"
            )
    return errors


def _panel_errors(dashboard_path: Path, panel: JsonObject) -> list[str]:
''',
    ),
    (
        """        + _fail_closed_panel_errors(dashboard_path, panel, expected_no_value)
    )
""",
        """        + _fail_closed_panel_errors(dashboard_path, panel, expected_no_value)
        + _empty_state_hedge_errors(dashboard_path, panel)
    )
""",
    ),
)

TESTS_MARKER = "_PROVIDER_CAUSE_COVERAGE_GUARD"
TESTS_APPENDIX = '''

_PROVIDER_HEALTH_DASHBOARD = Path("grafana/dashboards/bioetl-provider-health-v2.json")
_PROVIDER_HEALTH_UID = "bioetl-provider-health-v2"
# #10246: fleet-coverage proof required before any provider-health VALID EMPTY.
_PROVIDER_CAUSE_COVERAGE_GUARD = (
    "(count(max by (provider) (bioetl_provider_current_status)) > bool 0)"
    " * (count(max by (provider) (bioetl_provider_current_cause)) > bool 0)"
    " * absent(max by (provider) (bioetl_provider_current_status) != 0)"
    " * absent(max by (provider) (bioetl_provider_current_status)"
    " unless on(provider) max by (provider) (bioetl_provider_health_status))"
    " * absent(max by (provider, cause) (bioetl_provider_current_cause) > 0)"
)
_PROVIDER_CAUSE_VALID_EMPTY_LABEL = (
    "VALID EMPTY - FLEET coverage proven, no active provider causes"
)
_PROVIDER_CAUSE_UNKNOWN_LABEL = (
    "UNKNOWN - FLEET cause coverage unproven, restore provider telemetry"
)
_PROVIDER_CAUSE_PANEL_IDS = (9103, 9113)
_PROVIDER_SINGLE_STATE_NO_VALUE_PANEL_IDS = (9102, 9103, 9107)


def _provider_health_panels_by_id() -> dict[int, dict[str, object]]:
    dashboard = load_dashboard(_PROVIDER_HEALTH_DASHBOARD)
    return {
        panel["id"]: panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }


def test_provider_health_no_value_copy_confirms_exactly_one_empty_state() -> None:
    """#10246 H1: a provider-health noValue must not offer UNKNOWN *or* VALID EMPTY."""
    panels = _provider_health_panels_by_id()
    for panel_id in _PROVIDER_SINGLE_STATE_NO_VALUE_PANEL_IDS:
        panel = panels.get(panel_id)
        assert panel is not None, f"provider-health panel {panel_id} is missing"
        no_value = panel.get("fieldConfig", {}).get("defaults", {}).get("noValue")
        assert isinstance(no_value, str) and no_value, (
            f"panel {panel_id} must declare a fail-closed noValue"
        )
        assert not ("UNKNOWN" in no_value and "VALID EMPTY" in no_value), (
            f"panel {panel_id} noValue concatenates UNKNOWN and VALID EMPTY as "
            f"alternative explanations: {no_value!r}"
        )
        assert no_value.startswith("UNKNOWN"), (
            f"panel {panel_id} noValue must lead with the confirmed UNKNOWN state: "
            f"{no_value!r}"
        )


def test_provider_health_copy_never_hedges_two_empty_states() -> None:
    """Provider-health noValue/description must confirm one state, not alternatives."""
    from scripts.engineering.qa import check_dashboard_visual_semantics as subject

    errors = [
        error
        for panel in get_dashboard_panels(load_dashboard(_PROVIDER_HEALTH_DASHBOARD))
        for error in subject._empty_state_hedge_errors(
            _PROVIDER_HEALTH_DASHBOARD, panel
        )
    ]
    assert not errors, "hedged provider-health empty-state copy:\\n" + "\\n".join(errors)


def test_empty_state_hedge_invariant_rejects_the_10246_regression() -> None:
    """The anti-hedge invariant must fail on the exact copy #10246 removed."""
    from scripts.engineering.qa import check_dashboard_visual_semantics as subject

    regression = {
        "title": "Inspect Top Provider Causes",
        "fieldConfig": {
            "defaults": {
                "noValue": (
                    "UNKNOWN \\u2014 missing/stale provider telemetry, or VALID EMPTY "
                    "if the fleet has no matching rows."
                )
            }
        },
    }
    assert subject._empty_state_hedge_errors(_PROVIDER_HEALTH_DASHBOARD, regression)

    taxonomy_copy = {
        "title": "Inspect Top Provider Causes",
        "description": "TELEMETRY MISSING is not a zero and not VALID EMPTY.",
        "fieldConfig": {
            "defaults": {"noValue": "UNKNOWN \\u2014 cause evidence unavailable"}
        },
    }
    assert not subject._empty_state_hedge_errors(
        _PROVIDER_HEALTH_DASHBOARD, taxonomy_copy
    )


def test_provider_cause_tables_emit_one_fleet_verdict_row() -> None:
    """VALID EMPTY needs the coverage proof; otherwise the fleet row stays UNKNOWN."""
    panels = _provider_health_panels_by_id()
    for panel_id in _PROVIDER_CAUSE_PANEL_IDS:
        panel = panels.get(panel_id)
        assert panel is not None, f"provider-health panel {panel_id} is missing"
        expressions = [
            target["expr"]
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert len(expressions) == 1, (
            f"panel {panel_id} must answer from one instant snapshot"
        )
        expr = expressions[0]

        valid_empty_index = expr.find(_PROVIDER_CAUSE_VALID_EMPTY_LABEL)
        unknown_index = expr.find(_PROVIDER_CAUSE_UNKNOWN_LABEL)
        assert valid_empty_index > 0, (
            f"panel {panel_id} must expose a proven VALID EMPTY fleet row"
        )
        assert unknown_index > valid_empty_index, (
            f"panel {panel_id} must fall back to an UNKNOWN fleet row"
        )
        assert expr.count(_PROVIDER_CAUSE_COVERAGE_GUARD) == 2, (
            f"panel {panel_id} must gate VALID EMPTY on the coverage proof and "
            "exclude it from the UNKNOWN branch"
        )
        # The UNKNOWN branch must subtract the VALID EMPTY branch, so the two
        # fleet verdict rows can never render together.
        assert f"unless ({_PROVIDER_CAUSE_COVERAGE_GUARD})" in expr, (
            f"panel {panel_id} UNKNOWN row must exclude the proven-empty case"
        )
        assert "or vector(0)" not in expr
        assert "unless on (provider)" not in expr


def test_provider_cause_contract_declares_unknown_beside_valid_empty() -> None:
    """Contract must admit the UNKNOWN fleet row that #10246 locked in."""
    contract = yaml.safe_load(
        Path(
            "docs/03-guides/dashboards/contracts/panel-content-contract.yaml"
        ).read_text(encoding="utf-8")
    )
    panels = contract["dashboards"][_PROVIDER_HEALTH_UID]["panels"]
    for panel_id in _PROVIDER_CAUSE_PANEL_IDS:
        record = panels[str(panel_id)]
        assert {"VALID_EMPTY", "UNKNOWN"} <= set(record["state_model"]), (
            f"panel {panel_id} must declare both proven-empty and UNKNOWN states"
        )
        assert record["empty_state_class"] == "telemetry_missing"
    for panel_id in (9102, 9107):
        record = panels[str(panel_id)]
        assert "UNKNOWN" in record["state_model"]
        assert "VALID_EMPTY" not in record["state_model"], (
            f"panel {panel_id} cannot prove VALID EMPTY from its own query"
        )
'''


def _apply(path: Path, edits: tuple[tuple[str, str], ...]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    report: list[str] = []
    for old, new in edits:
        if new in text:
            report.append(f"  already applied: {old[:60]!r}")
            continue
        count = text.count(old)
        if count != 1:
            raise SystemExit(
                f"{path}: expected exactly one match for {old[:80]!r}, found {count}"
            )
        text = text.replace(old, new)
        report.append(f"  patched: {old[:60]!r}")
    path.write_text(text, encoding="utf-8")
    return report


def main() -> int:
    for path, edits in (
        (DASHBOARD, DASHBOARD_EDITS),
        (CONTRACT, CONTRACT_EDITS),
        (QA_CHECK, QA_EDITS),
    ):
        print(path)
        for line in _apply(path, edits):
            print(line)

    print(TESTS)
    tests_text = TESTS.read_text(encoding="utf-8")
    if TESTS_MARKER in tests_text:
        print("  already applied: test appendix")
    else:
        TESTS.write_text(tests_text.rstrip("\n") + "\n" + TESTS_APPENDIX, "utf-8")
        print("  patched: test appendix")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
