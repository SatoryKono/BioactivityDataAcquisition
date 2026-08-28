"""Deterministic Trivy JSON to RF-001 baseline CSV normalization."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

TRIVY_BASELINE_COLUMNS = (
    "alert_number",
    "CVE",
    "package",
    "installed",
    "fixed",
    "layer",
    "status",
)


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


def trivy_baseline_rows(
    payload: Mapping[str, Any],
    *,
    github_alerts: object | None = None,
) -> list[dict[str, str]]:
    """Normalize Trivy image JSON into the RF-001 baseline CSV schema."""
    alert_index = _github_trivy_alert_index(github_alerts)
    rows: list[dict[str, str]] = []
    results = payload.get("Results", [])
    if not isinstance(results, list):
        raise ValueError("Trivy JSON Results must be a list")
    for result in results:
        if not isinstance(result, Mapping):
            continue
        target = str(result.get("Target") or "")
        vulnerabilities = result.get("Vulnerabilities") or []
        if not isinstance(vulnerabilities, list):
            raise ValueError("Trivy JSON Vulnerabilities must be a list")
        for vulnerability in vulnerabilities:
            if not isinstance(vulnerability, Mapping):
                continue
            cve = str(vulnerability.get("VulnerabilityID") or "")
            package = str(vulnerability.get("PkgName") or "")
            installed = str(vulnerability.get("InstalledVersion") or "")
            if not cve or not package or not installed:
                raise ValueError("Trivy vulnerability is missing identity fields")
            layer = vulnerability.get("Layer")
            layer_id = (
                str(layer.get("DiffID") or "") if isinstance(layer, Mapping) else ""
            )
            rows.append(
                {
                    "alert_number": alert_index.get((cve, package, installed), ""),
                    "CVE": cve,
                    "package": package,
                    "installed": installed,
                    "fixed": str(vulnerability.get("FixedVersion") or ""),
                    "layer": layer_id or target,
                    "status": str(vulnerability.get("Status") or "affected"),
                }
            )
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
    from scripts.engineering.common.repo_paths import resolve_output_path

    payload = json.loads(trivy_json.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Trivy JSON root must be an object")
    github_alerts: object | None = None
    if github_alerts_json is not None and github_alerts_json.is_file():
        github_alerts = json.loads(github_alerts_json.read_text(encoding="utf-8"))
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
