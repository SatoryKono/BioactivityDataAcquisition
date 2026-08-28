"""Детерминированный контроль Trivy findings с учётом доступности upstream-исправления."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.engineering.common.repo_paths import resolve_output_path

BLOCKING_SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM")
SCHEMA_VERSION = "trivy-fixability-audit-v1"


def _text(value: object) -> str:
    """Нормализовать произвольное скалярное значение для audit-отчёта."""
    return str(value or "").strip()


def _vulnerability_rows(payload: Mapping[str, Any]) -> Iterable[dict[str, str]]:
    """Вернуть нормализованные строки уязвимостей из Trivy JSON evidence."""
    results = payload.get("Results", [])
    if not isinstance(results, list):
        raise ValueError("Trivy JSON Results must be a list")

    for result in results:
        if not isinstance(result, Mapping):
            continue
        target = _text(result.get("Target"))
        vulnerabilities = result.get("Vulnerabilities", [])
        if vulnerabilities is None:
            continue
        if not isinstance(vulnerabilities, list):
            raise ValueError("Trivy JSON Vulnerabilities must be a list")
        for vulnerability in vulnerabilities:
            if not isinstance(vulnerability, Mapping):
                continue
            vulnerability_id = _text(vulnerability.get("VulnerabilityID"))
            package = _text(vulnerability.get("PkgName"))
            installed = _text(vulnerability.get("InstalledVersion"))
            if not vulnerability_id or not package or not installed:
                raise ValueError("Trivy vulnerability is missing identity fields")
            severity = _text(vulnerability.get("Severity")).upper() or "UNKNOWN"
            status = _text(vulnerability.get("Status")).lower() or "affected"
            fixed = _text(vulnerability.get("FixedVersion"))
            yield {
                "vulnerability_id": vulnerability_id,
                "package": package,
                "installed_version": installed,
                "fixed_version": fixed,
                "severity": severity,
                "status": status,
                "target": target,
            }


def is_fixable_blocking_finding(row: Mapping[str, str]) -> bool:
    """Определить, должен ли finding блокировать merge без suppression уязвимости."""
    return (
        row["severity"] in BLOCKING_SEVERITIES
        and bool(row["fixed_version"])
        and row["status"] != "not_affected"
    )


def build_audit(payload: Mapping[str, Any]) -> dict[str, object]:
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
        if row["severity"] in BLOCKING_SEVERITIES and not is_fixable_blocking_finding(row)
    ]
    severity_counts = {
        severity: sum(1 for row in all_findings if row["severity"] == severity)
        for severity in (*BLOCKING_SEVERITIES, "LOW", "UNKNOWN")
    }
    return {
        "schema_version": SCHEMA_VERSION,
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


def write_audit(*, trivy_json: Path, output: Path) -> dict[str, object]:
    """Записать audit-отчёт в repository-bounded путь и вернуть его payload."""
    payload = json.loads(trivy_json.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Trivy JSON root must be an object")
    audit = build_audit(payload)
    safe_output = resolve_output_path(output)
    safe_output.parent.mkdir(parents=True, exist_ok=True)
    safe_output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return audit


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Разобрать аргументы CLI policy gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trivy-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--fail-on-fixable",
        action="store_true",
        help="Вернуть ненулевой exit code при наличии исправимых Critical/High/Medium findings.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Сформировать audit и применить merge-gate policy без suppression SARIF."""
    args = parse_args(argv)
    audit = write_audit(trivy_json=args.trivy_json, output=args.output)
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
