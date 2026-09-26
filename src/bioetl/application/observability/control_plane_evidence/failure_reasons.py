"""Bounded failure-reason classification for operator run-ledger evidence."""

from __future__ import annotations

from bioetl.application.observability.control_plane_evidence.checks import (
    EvidenceCheckResult,
)
from bioetl.application.observability.control_plane_evidence.models import (
    unresolved_scope_check,
)
from bioetl.application.observability.control_plane_evidence.service_support import (
    EvidenceScopeContext,
    ledger_entries,
    service_payload,
)
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.ports import RunLedgerPort

FAILURE_REASON_CATEGORIES: tuple[str, ...] = (
    "api",
    "dq",
    "schema",
    "storage",
    "network",
    "validation",
    "unknown",
)

_CATEGORY_TOKENS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("dq", ("dataquality", "data_quality", "dq", "quarantine", "qualitythreshold")),
    ("schema", ("schema", "pandera", "column", "datatype", "contractschema")),
    (
        "network",
        (
            "network",
            "timeout",
            "connection",
            "dns",
            "socket",
            "transport",
            "retryexhausted",
        ),
    ),
    (
        "api",
        ("api", "http", "auth", "ratelimit", "provider", "request", "response"),
    ),
    (
        "storage",
        ("storage", "file", "ioerror", "oserror", "parquet", "delta", "disk", "write"),
    ),
    (
        "validation",
        (
            "validation",
            "valueerror",
            "assertion",
            "checkpointconflict",
            "policyviolation",
            "incompatible",
        ),
    ),
)


def build_failure_reason_rows(
    entries: tuple[RunLedgerEntry, ...],
) -> tuple[list[dict[str, object]], int]:
    """Aggregate failed ledger events into a fixed seven-category vocabulary."""
    counts = dict.fromkeys(FAILURE_REASON_CATEGORIES, 0)
    total = 0
    for entry in entries:
        if not _is_failure(entry):
            continue
        category = _classify(entry)
        counts[category] += 1
        total += 1
    return (
        [
            {
                "category": category,
                "count": counts[category],
                "status": "OK",
                "reason": "failure_reasons_bounded",
            }
            for category in FAILURE_REASON_CATEGORIES
        ],
        total,
    )


def build_unknown_failure_reason_rows(reason: str) -> list[dict[str, object]]:
    """Return visible UNKNOWN rows while preserving the fixed categories."""
    return [
        {
            "category": category,
            "count": None,
            "status": "UNKNOWN",
            "reason": reason,
        }
        for category in FAILURE_REASON_CATEGORIES
    ]


def build_failure_reasons_payload(
    *,
    scope: EvidenceScopeContext,
    ledger_port: RunLedgerPort | None,
) -> dict[str, object]:
    """Return only fixed-category failure counts; omit raw errors/messages."""
    if scope.manifest is None:
        scope_check = unresolved_scope_check(scope.resolved_via)
        payload = service_payload(
            endpoint="failure-reasons",
            scope=scope,
            checks=(scope_check,),
            additional_data={
                "categories": list(FAILURE_REASON_CATEGORIES),
                "total_failure_count": None,
            },
        )
        payload["rows"] = build_unknown_failure_reason_rows(scope_check.reason)
        return payload
    if ledger_port is None:
        checks = (
            EvidenceCheckResult(
                "ledger",
                "UNKNOWN",
                "run_ledger_unavailable",
                "The run ledger is not configured for failure aggregation.",
            ),
        )
        rows = build_unknown_failure_reason_rows("run_ledger_unavailable")
        total = None
    else:
        rows, total = build_failure_reason_rows(
            ledger_entries(ledger_port, scope.manifest)
        )
        checks = (
            EvidenceCheckResult(
                "classification",
                "OK",
                "failure_reasons_bounded",
                "Failed ledger events were projected to the fixed category set.",
            ),
        )
    payload = service_payload(
        endpoint="failure-reasons",
        scope=scope,
        checks=checks,
        additional_data={
            "categories": list(FAILURE_REASON_CATEGORIES),
            "total_failure_count": total,
        },
        ledger_entries=ledger_entries(ledger_port, scope.manifest),
    )
    payload["rows"] = rows
    return payload


def _is_failure(entry: RunLedgerEntry) -> bool:
    status = str(entry.status or "").strip().lower()
    return entry.event_type == "run_failed" or status in {
        "failed",
        "failure",
        "error",
        "unhealthy",
    }


def _classify(entry: RunLedgerEntry) -> str:
    classifier_text = " ".join(
        (
            str(entry.error_type or ""),
            str(entry.event_type or ""),
            str(entry.event_family or ""),
            str(entry.stage or ""),
        )
    ).lower()
    for category, tokens in _CATEGORY_TOKENS:
        if any(token in classifier_text for token in tokens):
            return category
    return "unknown"


__all__ = [
    "FAILURE_REASON_CATEGORIES",
    "build_failure_reason_rows",
    "build_failure_reasons_payload",
    "build_unknown_failure_reason_rows",
]
