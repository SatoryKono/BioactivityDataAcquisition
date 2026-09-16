"""Deterministic selected-run assessment; wall clocks and chart ranges are not inputs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

RULES_VERSION = "selected-run-v1"
SNAPSHOT_SCHEMA = "selected_run_snapshot_v1"
DOMAINS = (
    "Runtime",
    "Control Plane",
    "Workflow",
    "Data Quality",
    "Provider",
    "Data Validation",
)
_PRIORITY = ("ERROR", "INCOMPLETE", "UNKNOWN", "WARN", "OK")


def evidence_digest(value: Mapping[str, object]) -> str:
    """Hash canonical evidence, rejecting non-JSON floating point sentinels."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _row(domain: str, verdict: str, reason: str, source: str) -> dict[str, object]:
    return {
        "domain": domain,
        "verdict": verdict,
        "reason": reason,
        "applicable": verdict != "N/A",
        "evidence_ref": source,
        "action": "Inspect saved evidence"
        if verdict in {"OK", "N/A"}
        else "Inspect reason and evidence",
    }


def _observed_row(domain: str, observations: Mapping[str, object]) -> dict[str, object]:
    observation = _mapping(observations.get(domain))
    verdict = str(observation.get("verdict", "INCOMPLETE"))
    if verdict not in {*_PRIORITY, "N/A"}:
        verdict = "UNKNOWN"
    return _row(
        domain,
        verdict,
        str(observation.get("reason", "run_observation_missing")),
        f"#/observations/{domain}",
    )


def _domain_rows(report: Mapping[str, object]) -> list[dict[str, object]]:
    """Project the six sources without aggregating their independent outcomes."""
    identity = _mapping(report.get("identity"))
    execution = str(identity.get("status", "unknown")).lower()
    observations = _mapping(report.get("observations"))
    runtime = {
        "success": "OK",
        "failed": "ERROR",
        "shutdown": "WARN",
        "cancelled": "WARN",
        "dry_run": "N/A",
    }.get(execution, "UNKNOWN")
    rows = [_row("Runtime", runtime, f"execution_{execution}", "#/identity")]
    rows.append(_observed_row("Control Plane", observations))
    rows.append(
        _observed_row("Workflow", observations)
        if identity.get("workflow_run_id")
        else _row(
            "Workflow", "N/A", "standalone_pipeline", "#/identity/workflow_run_id"
        )
    )
    rows.append(_observed_row("Data Quality", observations))
    io = _mapping(report.get("io"))
    rows.append(
        _row(
            "Provider", "N/A", "cached_bronze_no_remote_probe", "#/io/use_cached_bronze"
        )
        if io.get("use_cached_bronze") is True
        else _observed_row("Provider", observations)
    )
    rows.append(_observed_row("Data Validation", observations))
    return rows


def _assessment_rows(
    report: Mapping[str, object], execution: str
) -> list[dict[str, object]]:
    if execution == "dry_run":
        return [
            _row(name, "N/A", "dry_run_no_execution", "#/identity/status")
            for name in DOMAINS
        ]
    return _domain_rows(report)


def _aggregate(verdicts: set[str]) -> str:
    return next((status for status in _PRIORITY if status in verdicts), "N/A")


def assess_report(report: Mapping[str, object]) -> dict[str, object]:
    """Assess only facts recorded by this run; missing checks cannot imply success."""
    identity = _mapping(report.get("identity"))
    execution = str(identity.get("status", "unknown")).lower()
    rows = _assessment_rows(report, execution)
    verdicts = {str(row["verdict"]) for row in rows}
    checks = _aggregate(verdicts)
    return {
        "rules_version": RULES_VERSION,
        "execution_state": execution.upper(),
        "verdict": "RUNNING" if execution in {"running", "started"} else checks,
        "checks_verdict": checks,
        "evidence_completeness": "INCOMPLETE"
        if verdicts & {"UNKNOWN", "INCOMPLETE"}
        else "COMPLETE",
        "domains": rows,
    }


def build_snapshot(report: Mapping[str, object]) -> dict[str, object]:
    """Build a content-addressed revision with its own complete input evidence."""
    evidence = {
        key: value for key, value in report.items() if key != "selected_run_snapshot"
    }
    assessment = assess_report(evidence)
    body = {
        "schema_version": SNAPSHOT_SCHEMA,
        "evidence": evidence,
        "assessment": assessment,
    }
    return {**body, "revision": evidence_digest(body)}


def verify_snapshot(snapshot: Mapping[str, object]) -> bool:
    """Recheck bytes and evaluation on every read, never trust a cached OK."""
    if snapshot.get("schema_version") != SNAPSHOT_SCHEMA:
        return False
    body = {key: value for key, value in snapshot.items() if key != "revision"}
    evidence = _mapping(snapshot.get("evidence"))
    return snapshot.get("revision") == evidence_digest(body) and snapshot.get(
        "assessment"
    ) == assess_report(evidence)
