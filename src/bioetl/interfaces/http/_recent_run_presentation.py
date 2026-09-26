"""Bounded, exact-run presentation for the Run Explorer table."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from bioetl.interfaces.http.selected_run_status import load_selected_run_status

_PASSPORT_ROOT = (
    "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/"
    "docs/04-reference/passports"
)
_VALUES = {"OK", "WARN", "ERROR", "INCOMPLETE", "N/A", "QUERY ERROR"}


def _status(value: object) -> str:
    """Missing assessment evidence is incomplete, never inferred progress or OK."""
    token = str(value)
    return token if token in _VALUES else "INCOMPLETE"


def _passport(kind: str, name: object) -> str:
    token = str(name or "").strip()
    if token in {"", "—", "N/A", "-"}:
        return ""
    return f"{_PASSPORT_ROOT}/{kind}/{quote(token.replace('_', '-'), safe='')}.md"


def _evidence_status(assessment: dict[str, object]) -> str:
    availability = assessment.get("evidence_availability")
    if availability == "legacy_no_snapshot":
        return "N/A"
    if (
        assessment.get("verdict") in {"ERROR", "QUERY ERROR"}
        and availability != "AVAILABLE"
    ):
        return str(assessment["verdict"])
    checks = assessment.get("replay_checks")
    artifacts = (
        [
            item
            for item in checks
            if isinstance(item, dict)
            and str(item.get("evidence_ref", "")).startswith("#/artifacts/")
        ]
        if isinstance(checks, list)
        else []
    )
    if any(
        item.get("reason")
        in {"digest_mismatch", "artifact_path_escape", "artifact_record_invalid"}
        for item in artifacts
    ):
        return "ERROR"
    if not artifacts or any(item.get("result") != "pass" for item in artifacts):
        return "INCOMPLETE"
    return (
        "OK" if assessment.get("evidence_completeness") == "COMPLETE" else "INCOMPLETE"
    )


def recent_run_presentation(
    row: dict[str, object], *, root: Path | None, manifest_port: object | None
) -> dict[str, object]:
    """Reuse verified report/revision/artifact checks only for the bounded page."""
    assessment = load_selected_run_status(
        pipeline=str(row["pipeline"]),
        run_id=str(row["run_id"]),
        root=root,
        manifest_port=manifest_port,
    )
    domains = assessment.get("domains")
    quality = (
        next(
            (
                item.get("verdict")
                for item in domains
                if isinstance(item, dict) and item.get("domain") == "Data Quality"
            ),
            None,
        )
        if isinstance(domains, list)
        else None
    )
    provider = row.get("provider")
    checks = assessment.get("provider_checks")
    if isinstance(checks, list):
        provider = next(
            (
                item.get("provider")
                for item in checks
                if isinstance(item, dict)
                and item.get("provider") not in {None, "", "—"}
            ),
            provider,
        )
    legacy = assessment.get("evidence_availability") == "legacy_no_snapshot"
    replay = {
        "READY": "OK",
        "BLOCKED": "ERROR",
        "INSUFFICIENT": "INCOMPLETE",
        "UNSUPPORTED": "N/A",
        "QUERY ERROR": "QUERY ERROR",
    }.get(str(assessment.get("replay_readiness_now")), "INCOMPLETE")
    if (
        assessment.get("verdict") == "ERROR"
        and assessment.get("evidence_availability") != "AVAILABLE"
    ):
        replay = "ERROR"
    return {
        "provider": provider or "N/A",
        "workflow_passport_url": _passport("workflows", row.get("workflow_id")),
        "pipeline_passport_url": _passport("pipelines", row["pipeline"]),
        "saved_evidence_status": _evidence_status(assessment),
        "data_quality_status": "N/A"
        if legacy and quality in {None, "UNKNOWN", "INCOMPLETE"}
        else _status(quality),
        "replay_readiness_status": "N/A" if legacy else replay,
    }
