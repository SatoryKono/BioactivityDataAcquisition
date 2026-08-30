"""Детерминированная нормализация Trivy evidence и контроль исправимых уязвимостей."""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.engineering.common.repo_paths import resolve_output_path

TRIVY_BASELINE_COLUMNS = (
    "alert_number",
    "CVE",
    "package",
    "installed",
    "fixed",
    "layer",
    "status",
)
BLOCKING_SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM")
FIXABILITY_AUDIT_SCHEMA_VERSION = "trivy-fixability-audit-v1"


def _text(value: object) -> str:
    """Нормализовать произвольное скалярное значение для audit-отчёта."""
    return str(value or "").strip()


def _github_trivy_alert_index(payload: object) -> dict[tuple[str, str, str], str]:
    """Index GitHub Trivy alerts by the fields also present in Trivy JSON."""
    pages = payload if isinstance(payload, list) else []
    alerts = [
        alert
        for page in pages
        for alert in (page if isinstance(page, list) else [page])
        if isinstance(alert, Mapping)
    ]
    index: dict[tuple[str, str, str], str] = {}
    for alert in alerts:
        rule = alert.get("rule")
        instance = alert.get("most_recent_instance")
        message = instance.get("message") if isinstance(instance, Mapping) else None
        text = message.get("text") if isinstance(message, Mapping) else None
        if not isinstance(rule, Mapping) or not isinstance(text, str):
            continue
        fields = {
            key.strip(): value.strip()
            for line in text.splitlines()
            if ":" in line
            for key, value in [line.split(":", 1)]
        }
        vulnerability = str(rule.get("id") or fields.get("Vulnerability", ""))
        package = fields.get("Package", "")
        installed = fields.get("Installed Version", "")
        number = alert.get("number")
        if vulnerability and package and installed and isinstance(number, int):
            index.setdefault((vulnerability, package, installed), str(number))
    return index


def _iter_trivy_vulnerabilities(
    payload: Mapping[str, Any],
) -> Iterable[tuple[str, Mapping[str, Any]]]:
    """Итерировать валидные vulnerability rows полного Trivy JSON evidence."""
    results = payload.get("Results", [])
    if not isinstance(results, list):
        raise ValueError("Trivy JSON Results must be a list")

    for result in results:
        if not isinstance(result, Mapping):
            continue
        target = _text(result.get("Target"))
        vulnerabilities = result.get("Vulnerabilities") or []
        if not isinstance(vulnerabilities, list):
            raise ValueError("Trivy JSON Vulnerabilities must be a list")
        for vulnerability in vulnerabilities:
            if isinstance(vulnerability, Mapping):
                yield target, vulnerability


def _trivy_baseline_row(
    *,
    target: str,
    vulnerability: Mapping[str, Any],
    alert_index: Mapping[tuple[str, str, str], str],
) -> dict[str, str]:
    """Нормализовать одно finding в детерминированную строку baseline CSV."""
    cve = _text(vulnerability.get("VulnerabilityID"))
    package = _text(vulnerability.get("PkgName"))
    installed = _text(vulnerability.get("InstalledVersion"))
    if not cve or not package or not installed:
        raise ValueError("Trivy vulnerability is missing identity fields")
    layer = vulnerability.get("Layer")
    layer_id = _text(layer.get("DiffID")) if isinstance(layer, Mapping) else ""
    return {
        "alert_number": alert_index.get((cve, package, installed), ""),
        "CVE": cve,
        "package": package,
        "installed": installed,
        "fixed": _text(vulnerability.get("FixedVersion")),
        "layer": layer_id or target,
        "status": _text(vulnerability.get("Status")) or "affected",
    }


def trivy_baseline_rows(
    payload: Mapping[str, Any],
    *,
    github_alerts: object | None = None,
) -> list[dict[str, str]]:
    """Нормализовать Trivy image JSON в схему baseline CSV RF-001."""
    alert_index = _github_trivy_alert_index(github_alerts)
    rows = [
        _trivy_baseline_row(
            target=target,
            vulnerability=vulnerability,
            alert_index=alert_index,
        )
        for target, vulnerability in _iter_trivy_vulnerabilities(payload)
    ]
    return sorted(
        rows,
        key=lambda row: (
            row["CVE"],
            row["package"],
            row["installed"],
            row["layer"],
        ),
    )


def export_trivy_baseline_csv(
    *,
    trivy_json: Path,
    output: Path,
    github_alerts_json: Path | None = None,
) -> int:
    """Write deterministic RF-001 CSV evidence and return the row count."""
    safe_trivy = resolve_output_path(trivy_json)
    payload = json.loads(safe_trivy.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Trivy JSON root must be an object")
    github_alerts: object | None = None
    if github_alerts_json is not None:
        safe_alerts = resolve_output_path(github_alerts_json)
        if safe_alerts.is_file():
            github_alerts = json.loads(safe_alerts.read_text(encoding="utf-8"))
    rows = trivy_baseline_rows(payload, github_alerts=github_alerts)
    safe_output = resolve_output_path(output)
    safe_output.parent.mkdir(parents=True, exist_ok=True)
    with safe_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=TRIVY_BASELINE_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _vulnerability_rows(payload: Mapping[str, Any]) -> Iterable[dict[str, str]]:
    """Return normalized vulnerability rows from full Trivy JSON evidence."""
    for result in _mapping_list(payload.get("Results", []), label="Results"):

        target = _text(result.get("Target"))
        yield from _result_vulnerability_rows(result, target=target)


def _result_vulnerability_rows(
    result: Mapping[str, Any],
    *,
    target: str,
) -> Iterable[dict[str, str]]:
    """Return normalized vulnerability rows for one Trivy result."""
    vulnerabilities = result.get("Vulnerabilities", [])
    if vulnerabilities is None:
        return
    for vulnerability in _mapping_list(vulnerabilities, label="Vulnerabilities"):
        yield _fixability_row(vulnerability, target=target)


def _fixability_row(
    vulnerability: Mapping[str, Any],
    *,
    target: str,
) -> dict[str, str]:
    """Normalize one vulnerability into the fixability audit schema."""
    vulnerability_id = _text(vulnerability.get("VulnerabilityID"))
    package = _text(vulnerability.get("PkgName"))
    installed = _text(vulnerability.get("InstalledVersion"))
    if not vulnerability_id or not package or not installed:
        raise ValueError("Trivy vulnerability is missing identity fields")
    return {
        "vulnerability_id": vulnerability_id,
        "package": package,
        "installed_version": installed,
        "fixed_version": _text(vulnerability.get("FixedVersion")),
        "severity": _text(vulnerability.get("Severity")).upper() or "UNKNOWN",
        "status": _text(vulnerability.get("Status")).lower() or "affected",
        "target": target,
    }


def is_fixable_blocking_finding(row: Mapping[str, str]) -> bool:
    """Определить, должен ли finding блокировать merge без suppression уязвимости."""
    return (
        row["severity"] in BLOCKING_SEVERITIES
        and bool(row["fixed_version"])
        and row["status"] != "not_affected"
    )


def build_fixability_audit(payload: Mapping[str, Any]) -> dict[str, object]:
    """Собрать stable audit с полным перечнем findings и отдельным merge gate."""
    all_findings = sorted(
        _vulnerability_rows(payload),
        key=lambda row: (
            row["vulnerability_id"],
            row["package"],
            row["installed_version"],
            row["target"],
        ),
    )
    blocking = [row for row in all_findings if is_fixable_blocking_finding(row)]
    unfixed_or_deferred = [
        row
        for row in all_findings
        if row["severity"] in BLOCKING_SEVERITIES
        and not is_fixable_blocking_finding(row)
    ]
    severity_counts = {
        severity: sum(1 for row in all_findings if row["severity"] == severity)
        for severity in (*BLOCKING_SEVERITIES, "LOW", "UNKNOWN")
    }
    return {
        "schema_version": FIXABILITY_AUDIT_SCHEMA_VERSION,
        "policy": {
            "blocking_severities": list(BLOCKING_SEVERITIES),
            "block_only_when_fixed_version_available": True,
            "sarif_evidence_required": True,
            "recheck_trigger": "every_container_build",
        },
        "summary": {
            "all_findings": len(all_findings),
            "fixable_blocking_findings": len(blocking),
            "unfixed_or_deferred_blocking_severity_findings": len(unfixed_or_deferred),
            "severity_counts": severity_counts,
        },
        "fixable_blocking_findings": blocking,
        "unfixed_or_deferred_findings": unfixed_or_deferred,
        "all_findings": all_findings,
    }


def write_fixability_audit(*, trivy_json: Path, output: Path) -> dict[str, object]:
    """Записать audit-отчёт в repository-bounded путь и вернуть его payload."""
    safe_trivy = resolve_output_path(trivy_json)
    payload = json.loads(safe_trivy.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Trivy JSON root must be an object")
    audit = build_fixability_audit(payload)
    safe_output = resolve_output_path(output)
    safe_output.parent.mkdir(parents=True, exist_ok=True)
    safe_output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return audit


def parse_fixability_gate_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Разобрать аргументы CLI fixability-aware merge gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trivy-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--fail-on-fixable",
        action="store_true",
        help="Вернуть ненулевой exit code при исправимых Critical/High/Medium findings.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Сформировать audit и применить merge-gate policy без suppression SARIF."""
    args = parse_fixability_gate_args(argv)
    audit = write_fixability_audit(
        trivy_json=resolve_output_path(args.trivy_json),
        output=resolve_output_path(args.output),
    )
    summary = audit["summary"]
    assert isinstance(summary, Mapping)
    blocking = summary["fixable_blocking_findings"]
    assert isinstance(blocking, int)
    if args.fail_on_fixable and blocking:
        print(f"Fixable Critical/High/Medium Trivy findings: {blocking}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
