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
"""Unit tests for debt-governance gate helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime
from copy import deepcopy
from types import SimpleNamespace
import json
from pathlib import Path
import subprocess

import pytest
import yaml

from scripts.engineering.qa import report_debt_governance_gates as gates
from scripts.engineering.qa import debt_governance_gate_evaluators as gate_evaluators

pytestmark = pytest.mark.unit


def _review_expiry_scorecard(count: int) -> dict:
    return {
        "supporting_scripts_governance": {
            "metrics": {
                "expired_review_by_count": {"current_count": count, "max_count": count},
            }
        },
        "governance": {
            "coarse_budgets": {
                "expired_review_by_count": {"current_count": count, "max_count": count},
            }
        },
    }


@pytest.mark.parametrize(("count", "status"), [(1, "pass"), (2, "fail"), (0, "pass")])
def test_review_expiry_gate_ratcheted_count(
    tmp_path, monkeypatch, count, status
) -> None:
    monkeypatch.setattr(
        gate_evaluators,
        "_load_json",
        lambda *args: {
            "entries": {
                f"scripts/old{i}.py": {"review_by": "2026-10-20"} for i in range(count)
            }
        },
    )
    gate = gate_evaluators._scripts_review_expiry_gate(
        repo_root=tmp_path,
        scorecard=_review_expiry_scorecard(1),
        today=date(2026, 10, 21),
    )
    assert gate.status == status
    assert gate.current == count
    assert gate.limit == [1, 1]


@pytest.mark.parametrize(
    ("contents", "reason"),
    [
        (None, "missing"),
        ("{", "invalid_json"),
        ("[]", "invalid_structure"),
        ('{"entries": []}', "invalid_structure"),
    ],
)
def test_review_expiry_gate_reports_bad_registry_without_crashing(
    tmp_path, contents, reason
) -> None:
    path = tmp_path / gate_evaluators.SCRIPTS_LIFECYCLE_REGISTRY_JSON
    if contents is not None:
        path.parent.mkdir(parents=True)
        path.write_text(contents, encoding="utf-8")
    gate = gate_evaluators._scripts_review_expiry_gate(
        repo_root=tmp_path,
        scorecard=_review_expiry_scorecard(1),
        today=date(2026, 10, 21),
    )
    assert gate.status == "fail"
    assert gate.metric == "required_json_input"
    assert gate.current == reason


def test_review_expiry_gate_reports_unreadable_registry(tmp_path, monkeypatch) -> None:
    def unreadable(*args):
        raise PermissionError("read denied")

    monkeypatch.setattr(gate_evaluators, "_load_json", unreadable)
    gate = gate_evaluators._scripts_review_expiry_gate(
        repo_root=tmp_path,
        scorecard=_review_expiry_scorecard(1),
        today=date(2026, 10, 21),
    )
    assert gate.status == "fail"
    assert gate.current == "unreadable"


@pytest.mark.parametrize(
    "failure",
    [ValueError("bad registry"), OSError("unreadable"), yaml.YAMLError("bad YAML")],
)
def test_bad_initial_registry_does_not_hide_other_budget_growth(
    tmp_path, monkeypatch, failure
) -> None:
    def baseline(root, ref, path):
        if path == gate_evaluators.DEBT_SCORECARD_PATH:
            return {"family": {"max_count": 1}}
        raise failure

    current = _review_expiry_scorecard(1)
    current["family"] = {"max_count": 2}
    monkeypatch.setattr(gate_evaluators, "_load_yaml_from_git_ref", baseline)
    monkeypatch.setattr(gate_evaluators, "_load_yaml", lambda *args: current)
    gate = gate_evaluators._debt_scorecard_budget_no_growth_gate(
        repo_root=tmp_path,
        changed_from_ref="origin/main",
    )
    assert gate.status == "fail"
    assert gate.current["family.max_count"] == {"from": 1, "to": 2}
    for path in gate_evaluators.REVIEW_EXPIRY_METRIC_PATHS:
        assert gate.current[f"{path}.max_count"] == {"from": None, "to": 1}


@pytest.mark.parametrize("raw", [None, "2026-02-30", "20261020"])
def test_review_expiry_gate_cannot_hide_debt_with_invalid_dates(
    tmp_path, monkeypatch, raw
) -> None:
    monkeypatch.setattr(
        gate_evaluators,
        "_load_json",
        lambda *args: {
            "entries": {"scripts/old.py": {"review_by": raw}},
        },
    )
    gate = gate_evaluators._scripts_review_expiry_gate(
        repo_root=tmp_path,
        scorecard=_review_expiry_scorecard(1),
        today=date(2026, 10, 21),
    )
    assert gate.status == "fail"


@pytest.mark.parametrize("limit", [None, True, 1.0, -1, 2])
def test_review_expiry_gate_rejects_invalid_or_divergent_budgets(
    tmp_path, monkeypatch, limit
) -> None:
    monkeypatch.setattr(gate_evaluators, "_load_json", lambda *args: {"entries": {}})
    scorecard = _review_expiry_scorecard(1)
    scorecard["governance"]["coarse_budgets"]["expired_review_by_count"][
        "max_count"
    ] = limit
    assert (
        gate_evaluators._scripts_review_expiry_gate(
            repo_root=tmp_path,
            scorecard=scorecard,
            today=date(2026, 10, 21),
        ).status
        == "fail"
    )


@pytest.mark.parametrize("raised_path", gate_evaluators.REVIEW_EXPIRY_METRIC_PATHS)
def test_review_expiry_budget_increase_fails_even_if_count_unchanged(
    raised_path,
) -> None:
    baseline = _review_expiry_scorecard(172)
    current = deepcopy(baseline)
    node = current
    for part in raised_path.split("."):
        node = node[part]
    node["max_count"] = 173
    assert gate_evaluators._budget_growth_increases(
        baseline_payload=baseline,
        current_payload=current,
    ) == {f"{raised_path}.max_count": {"from": 172, "to": 173}}


@pytest.mark.parametrize(
    ("base_count", "live_count", "budget", "status"),
    [
        (1, 1, 1, "pass"),
        (1, 1, 2, "fail"),
        (1, 2, 2, "fail"),
    ],
)
def test_review_expiry_first_freeze_requires_base_and_live_fact(
    tmp_path,
    monkeypatch,
    base_count,
    live_count,
    budget,
    status,
) -> None:
    monkeypatch.setattr(
        gate_evaluators,
        "datetime",
        SimpleNamespace(
            now=lambda tz: datetime(2026, 10, 21, tzinfo=UTC),
        ),
    )

    def registry(count):
        return {
            "entries": {
                f"scripts/old{i}.py": {"review_by": "2000-01-01"} for i in range(count)
            }
        }

    monkeypatch.setattr(
        gate_evaluators,
        "_load_yaml_from_git_ref",
        lambda root, ref, path: (
            {} if path == gate_evaluators.DEBT_SCORECARD_PATH else registry(base_count)
        ),
    )
    monkeypatch.setattr(
        gate_evaluators, "_load_json", lambda *args: registry(live_count)
    )
    monkeypatch.setattr(
        gate_evaluators, "_load_yaml", lambda *args: _review_expiry_scorecard(budget)
    )
    assert (
        gate_evaluators._debt_scorecard_budget_no_growth_gate(
            repo_root=tmp_path,
            changed_from_ref="origin/main",
        ).status
        == status
    )


def _patch_both(monkeypatch: pytest.MonkeyPatch, name: str, value: object) -> None:
    """Patch a helper on both modules that expose it.

    ``debt_governance_gate_evaluators`` re-exports the gate helpers via
    ``from report_debt_governance_gates import *`` and resolves them in its own
    module namespace. Patching only ``report_debt_governance_gates`` therefore
    does not reach the evaluator functions, so we rebind both bindings.
    """
    monkeypatch.setattr(gates, name, value, raising=False)
    monkeypatch.setattr(gate_evaluators, name, value, raising=False)


@pytest.mark.parametrize(("expired", "exit_code"), [(1, 0), (2, 1)])
def test_source_only_cli_checks_live_review_expiry_without_generated_inputs(
    tmp_path,
    monkeypatch,
    expired,
    exit_code,
) -> None:
    from scripts.engineering.qa import debt_governance_gate_report as cli
    from scripts.engineering.repo import check_scripts_inventory as inventory

    registry_path = tmp_path / gate_evaluators.SCRIPTS_LIFECYCLE_REGISTRY_JSON
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(
        json.dumps(
            {
                "entries": {
                    f"scripts/old{i}.py": {"review_by": "2026-10-20"}
                    for i in range(expired)
                }
            }
        ),
        encoding="utf-8",
    )

    def authored_json(root, path):
        assert path == gate_evaluators.SCRIPTS_LIFECYCLE_REGISTRY_JSON
        return json.loads((root / path).read_text(encoding="utf-8"))

    _patch_both(monkeypatch, "_load_json", authored_json)
    monkeypatch.setattr(
        inventory,
        "datetime",
        SimpleNamespace(
            now=lambda tz: datetime(2026, 10, 21, tzinfo=UTC),
        ),
    )
    monkeypatch.setattr(
        gates, "_collect_changed_paths", lambda *a, **k: {registry_path.name}
    )
    monkeypatch.setattr(gates, "_debt_scorecard_gates", lambda: [])
    monkeypatch.setattr(
        gates,
        "_debt_scorecard_budget_no_growth_gate",
        lambda **k: gates.Gate("no_growth", "pass", "count", 0, 0, "source", "none"),
    )
    monkeypatch.setattr(gates, "_load_yaml", lambda *a: _review_expiry_scorecard(1))
    monkeypatch.setattr(gates, "_runtime_uuid_gates", lambda *a: [])
    monkeypatch.setattr(
        gates,
        "build_contract_registry_dq_diagnostics",
        lambda *a: {"blocking_issue_count": 0},
    )
    payload = gates.build_source_payload(
        repo_root=tmp_path, changed_from_ref="origin/main"
    )
    expiry = next(
        row for row in payload["gates"] if row["metric"] == "expired_review_by_count"
    )
    assert expiry["current"] == expired
    assert payload["summary"]["failing_gates"] == (
        ["scripts_review_expiry_ratchet"] if exit_code else []
    )
    assert (
        cli.main(
            [
                "--source-only",
                "--check",
                "--changed-from-ref",
                "origin/main",
                "--repo-root",
                str(tmp_path),
            ]
        )
        == exit_code
    )


def test_release_review_freshness_gate_passes_for_recent_live_review() -> None:
    """Verify release review freshness gate passes for recent live review."""
    gate = gates._release_review_freshness_gate(
        {
            "mode": "live_review",
            "status": "passed",
            "generated_at": "2026-06-04T15:01:29Z",
        },
        now=datetime(2026, 6, 17, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "pass"
    assert gate.name == "observability_release_review_freshness"
    assert gate.current == 13
    assert gate.limit == gates.RELEASE_REVIEW_MAX_AGE_DAYS


def test_release_review_freshness_gate_fails_for_stale_live_review() -> None:
    """Verify release review freshness gate fails for stale live review."""
    gate = gates._release_review_freshness_gate(
        {
            "mode": "live_review",
            "status": "passed",
            "generated_at": "2026-06-04T15:01:29Z",
        },
        now=datetime(2026, 7, 6, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == 32


def test_release_review_freshness_gate_fails_for_invalid_generated_at() -> None:
    """Verify release review freshness gate fails for invalid generated at."""
    gate = gates._release_review_freshness_gate(
        {"mode": "live_review", "status": "passed", "generated_at": "not-a-timestamp"},
        now=datetime(2026, 6, 17, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == "missing_or_invalid"


def test_release_review_freshness_gate_fails_for_future_generated_at() -> None:
    """Verify release review freshness gate fails for future generated at."""
    gate = gates._release_review_freshness_gate(
        {
            "mode": "live_review",
            "status": "passed",
            "generated_at": "2026-06-18T00:00:00Z",
        },
        now=datetime(2026, 6, 17, 0, 0, 0, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == -1


def test_release_gate_status_prioritizes_failures_over_warnings() -> None:
    assert gates._release_gate_status({"pass": 25, "warn": 0, "fail": 1}) == "failing"
    assert gates._release_gate_status({"pass": 25, "warn": 1, "fail": 0}) == "warning"
    assert gates._release_gate_status({"pass": 26, "warn": 0, "fail": 0}) == "passing"


def test_module_coverage_source_tree_hash_gate_fails_for_stale_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_both(
        monkeypatch,
        "_refresh_existing_inventory_source_tree",
        lambda payload, *, repo_root: {"source_tree_sha256": "live-source-hash"},
    )

    gate = gates._module_coverage_source_tree_hash_gate(
        {"source_tree_sha256": "committed-source-hash"},
        repo_root=gates.PROJECT_ROOT,
    )

    assert gate.name == "module_coverage_source_tree_hash_current"
    assert gate.status == "fail"
    assert gate.current == "live-source-hash"
    assert gate.limit == "committed-source-hash"


def test_module_coverage_source_tree_hash_gate_passes_for_current_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_both(
        monkeypatch,
        "_refresh_existing_inventory_source_tree",
        lambda payload, *, repo_root: {"source_tree_sha256": "live-source-hash"},
    )

    gate = gates._module_coverage_source_tree_hash_gate(
        {"source_tree_sha256": "live-source-hash"},
        repo_root=gates.PROJECT_ROOT,
    )

    assert gate.status == "pass"


def test_module_coverage_scorecard_coherence_gate_passes_when_metrics_align() -> None:
    gate = gates._module_coverage_scorecard_coherence_gate(
        {
            "metrics": {
                "source_module_count": 10,
                "unmeasured_module_count": 0,
                "uncovered_module_count": 0,
            },
            "source_artifacts": {
                "module_coverage_inventory": {"source_tree_sha256": "same-hash"}
            },
        },
        {
            "summary": {
                "source_module_count": 10,
                "unmeasured_module_count": 0,
                "uncovered_module_count": 0,
            },
            "source_tree_sha256": "same-hash",
        },
    )

    assert gate.status == "pass"


def test_module_coverage_scorecard_coherence_gate_fails_for_metric_drift() -> None:
    gate = gates._module_coverage_scorecard_coherence_gate(
        {
            "metrics": {
                "source_module_count": 11,
                "unmeasured_module_count": 1,
                "uncovered_module_count": 0,
            },
            "source_artifacts": {
                "module_coverage_inventory": {"source_tree_sha256": "stale-hash"}
            },
        },
        {
            "summary": {
                "source_module_count": 10,
                "unmeasured_module_count": 0,
                "uncovered_module_count": 0,
            },
            "source_tree_sha256": "live-hash",
        },
    )

    assert gate.status == "fail"


def test_compatibility_scorecard_coherence_gate_passes_when_metrics_align() -> None:
    gate = gates._compatibility_scorecard_coherence_gate(
        {
            "metrics": {
                "retained_entrypoint_count": 12,
                "retained_public_export_facade_count": 3,
                "twin_pair_count": 0,
            }
        },
        {
            "summary": {
                "retained_entrypoint_count": 12,
                "retained_public_export_facade_count": 3,
                "twin_pair_count": 0,
            }
        },
    )

    assert gate.status == "pass"


def test_compatibility_scorecard_coherence_gate_fails_for_metric_drift() -> None:
    gate = gates._compatibility_scorecard_coherence_gate(
        {
            "metrics": {
                "retained_entrypoint_count": 13,
                "retained_public_export_facade_count": 3,
                "twin_pair_count": 1,
            }
        },
        {
            "summary": {
                "retained_entrypoint_count": 12,
                "retained_public_export_facade_count": 3,
                "twin_pair_count": 0,
            }
        },
    )

    assert gate.status == "fail"


def test_remote_baseline_allows_branch_introduced_missing_artifacts() -> None:
    remote_baseline = {
        "artifacts": [
            {
                "path": "reports/quality/compatibility-importer-census.json",
                "required": True,
                "required_on_remote": False,
                "introduced_after_remote_main": True,
                "summary": {"available": False},
            },
            {
                "path": "reports/quality/module-coverage-inventory.json",
                "required": True,
                "required_on_remote": True,
                "introduced_after_remote_main": False,
                "summary": {"available": True},
            },
        ]
    }

    assert gates._unavailable_required_remote_baseline_artifacts(remote_baseline) == []


def test_remote_baseline_fails_for_missing_artifact_required_on_remote() -> None:
    remote_baseline = {
        "artifacts": [
            {
                "path": "reports/quality/module-coverage-inventory.json",
                "required": True,
                "required_on_remote": True,
                "introduced_after_remote_main": False,
                "summary": {"available": False},
            }
        ]
    }

    assert gates._unavailable_required_remote_baseline_artifacts(remote_baseline) == [
        remote_baseline["artifacts"][0]
    ]


def test_module_coverage_aggregate_residual_limits_returns_none_without_ratchets() -> (
    None
):
    assert gates._module_coverage_aggregate_residual_limits({}) is None


def test_module_coverage_aggregate_residual_limits_reads_reviewed_limits() -> None:
    limits = gates._module_coverage_aggregate_residual_limits(
        {
            "aggregate_residual_ratchets": {
                "unmeasured_module_count": {"max_count": 2},
                "uncovered_module_count": {"max_count": 5},
            }
        }
    )

    assert limits == {
        "unmeasured_module_count": 2,
        "uncovered_module_count": 5,
    }


def test_budget_growth_increases_flags_raised_scorecard_limits() -> None:
    increases = gates._budget_growth_increases(
        baseline_payload={
            "family": {
                "metrics": {
                    "size": {"max_count": 3},
                    "warnings": {"current_count": 2},
                }
            }
        },
        current_payload={
            "family": {
                "metrics": {
                    "size": {"max_count": 4},
                    "warnings": {"current_count": 10},
                }
            }
        },
    )

    assert increases == {"family.metrics.size.max_count": {"from": 3, "to": 4}}


def test_budget_growth_increases_ignores_flat_or_lower_limits() -> None:
    assert (
        gates._budget_growth_increases(
            baseline_payload={"family": {"metrics": {"size": {"max_count": 3}}}},
            current_payload={"family": {"metrics": {"size": {"max_count": 2}}}},
        )
        == {}
    )


def test_debt_scorecard_budget_no_growth_gate_fails_on_budget_increase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_both(
        monkeypatch,
        "_load_yaml_from_git_ref",
        lambda repo_root, ref, rel_path: {"family": {"max_count": 3}},
    )
    _patch_both(
        monkeypatch,
        "_load_yaml",
        lambda repo_root, rel_path: {"family": {"max_count": 4}},
    )

    gate = gates._debt_scorecard_budget_no_growth_gate(
        repo_root=gates.PROJECT_ROOT,
        changed_from_ref="origin/main",
    )

    assert gate.status == "fail"
    assert gate.current == {"family.max_count": {"from": 3, "to": 4}}


def test_flaky_untriaged_entries_require_triage_status() -> None:
    untriaged = gates._flaky_untriaged_entries(
        {
            "reviewed_flaky_tests": [
                {"nodeid": "tests/unit/test_a.py::test_ok", "triage_status": "fixed"},
                {"nodeid": "tests/unit/test_b.py::test_missing"},
                {
                    "nodeid": "tests/unit/test_c.py::test_unknown",
                    "triage_status": "unknown",
                },
            ]
        }
    )

    assert [entry["nodeid"] for entry in untriaged] == [
        "tests/unit/test_b.py::test_missing",
        "tests/unit/test_c.py::test_unknown",
    ]


def test_flaky_review_input_preflight_fails_closed_when_artifact_is_missing(
    tmp_path: Path,
) -> None:
    payload, gate = gates._load_json_input_with_preflight(
        tmp_path,
        gates.FLAKY_TEST_REVIEW_PATH,
        gate_name="flaky_test_review_input_preflight",
    )

    assert payload == {}
    assert gate.status == "fail"
    assert gate.current == "missing"
    assert gate.source_artifact == gates.FLAKY_TEST_REVIEW_PATH


def test_flaky_review_input_preflight_fails_closed_for_invalid_json(
    tmp_path: Path,
) -> None:
    review_path = tmp_path / gates.FLAKY_TEST_REVIEW_PATH
    review_path.parent.mkdir(parents=True)
    review_path.write_text("{not-json}\n", encoding="utf-8")

    payload, gate = gates._load_json_input_with_preflight(
        tmp_path,
        gates.FLAKY_TEST_REVIEW_PATH,
        gate_name="flaky_test_review_input_preflight",
    )

    assert payload == {}
    assert gate.status == "fail"
    assert gate.current == "invalid_json"


def test_flaky_review_input_preflight_fails_closed_for_non_object_json(
    tmp_path: Path,
) -> None:
    review_path = tmp_path / gates.FLAKY_TEST_REVIEW_PATH
    review_path.parent.mkdir(parents=True)
    review_path.write_text("[]\n", encoding="utf-8")

    payload, gate = gates._load_json_input_with_preflight(
        tmp_path,
        gates.FLAKY_TEST_REVIEW_PATH,
        gate_name="flaky_test_review_input_preflight",
    )

    assert payload == {}
    assert gate.status == "fail"
    assert gate.current == "invalid_top_level_type"


def test_flaky_review_input_preflight_fails_closed_when_artifact_is_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_os_error(
        _path: Path,
        *,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> str:
        del encoding, errors
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "read_text", _raise_os_error)

    payload, gate = gates._load_json_input_with_preflight(
        tmp_path,
        gates.FLAKY_TEST_REVIEW_PATH,
        gate_name="flaky_test_review_input_preflight",
    )

    assert payload == {}
    assert gate.status == "fail"
    assert gate.current == "unreadable"


def test_flaky_review_input_preflight_returns_payload_for_valid_object(
    tmp_path: Path,
) -> None:
    review_path = tmp_path / gates.FLAKY_TEST_REVIEW_PATH
    review_path.parent.mkdir(parents=True)
    review_path.write_text('{"summary": {"total_flaky": 0}}\n', encoding="utf-8")

    payload, gate = gates._load_json_input_with_preflight(
        tmp_path,
        gates.FLAKY_TEST_REVIEW_PATH,
        gate_name="flaky_test_review_input_preflight",
    )

    assert payload == {"summary": {"total_flaky": 0}}
    assert gate.status == "pass"
    assert gate.current == "available_valid_object"


@pytest.mark.generated_artifact
def test_build_payload__missing_flaky_review__fails_gate_without_crashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_coverage = gates._load_json(
        gates.PROJECT_ROOT,
        "reports/quality/module-coverage-inventory.json",
    )
    monkeypatch.setattr(
        gates,
        "FLAKY_TEST_REVIEW_PATH",
        "reports/quality/__missing_flaky_test_review__.json",
    )
    monkeypatch.setattr(
        gates,
        "_refresh_existing_inventory_source_tree",
        lambda payload, *, repo_root: {
            "source_tree_sha256": module_coverage["source_tree_sha256"]
        },
    )
    monkeypatch.setattr(
        gates,
        "_artifact_matches_builder",
        lambda *, repo_root, rel_path, payload_builder: True,
    )
    monkeypatch.setattr(
        gates,
        "_hotspot_family_baseline_artifact_matches_builder",
        lambda *, repo_root: True,
    )
    monkeypatch.setattr(
        gates,
        "_remote_main_baseline_artifact_matches_builder",
        lambda *, repo_root: True,
    )

    payload = gates.build_payload(repo_root=gates.PROJECT_ROOT)

    preflight_gate = next(
        row
        for row in payload["gates"]
        if row["name"] == "flaky_test_review_input_preflight"
    )
    assert preflight_gate["status"] == "fail"
    assert preflight_gate["current"] == "missing"
    assert payload["summary"]["release_gate_status"] == "failing"


@pytest.mark.generated_artifact
def test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    # Force the non-test branch so module_coverage_inventory staleness is
    # evaluated from the live source-tree hash gate (not short-circuited).
    monkeypatch.delitem(sys.modules, "pytest", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    _patch_both(
        monkeypatch,
        "_refresh_existing_inventory_source_tree",
        lambda payload, *, repo_root: {"source_tree_sha256": "stale-source-hash"},
    )
    _patch_both(
        monkeypatch,
        "_artifact_matches_builder",
        lambda *, repo_root, rel_path, payload_builder: True,
    )
    # Avoid full hotspot AST census / remote-main git work; this test only
    # asserts release failure from a stale module-coverage inventory hash.
    _patch_both(
        monkeypatch,
        "_hotspot_family_baseline_artifact_matches_builder",
        lambda *, repo_root: True,
    )
    _patch_both(
        monkeypatch,
        "_remote_main_baseline_artifact_matches_builder",
        lambda *, repo_root: True,
    )

    payload = gates.build_payload(repo_root=gates.PROJECT_ROOT)
    summary = payload["summary"]
    assert isinstance(summary, dict)

    failing_gates = summary["failing_gates"]
    assert isinstance(failing_gates, list)
    assert "module_coverage_source_tree_hash_current" in failing_gates
    assert "generated_artifact_drift" in failing_gates
    assert summary["release_gate_status"] == "failing"


@pytest.mark.generated_artifact
def test_build_payload_tolerates_unavailable_remote_main_baseline_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_coverage = gates._load_json(
        gates.PROJECT_ROOT, "reports/quality/module-coverage-inventory.json"
    )
    assert isinstance(module_coverage, dict)
    _patch_both(
        monkeypatch,
        "_refresh_existing_inventory_source_tree",
        lambda payload, *, repo_root: {
            "source_tree_sha256": module_coverage["source_tree_sha256"]
        },
    )
    _patch_both(
        monkeypatch,
        "_artifact_matches_builder",
        lambda *, repo_root, rel_path, payload_builder: True,
    )
    _patch_both(
        monkeypatch,
        "_hotspot_family_baseline_artifact_matches_builder",
        lambda *, repo_root: True,
    )
    _patch_both(
        monkeypatch,
        "_config_surface_backlog_matches_builder",
        lambda *, repo_root: True,
    )
    monkeypatch.setattr(
        gates.report_architecture_debt_remote_main_baseline,
        "build_payload",
        lambda **kwargs: (_ for _ in ()).throw(
            subprocess.CalledProcessError(
                returncode=1,
                cmd=["git", "ls-remote", "origin", "refs/heads/main"],
            )
        ),
    )

    payload = gates.build_payload(repo_root=gates.PROJECT_ROOT)
    summary = payload["summary"]
    assert isinstance(summary, dict)

    failing_gates = summary["failing_gates"]
    assert isinstance(failing_gates, list)
    assert "generated_artifact_drift" not in failing_gates


@pytest.mark.generated_artifact
def test_build_payload_marks_config_surface_backlog_drift_as_stale_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_both(
        monkeypatch,
        "_refresh_existing_inventory_source_tree",
        lambda payload, *, repo_root: {"source_tree_sha256": "live-source-hash"},
    )
    _patch_both(
        monkeypatch,
        "build_backlog",
        lambda: {"schema_version": "drifted-live-backlog"},
    )
    # Avoid full hotspot AST census; this test only asserts config-backlog drift.
    _patch_both(
        monkeypatch,
        "_hotspot_family_baseline_artifact_matches_builder",
        lambda *, repo_root: True,
    )

    payload = gates.build_payload(repo_root=gates.PROJECT_ROOT)
    summary = payload["summary"]
    assert isinstance(summary, dict)
    assert payload["stale_artifacts"]["config_surface_backlog"] is True
    assert "generated_artifact_drift" in summary["failing_gates"]


@pytest.mark.generated_artifact
def test_build_payload_marks_in_budget_hotspot_census_drift_as_stale_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale hotspot census must fail even when its budget warnings remain zero."""
    module_coverage = gates._load_json(
        gates.PROJECT_ROOT,
        "reports/quality/module-coverage-inventory.json",
    )
    _patch_both(
        monkeypatch,
        "_refresh_existing_inventory_source_tree",
        lambda payload, *, repo_root: {
            "source_tree_sha256": module_coverage["source_tree_sha256"]
        },
    )
    _patch_both(
        monkeypatch,
        "_artifact_matches_builder",
        lambda *, repo_root, rel_path, payload_builder: True,
    )
    _patch_both(
        monkeypatch,
        "_hotspot_family_baseline_artifact_matches_builder",
        lambda *, repo_root: False,
    )

    # Isolate census-drift failure from the live budget residual: force the
    # committed hotspot summary into an in-budget state (budget_warnings=0).
    original_load_json = gates._load_json

    def _load_json_in_budget_hotspot(
        repo_root: Path, relative_path: str, *args: object, **kwargs: object
    ) -> object:
        payload = original_load_json(repo_root, relative_path, *args, **kwargs)
        if relative_path != gates.HOTSPOT_FAMILY_BASELINE_JSON:
            return payload
        if not isinstance(payload, dict):
            return payload
        forced = dict(payload)
        summary = dict(forced.get("summary") or {})
        summary["budget_warnings"] = 0
        forced["summary"] = summary
        return forced

    _patch_both(monkeypatch, "_load_json", _load_json_in_budget_hotspot)

    payload = gates.build_payload(repo_root=gates.PROJECT_ROOT)
    summary = payload["summary"]
    assert isinstance(summary, dict)

    hotspot_gate = next(
        row
        for row in payload["gates"]
        if row["name"] == "hotspot_family_baseline_budget_warnings"
    )
    assert hotspot_gate["current"] == 0
    assert hotspot_gate["status"] == "pass"
    assert payload["stale_artifacts"]["hotspot_family_baseline"] is True
    assert "generated_artifact_drift" in summary["failing_gates"]
    assert summary["release_gate_status"] == "failing"


def test_remote_main_baseline_stale_check_ignores_revision_metadata_only(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_dir = tmp_path / "reports" / "quality"
    baseline_dir.mkdir(parents=True)
    committed = {
        "schema_version": 1,
        "generated_by": "scripts.engineering.qa.report_architecture_debt_remote_main_baseline",
        "evidence_source": "remote_main_git_tree",
        "remote": "origin",
        "branch": "main",
        "remote_main_ref": "refs/heads/main",
        "remote_main_sha": "old",
        "local_tracking_ref": "origin/main",
        "local_tracking_ref_sha": "old",
        "local_tracking_ref_matches_remote": True,
        "generator_commands": [
            "python -m scripts.engineering.qa report-module-coverage --check"
        ],
        "artifacts": [
            {
                "path": "reports/quality/module-coverage-inventory.json",
                "source_revision": "old",
                "blob_sha256": "same-blob",
                "required": True,
                "summary": {"available": True, "source_tree_sha256": "same-source"},
            }
        ],
    }
    live = {
        **committed,
        "remote_main_sha": "new",
        "local_tracking_ref_sha": "new",
        "artifacts": [
            {
                **committed["artifacts"][0],
                "source_revision": "new",
            }
        ],
    }
    (baseline_dir / "architecture-debt-remote-main-baseline.json").write_text(
        json.dumps(committed),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        gates.report_architecture_debt_remote_main_baseline,
        "build_payload",
        lambda **kwargs: live,
    )

    assert (
        gates._remote_main_baseline_artifact_matches_builder(repo_root=tmp_path) is True
    )


def test_remote_main_baseline_stale_when_live_tracking_ref_mismatches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_dir = tmp_path / "reports" / "quality"
    baseline_dir.mkdir(parents=True)
    committed = {
        "schema_version": 1,
        "generated_by": "scripts.engineering.qa.report_architecture_debt_remote_main_baseline",
        "evidence_source": "remote_main_git_tree",
        "remote": "origin",
        "branch": "main",
        "remote_main_ref": "refs/heads/main",
        "remote_main_sha": "same",
        "local_tracking_ref": "origin/main",
        "local_tracking_ref_sha": "same",
        "local_tracking_ref_matches_remote": True,
        "generator_commands": [
            "python -m scripts.engineering.qa report-module-coverage --check"
        ],
        "artifacts": [
            {
                "path": "reports/quality/module-coverage-inventory.json",
                "source_revision": "same",
                "blob_sha256": "same-blob",
                "required": True,
                "summary": {"available": True, "source_tree_sha256": "same-source"},
            }
        ],
    }
    live = {**committed, "local_tracking_ref_matches_remote": False}
    (baseline_dir / "architecture-debt-remote-main-baseline.json").write_text(
        json.dumps(committed),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        gates.report_architecture_debt_remote_main_baseline,
        "build_payload",
        lambda **kwargs: live,
    )

    assert (
        gates._remote_main_baseline_artifact_matches_builder(repo_root=tmp_path)
        is False
    )


def test_render_markdown_separates_weighted_score_from_release_gate_status() -> None:
    payload = {
        "summary": {
            "gate_count": 1,
            "pass_count": 0,
            "warn_count": 0,
            "fail_count": 1,
            "release_gate_status": "failing",
            "architecture_quality_scorecard_integral_score": 7.98,
            "architecture_quality_scorecard_interpretation": (
                "satisfactory_system_refactoring_required"
            ),
        },
        "gates": [
            {
                "name": "generated_artifact_drift",
                "status": "fail",
                "metric": "stale_artifact_count",
                "current": 1,
                "limit": 0,
                "source_artifact": "reports/quality/*.json",
            }
        ],
    }

    markdown = gates.render_markdown(payload)

    assert "release_gate_status: `failing`" in markdown
    assert "architecture_quality_scorecard_integral_score: `7.98`" in markdown


def test_check_artifacts_can_skip_artifact_comparison_for_changed_path_gate(
    tmp_path,
) -> None:
    payload = {
        "summary": {
            "gate_count": 1,
            "pass_count": 1,
            "warn_count": 0,
            "fail_count": 0,
            "release_gate_status": "passing",
            "architecture_quality_scorecard_integral_score": 7.98,
            "architecture_quality_scorecard_interpretation": (
                "satisfactory_system_refactoring_required"
            ),
        },
        "gates": [],
    }

    errors = gates._check_artifacts(
        payload,
        json_out=tmp_path / "missing.json",
        md_out=tmp_path / "missing.md",
        compare_artifacts=False,
    )

    assert errors == []


def test_observability_touched_metric_review_gate_passes_without_metric_changes() -> (
    None
):
    """Verify observability touched metric review gate passes without metric changes."""
    gate = gates._observability_touched_metric_review_gate(
        {
            "generated_at": "2026-06-04T15:01:29Z",
            "status": "passed",
        },
        changed_paths={"src/bioetl/interfaces/cli/main.py"},
        trigger_paths={"src/bioetl/infrastructure/observability/server.py"},
        now=datetime(2026, 6, 17, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "pass"
    assert gate.current == 0


def test_collect_metric_change_trigger_paths_includes_dashboard_and_alert_surfaces() -> (
    None
):
    trigger_paths = gates._collect_metric_change_trigger_paths(
        {
            "runtime_emitters": {
                "bioetl_example_total": ["src/bioetl/observability/example.py"]
            },
            "docs_mentions": {
                "bioetl_example_total": ["grafana/dashboards/example.json"]
            },
            "rules_mentions": {
                "bioetl_example_total": ["grafana/prometheus-rules/example.yml"]
            },
        },
        {
            "runtime_cardinality_review": {
                "live_evidence": {
                    "touched_metric_change_gate": {
                        "changed_path_trigger_fields": [
                            "runtime_emitters",
                            "docs_mentions",
                            "rules_mentions",
                        ],
                        "changed_path_trigger_static_paths": [
                            "configs/quality/observability_metric_declarations.yaml"
                        ],
                        "changed_path_trigger_prefixes": [
                            "grafana/dashboards/",
                            "grafana/prometheus-rules/",
                        ],
                    }
                }
            }
        },
    )

    assert {
        "src/bioetl/observability/example.py",
        "grafana/dashboards/example.json",
        "grafana/prometheus-rules/example.yml",
        "configs/quality/observability_metric_declarations.yaml",
        "grafana/dashboards/",
        "grafana/prometheus-rules/",
    } <= trigger_paths


def test_observability_touched_metric_review_gate_matches_static_prefixes() -> None:
    """Verify observability touched metric review gate matches static prefixes."""
    gate = gates._observability_touched_metric_review_gate(
        {
            "generated_at": "2026-06-04T15:01:29Z",
            "status": "passed",
        },
        changed_paths={"grafana/dashboards/new-metric.json"},
        trigger_paths={"grafana/dashboards/"},
        now=datetime(2026, 7, 6, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == 1


def test_observability_touched_metric_inventory_gate_passes_without_metric_changes() -> (
    None
):
    gate = gates._observability_touched_metric_inventory_gate(
        {"declared_metrics": []},
        changed_paths={"docs/README.md"},
        trigger_paths={"grafana/dashboards/"},
        repo_root=gates.PROJECT_ROOT,
        current_inventory={"declared_metrics": []},
    )

    assert gate.status == "pass"
    assert gate.current == 0


def test_observability_touched_metric_inventory_gate_fails_for_stale_artifact() -> None:
    gate = gates._observability_touched_metric_inventory_gate(
        {"declared_metrics": ["bioetl_old_total"]},
        changed_paths={"grafana/prometheus-rules/new-rule.yml"},
        trigger_paths={"grafana/prometheus-rules/"},
        repo_root=gates.PROJECT_ROOT,
        current_inventory={"declared_metrics": ["bioetl_new_total"]},
    )

    assert gate.status == "fail"
    assert gate.current is False
    assert gate.limit is True


def test_observability_touched_metric_review_gate_fails_for_stale_review() -> None:
    """Verify observability touched metric review gate fails for stale review."""
    gate = gates._observability_touched_metric_review_gate(
        {
            "generated_at": "2026-06-04T15:01:29Z",
            "status": "passed",
        },
        changed_paths={"src/bioetl/infrastructure/observability/server.py"},
        trigger_paths={"src/bioetl/infrastructure/observability/server.py"},
        now=datetime(2026, 7, 6, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == 1


def test_observability_touched_metric_review_gate_fails_for_degraded_review() -> None:
    """Verify observability touched metric review gate fails for degraded review."""
    gate = gates._observability_touched_metric_review_gate(
        {
            "generated_at": "2026-06-04T15:01:29Z",
            "status": "degraded",
        },
        changed_paths={"configs/quality/observability_metric_declarations.yaml"},
        trigger_paths={"configs/quality/observability_metric_declarations.yaml"},
        now=datetime(2026, 6, 17, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == 1


def test_new_max_count_freezes_recorded_current_without_raising_it() -> None:
    baseline = {"metrics": {"public_export_facade_count": {"current_count": 3}}}
    frozen = {
        "metrics": {"public_export_facade_count": {"current_count": 3, "max_count": 3}}
    }
    raised = {
        "metrics": {"public_export_facade_count": {"current_count": 4, "max_count": 4}}
    }
    path = "metrics.public_export_facade_count.max_count"
    assert gate_evaluators._new_max_count_freezes_recorded_current(
        path,
        baseline_payload=baseline,
        current_payload=frozen,
        current_value=3,
    )
    assert not gate_evaluators._new_max_count_freezes_recorded_current(
        path,
        baseline_payload=baseline,
        current_payload=raised,
        current_value=4,
    )


def test_stored_public_surface_max_count_is_independent_of_live_census() -> None:
    scorecard = {
        "sanctioned_public_entrypoint_governance": {
            "metrics": {
                "public_export_facade_count": {"current_count": 9, "max_count": 3},
                "public_entrypoint_count": {"current_count": 20, "max_count": 12},
            }
        }
    }
    assert (
        gate_evaluators._stored_shrink_only_max_count(
            scorecard, "public_export_facade_count"
        )
        == 3
    )
    assert (
        gate_evaluators._stored_shrink_only_max_count(
            scorecard, "public_entrypoint_count"
        )
        == 12
    )


@pytest.mark.parametrize(
    "mode,status",
    [
        ("local_cardinality_fallback", "passed"),
        ("local_cardinality_fallback", "degraded"),
        ("live_review_unavailable", "degraded"),
        ("live_review", "failed"),
        ("live_review", "degraded"),
        (None, "passed"),
        ("live_review", None),
    ],
)
def test_release_review_freshness_rejects_non_release_evidence(mode, status):
    """Verify release review freshness rejects non release evidence."""
    gate = gates._release_review_freshness_gate(
        {"mode": mode, "status": status, "generated_at": "2026-06-17T00:00:00Z"},
        now=datetime(2026, 6, 17, tzinfo=UTC),
    )
    assert gate.status == "fail"
