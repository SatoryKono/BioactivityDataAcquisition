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
"""Closeout guards for observability/dashboard/export issues #5716-#5728."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import pytest
import yaml

from bioetl.application.services.export_models import ExportOptions, ExportResult
from bioetl.domain.ports.export import (
    ExportJobStatus,
    ExportRedactionProfile,
    ExportRole,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = (
    ROOT
    / "reports"
    / "quality"
    / "observability-export-dashboard-rollout-closeout.json"
)
ERROR_CATALOG = ROOT / "configs" / "contracts" / "errors" / "error_catalog.yaml"
ROLLOUT_CONTRACT = (
    ROOT / "docs" / "04-reference" / "contracts" / "observability-rollout-contracts.md"
)
RBAC_MATRIX = ROOT / "docs" / "security" / "rbac-matrix.md"
EXPORT_POLICY = ROOT / "docs" / "security" / "export-policy.md"
TESTS_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
DASHBOARD_DIR = ROOT / "grafana" / "dashboards"
PROM_RULES_DIR = ROOT / "grafana" / "prometheus-rules"

EXPECTED_ISSUES = set(range(5716, 5729))
EXPECTED_PROGRAM_ORDER = [
    5717,
    5718,
    5719,
    5720,
    5721,
    5722,
    5723,
    5724,
    5725,
    5726,
    5727,
    5728,
    5716,
]
FORBIDDEN_PROM_LABELS = {
    "run_id",
    "record_id",
    "payload_hash",
    "manifest_id",
    "execution_fingerprint",
    "file_path",
}
_PROMQL_SELECTOR_RE = re.compile(r"([a-zA-Z_:][a-zA-Z0-9_:]*)\{([^{}]*)\}")
_LABEL_MATCHER_RE = re.compile(r'([a-zA-Z_]\w*)\s*(=~|=|!=|!~)\s*"')


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _iter_dashboard_promql() -> list[tuple[str, str, str]]:
    expressions: list[tuple[str, str, str]] = []
    for dashboard_path in sorted(DASHBOARD_DIR.glob("*.json")):
        dashboard = _load_json(dashboard_path)
        panels = list(dashboard.get("panels", []))
        for panel in panels:
            if not isinstance(panel, dict):
                continue
            title = str(panel.get("title", ""))
            targets = panel.get("targets", [])
            if not isinstance(targets, list):
                continue
            for target in targets:
                if not isinstance(target, dict):
                    continue
                expr = target.get("expr")
                if isinstance(expr, str) and expr.strip():
                    expressions.append((dashboard_path.name, title, expr))
    return expressions


def _iter_rule_promql() -> list[tuple[str, str, str]]:
    expressions: list[tuple[str, str, str]] = []
    for rules_path in sorted(PROM_RULES_DIR.glob("*.yml")):
        payload = _load_yaml(rules_path)
        for group in payload.get("groups", []):
            if not isinstance(group, dict):
                continue
            group_name = str(group.get("name", rules_path.name))
            for rule in group.get("rules", []):
                if not isinstance(rule, dict):
                    continue
                expr = rule.get("expr")
                if isinstance(expr, str) and expr.strip():
                    rule_name = str(rule.get("alert") or rule.get("record") or "<rule>")
                    expressions.append((group_name, rule_name, expr))
    return expressions


def test_prometheus_rules_directory_contains_no_active_backups() -> None:
    """Prometheus rule directories must not carry tracked backup copies."""
    forbidden = sorted(
        path.name
        for path in PROM_RULES_DIR.iterdir()
        if path.is_file()
        and (
            path.suffix == ".bak"
            or path.name.endswith(".yml.bak")
            or "fixed" in path.name.lower()
            or "scratch" in path.name.lower()
        )
    )
    assert forbidden == []


def _forbidden_selector_labels(expr: str) -> set[str]:
    labels: set[str] = set()
    for _metric, selector in _PROMQL_SELECTOR_RE.findall(expr):
        labels.update(
            label
            for label, _operator in _LABEL_MATCHER_RE.findall(selector)
            if label in FORBIDDEN_PROM_LABELS
        )
    return labels


def test_closeout_artifact_covers_requested_observability_rollout_issues() -> None:
    payload = _load_json(CLOSEOUT)

    assert (
        payload["schema_version"]
        == "observability-export-dashboard-rollout-closeout-v1"
    )
    assert payload["debt_budget_outcome"] == "reduced_or_unchanged"
    assert payload["program_order"] == EXPECTED_PROGRAM_ORDER
    assert {issue["number"] for issue in payload["issues"]} == EXPECTED_ISSUES
    assert all(issue["status"] == "closed-ready" for issue in payload["issues"])

    for issue in payload["issues"]:
        for relative_path in issue["evidence"]:
            assert (ROOT / relative_path).exists(), (
                f"Missing evidence for #{issue['number']}: {relative_path}"
            )

    for name, ratchet in payload["ratchets"].items():
        assert ratchet["current"] <= ratchet["max"], name


def test_error_catalog_is_machine_readable_stable_and_bounded() -> None:
    payload = _load_yaml(ERROR_CATALOG)

    assert payload["schema_version"] == "error-catalog-v1"
    assert payload["policy"]["grouping_contract"] == "canonical_code_only"
    assert payload["policy"]["severity_changes_require_tests"] is True
    assert payload["policy"]["unknown_fallback_code"] == "SYS-UNKNOWN"
    assert set(payload["domains"]) >= {
        "SRC",
        "NET",
        "RATE",
        "DQ",
        "ENR",
        "XVAL",
        "SILVER",
        "GOLD",
        "QTN",
        "CFG",
        "EXP",
        "SYS",
    }

    codes = payload["codes"]
    seen_codes: set[str] = set()
    for row in codes:
        assert row["code"] not in seen_codes
        seen_codes.add(row["code"])
        assert row["domain"] in payload["domains"]
        assert row["severity"] in {"warning", "error", "critical"}
        assert isinstance(row["retryable"], bool)
        assert row["safe_user_message"].strip()
        assert row["internal_template"].strip()
        assert row["owner_area"].strip()
        assert (ROOT / row["runbook"]).exists(), row["runbook"]
        assert row["maps_error_types"]

    assert "EXP-AUTHZ-DENIED" in seen_codes
    assert "EXP-EXPIRED" in seen_codes
    assert payload["legacy_mappings"]["PermissionError"] == "EXP-AUTHZ-DENIED"


def test_export_contract_exposes_audit_checksum_expiry_and_redaction_controls() -> None:
    options = ExportOptions()
    result = ExportResult(
        table_name="chembl.activity",
        layer="silver",
        format="csv",
        output_path=None,
        row_count=0,
    )

    assert {item.value for item in ExportJobStatus} == {
        "requested",
        "authorized",
        "materialized",
        "expired",
        "revoked",
        "failed",
    }
    assert {item.value for item in ExportRole} == {
        "viewer",
        "investigator",
        "exporter",
        "admin",
    }
    assert {item.value for item in ExportRedactionProfile} == {"default", "none"}
    assert options.role == "viewer"
    assert options.redaction_profile == "default"
    assert result.redacted_columns == ()

    export_policy = EXPORT_POLICY.read_text(encoding="utf-8")
    for token in (
        "audit_ref",
        "checksum_manifest_path",
        "expires_at",
        "redaction_profile",
        "Expired exports must be denied",
    ):
        assert token in export_policy


def test_rollout_docs_preserve_prompt_narrowing_and_projection_boundaries() -> None:
    contract = ROLLOUT_CONTRACT.read_text(encoding="utf-8")
    rbac = RBAC_MATRIX.read_text(encoding="utf-8")

    assert "append-only" in contract
    assert "RunLedger/control-plane event log" in contract
    assert "not BioETL data Bronze" in contract
    assert "SQL migrations are not part of this rollout" in contract
    assert "run_id" in contract and "forbidden as a Prometheus label" in contract
    assert "`export_jobs`" in contract
    assert "raw Bronze/Silver storage directly" in contract

    assert "hidden" in rbac.lower()
    assert "security boundary" in rbac.lower()
    assert "Grafana MUST NOT expose raw storage" in rbac
    assert "Service account tokens and secrets MUST NOT be committed" in rbac


def test_dashboard_and_rule_promql_do_not_use_forbidden_identifier_labels() -> None:
    offenders: list[str] = []
    for source, title, expr in [*_iter_dashboard_promql(), *_iter_rule_promql()]:
        forbidden_labels = _forbidden_selector_labels(expr)
        if forbidden_labels:
            offenders.append(f"{source}::{title}: {sorted(forbidden_labels)}")
        for token in FORBIDDEN_PROM_LABELS:
            if re.search(rf"\b{re.escape(token)}\b", expr):
                offenders.append(f"{source}::{title}: token={token}")

    assert not offenders, "\n".join(offenders[:40])


def test_ci_contains_dashboard_rule_and_contract_drift_gates() -> None:
    workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
    closeout = _load_json(CLOSEOUT)

    assert "Prometheus rules syntax + promtool test vectors" in workflow
    assert "check-prometheus-rules --runner docker" in workflow
    assert "Dashboard navigation contract sync gate" in workflow
    assert closeout["outcomes"]["5725"]["ci_contract_drift_validation"] is True
