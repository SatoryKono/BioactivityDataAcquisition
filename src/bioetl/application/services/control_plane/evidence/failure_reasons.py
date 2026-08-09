"""Bounded failure-reason classification for run-ledger evidence."""

from __future__ import annotations

from bioetl.domain.control_plane import RunLedgerEntry

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
            {"category": category, "count": counts[category]}
            for category in FAILURE_REASON_CATEGORIES
        ],
        total,
    )


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


__all__ = ["FAILURE_REASON_CATEGORIES", "build_failure_reason_rows"]
