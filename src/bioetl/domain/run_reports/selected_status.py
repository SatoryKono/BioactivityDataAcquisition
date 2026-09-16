"""Deterministic selected-run assessment; wall clocks and chart ranges are not inputs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

RULES_VERSION = "selected-run-v2"
_SELECTED_RUN_V1 = "selected-run-v1"
SUPPORTED_RULES = {_SELECTED_RUN_V1, RULES_VERSION}
SNAPSHOT_SCHEMA = "selected_run_snapshot_v1"
_INCOMPLETE = "INCOMPLETE"
_UNKNOWN = "UNKNOWN"
_OK = "OK"
_NA = "N/A"
_PRIORITY = ("ERROR", _INCOMPLETE, _UNKNOWN, "WARN", _OK)
RUNTIME = "Runtime"
CONTROL_PLANE = "Control Plane"
WORKFLOW = "Workflow"
DATA_QUALITY = "Data Quality"
PROVIDER = "Provider"
DATA_VALIDATION = "Data Validation"
DOMAINS = (
    RUNTIME,
    CONTROL_PLANE,
    WORKFLOW,
    DATA_QUALITY,
    PROVIDER,
    DATA_VALIDATION,
)


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
        "applicable": verdict != _NA,
        "evidence_ref": source,
        "action": "Inspect saved evidence"
        if verdict in {_OK, _NA}
        else "Inspect reason and evidence",
    }


def _observed_row(domain: str, observations: Mapping[str, object]) -> dict[str, object]:
    observation = _mapping(observations.get(domain))
    verdict = str(observation.get("verdict", _INCOMPLETE))
    if verdict not in {*_PRIORITY, _NA}:
        verdict = _UNKNOWN
    return _row(
        domain,
        verdict,
        str(observation.get("reason", "run_observation_missing")),
        f"#/observations/{domain}",
    )


def _domain_rows(
    report: Mapping[str, object], rules_version: str
) -> list[dict[str, object]]:
    """Project the six sources without aggregating their independent outcomes."""
    identity = _mapping(report.get("identity"))
    execution = str(identity.get("status", "unknown")).lower()
    observations = _mapping(report.get("observations"))
    runtime = {
        "success": _OK,
        "failed": "ERROR",
        "shutdown": "WARN",
        "cancelled": "WARN",
        "dry_run": _NA,
    }.get(execution, _UNKNOWN)
    rows = [_row(RUNTIME, runtime, f"execution_{execution}", "#/identity")]
    rows.append(_observed_row(CONTROL_PLANE, observations))
    rows.append(
        _observed_row(WORKFLOW, observations)
        if identity.get("workflow_run_id")
        else _row(
            WORKFLOW, _NA, "standalone_pipeline", "#/identity/workflow_run_id"
        )
    )
    rows.append(_observed_row(DATA_QUALITY, observations))
    io = _mapping(report.get("io"))
    rows.append(
        _row(
            PROVIDER, _NA, "cached_bronze_no_remote_probe", "#/io/use_cached_bronze"
        )
        if io.get("use_cached_bronze") is True
        else _observed_row(PROVIDER, observations)
    )
    rows.append(
        _row(DATA_VALIDATION, _NA, "gold_explicitly_skipped", "#/io/skip_gold")
        if rules_version != _SELECTED_RUN_V1 and io.get("skip_gold") is True
        else _observed_row(DATA_VALIDATION, observations)
    )
    return rows


def _assessment_rows(
    report: Mapping[str, object], execution: str, rules_version: str
) -> list[dict[str, object]]:
    if execution == "dry_run":
        return [
            _row(name, _NA, "dry_run_no_execution", "#/identity/status")
            for name in DOMAINS
        ]
    return _domain_rows(report, rules_version)


def _aggregate(verdicts: set[str]) -> str:
    return next((status for status in _PRIORITY if status in verdicts), _NA)


def assess_report(
    report: Mapping[str, object], *, rules_version: str = RULES_VERSION
) -> dict[str, object]:
    """Assess only facts recorded by this run; missing checks cannot imply success."""
    identity = _mapping(report.get("identity"))
    execution = str(identity.get("status", "unknown")).lower()
    if rules_version not in SUPPORTED_RULES:
        raise ValueError("assessment_rules_unsupported")
    rows = _assessment_rows(report, execution, rules_version)
    verdicts = {str(row["verdict"]) for row in rows}
    checks = _aggregate(verdicts)
    return {
        "rules_version": rules_version,
        "execution_state": execution.upper(),
        "verdict": "RUNNING" if execution in {"running", "started"} else checks,
        "checks_verdict": checks,
        "evidence_completeness": _INCOMPLETE
        if verdicts & {_UNKNOWN, _INCOMPLETE}
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
    if not isinstance(snapshot.get("evidence"), dict) or not isinstance(
        snapshot.get("assessment"), dict
    ):
        return False
    try:
        return _snapshot_matches_evidence(snapshot)
    except (TypeError, ValueError):
        return False


def _snapshot_matches_evidence(snapshot: Mapping[str, object]) -> bool:
    """Compare a structurally valid envelope with its versioned recomputation."""
    body = {key: value for key, value in snapshot.items() if key != "revision"}
    evidence = _mapping(snapshot.get("evidence"))
    rules_version = str(_mapping(snapshot.get("assessment")).get("rules_version"))
    return snapshot.get("revision") == evidence_digest(body) and snapshot.get(
        "assessment"
    ) == assess_report(evidence, rules_version=rules_version)
