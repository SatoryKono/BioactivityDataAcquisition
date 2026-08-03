"""Repo-local observability contract checks exposed through diagnostics CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_METRIC_ALLOWLIST = Path(
    "configs/quality/observability_metric_inventory_allowlist.yaml"
)
_SLO_ALERT_CONTRACT = Path("configs/quality/observability_slo_alert_contract.yaml")
_TRACING_COVERAGE_CONTRACT = Path("configs/quality/mandatory_tracing_coverage.yaml")
_PROMETHEUS_RULES = Path("grafana/prometheus-rules/bioetl_observability.yml")


@dataclass(frozen=True, slots=True)
class ContractCheck:
    """One observability contract check result."""

    name: str
    passed: bool
    details: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation."""
        return {
            "name": self.name,
            "passed": self.passed,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class ObservabilityContractCheckReport:
    """Aggregate observability contract check result."""

    passed: bool
    checks: tuple[ContractCheck, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation."""
        return {
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
        }


def run_observability_contract_checks(
    repo_root: Path | None = None,
) -> ObservabilityContractCheckReport:
    """Run the public diagnostics contract check set."""
    root = repo_root or Path.cwd()
    checks = (
        _check_metric_inventory(root),
        _check_slo_alert_contract(root),
        _check_tracing_coverage_contract(root),
    )
    return ObservabilityContractCheckReport(
        passed=all(check.passed for check in checks),
        checks=checks,
    )


def render_contract_check_report(report: ObservabilityContractCheckReport) -> str:
    """Render contract checks for operator-friendly CLI text output."""
    lines = [
        "BioETL Observability Contract Checks",
        f"  passed: {str(report.passed).lower()}",
    ]
    for check in report.checks:
        lines.append(f"  - {check.name}: {'pass' if check.passed else 'fail'}")
        violations = check.details.get("violations")
        if isinstance(violations, dict) and violations:
            for key, values in violations.items():
                lines.append(f"      {key}: {values}")
        missing = check.details.get("missing")
        if isinstance(missing, list) and missing:
            lines.append(f"      missing: {missing}")
        mismatches = check.details.get("mismatches")
        if isinstance(mismatches, list) and mismatches:
            lines.append(f"      mismatches: {mismatches}")
    return "\n".join(lines)


def _check_metric_inventory(repo_root: Path) -> ContractCheck:
    from scripts.engineering.qa import report_observability_metric_inventory

    report = report_observability_metric_inventory.collect_metric_inventory(repo_root)
    allowlist_path = repo_root / _METRIC_ALLOWLIST
    violations = report_observability_metric_inventory.validate_metric_inventory(
        report,
        allowlist=_load_metric_allowlist(allowlist_path),
    )
    return ContractCheck(
        name="metric_inventory_drift",
        passed=not violations,
        details={
            "violations": violations,
            "registered_without_runtime": report["registered_without_runtime"],
            "runtime_without_registry": report["runtime_without_registry"],
        },
    )


def _check_slo_alert_contract(repo_root: Path) -> ContractCheck:
    rules = _load_yaml(repo_root / _PROMETHEUS_RULES)
    contract = _load_yaml(repo_root / _SLO_ALERT_CONTRACT)
    rule_map = _build_alert_rule_map(rules)
    missing: list[str] = []
    mismatches: list[str] = []
    for slo_name, alert, source_metrics in _iter_slo_contract_alerts(contract):
        alert_name = str(alert["name"])
        rule = rule_map.get(alert_name)
        if rule is None:
            missing.append(alert_name)
            continue
        expr = str(rule.get("expr", ""))
        labels = rule.get("labels", {})
        annotations = rule.get("annotations", {})
        if not isinstance(labels, dict) or labels.get("severity") != alert.get(
            "severity"
        ):
            mismatches.append(f"{alert_name}:severity")
        if rule.get("for") != alert.get("for"):
            mismatches.append(f"{alert_name}:for")
        if not isinstance(annotations, dict) or annotations.get("runbook") != alert.get(
            "runbook"
        ):
            mismatches.append(f"{alert_name}:runbook")
        if not any(metric in expr for metric in source_metrics):
            mismatches.append(f"{alert_name}:{slo_name}:metric_reference")
    orphan_alerts = sorted(set(rule_map) - _contract_alert_names(contract))
    if orphan_alerts:
        mismatches.extend(f"{alert_name}:orphan" for alert_name in orphan_alerts)
    return ContractCheck(
        name="slo_alert_contract",
        passed=not missing and not mismatches,
        details={"missing": missing, "mismatches": mismatches},
    )


def _check_tracing_coverage_contract(repo_root: Path) -> ContractCheck:
    contract = _load_yaml(repo_root / _TRACING_COVERAGE_CONTRACT)
    surfaces = contract.get("surfaces")
    missing: list[str] = []
    mismatches: list[str] = []
    if not isinstance(surfaces, dict):
        return ContractCheck(
            name="mandatory_tracing_coverage",
            passed=False,
            details={"missing": ["surfaces"], "mismatches": []},
        )
    for surface_name, surface in surfaces.items():
        if not isinstance(surface, dict):
            mismatches.append(f"{surface_name}:invalid_surface")
            continue
        files = surface.get("files")
        if not isinstance(files, list):
            mismatches.append(f"{surface_name}:missing_files")
            continue
        for entry in files:
            _check_tracing_file_entry(
                repo_root=repo_root,
                surface_name=str(surface_name),
                entry=entry,
                missing=missing,
                mismatches=mismatches,
            )
    return ContractCheck(
        name="mandatory_tracing_coverage",
        passed=not missing and not mismatches,
        details={"missing": missing, "mismatches": mismatches},
    )


def _check_tracing_file_entry(
    *,
    repo_root: Path,
    surface_name: str,
    entry: object,
    missing: list[str],
    mismatches: list[str],
) -> None:
    if not isinstance(entry, dict):
        mismatches.append(f"{surface_name}:invalid_file_entry")
        return
    path_value = entry.get("path")
    if not isinstance(path_value, str):
        mismatches.append(f"{surface_name}:missing_path")
        return
    path = repo_root / path_value
    if not path.exists():
        missing.append(path_value)
        return
    source = path.read_text(encoding="utf-8")
    for term in _string_list(entry.get("required_terms")):
        if term not in source:
            mismatches.append(f"{path_value}:missing:{term}")
    for term in _string_list(entry.get("forbidden_terms")):
        if term in source:
            mismatches.append(f"{path_value}:forbidden:{term}")


def _load_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_metric_allowlist(path: Path) -> dict[str, set[str]]:
    payload = _load_yaml(path)
    raw_allowed = payload.get("allowed", payload)
    if not isinstance(raw_allowed, dict):
        return {}
    allowlist: dict[str, set[str]] = {}
    for key, values in raw_allowed.items():
        if isinstance(key, str) and isinstance(values, list):
            allowlist[key] = {str(value) for value in values}
    return allowlist


def _build_alert_rule_map(rules: dict[str, object]) -> dict[str, dict[str, object]]:
    rule_map: dict[str, dict[str, object]] = {}
    groups = rules.get("groups", [])
    if not isinstance(groups, list):
        return rule_map
    for group in groups:
        if not isinstance(group, dict):
            continue
        for rule in group.get("rules", []):
            if not isinstance(rule, dict):
                continue
            alert_name = rule.get("alert")
            if isinstance(alert_name, str):
                rule_map[alert_name] = rule
    return rule_map


def _iter_slo_contract_alerts(
    contract: dict[str, object],
) -> list[tuple[str, dict[str, object], set[str]]]:
    contracts = contract.get("slo_contracts")
    if not isinstance(contracts, dict):
        return []
    results: list[tuple[str, dict[str, object], set[str]]] = []
    for slo_name, slo in contracts.items():
        if not isinstance(slo, dict):
            continue
        metrics = set(_string_list(slo.get("metrics")))
        alerts = slo.get("alerts")
        if not isinstance(alerts, list):
            continue
        for alert in alerts:
            if isinstance(alert, dict) and isinstance(alert.get("name"), str):
                results.append((str(slo_name), alert, metrics))
    return results


def _contract_alert_names(contract: dict[str, object]) -> set[str]:
    return {str(alert["name"]) for _, alert, _ in _iter_slo_contract_alerts(contract)}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
