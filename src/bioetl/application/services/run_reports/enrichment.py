"""Build optional pipeline run-report enrichment blocks from RunResult/options."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_models import (
        RunOptions,
        RunResult,
    )


def build_artifacts_from_result(
    result: RunResult,
) -> tuple[dict[str, Any], ...]:  # Any: artifact payload
    """Collect known artifact refs available at report finalize time."""
    items: list[dict[str, Any]] = []  # Any: artifact payload
    if result.debug_export_uri:
        item: dict[str, Any] = {  # Any: artifact payload
            "kind": "debug_export",
            "ref": str(result.debug_export_uri),
        }
        if result.debug_export_hash:
            item["hash"] = str(result.debug_export_hash)
        items.append(item)
    return tuple(items)


def build_failure_block(result: RunResult) -> dict[str, Any] | None:  # Any: failure block
    """Surface failure details when the run did not complete cleanly."""
    status = result.status.value
    if status in {"success", "dry_run"} and not result.error_type and not result.error_message:
        return None
    if status in {"success", "dry_run"}:
        return None
    return {
        "error_type": result.error_type,
        "error_message": result.error_message,
        "failed_stage": None,
        "exit_hint": _exit_hint(status, result.error_type),
    }


def _exit_hint(status: str, error_type: str | None) -> str:
    if status == "shutdown":
        return "Run interrupted by shutdown signal; inspect checkpoint/resume options."
    if error_type:
        return f"Investigate {error_type}; check quarantine and gold contract exclusions."
    return "Inspect pipeline logs, quarantine artifacts, and stage funnel removals."


def build_io_block(
    result: RunResult,
    *,
    options: RunOptions | None,
) -> dict[str, Any] | None:  # Any: io block
    """Compact IO selector summary without unbounded ID dumps."""
    if options is None:
        return {
            "pipeline_name": result.pipeline_name,
            "run_type": result.run_type,
        }
    filter_ids = options.filter_ids or ()
    multi = options.multi_filter_ids or {}
    multi_counts = {key: len(values) for key, values in multi.items()}
    payload: dict[str, Any] = {  # Any: io block
        "pipeline_name": result.pipeline_name,
        "run_type": options.run_type or result.run_type,
        "limit": options.limit,
        "start_offset": options.start_offset,
        "input_csv": options.input_csv,
        "filter_column": options.filter_column or options.filter_field,
        "filter_id_count": len(filter_ids) if filter_ids else None,
        "filter_id_hash": _hash_ids(filter_ids) if filter_ids else None,
        "multi_filter_id_counts": multi_counts or None,
        "skip_gold": options.skip_gold,
        "dry_run": options.dry_run,
        "use_cached_bronze": options.use_cached_bronze,
        "cached_bronze_path": options.cached_bronze_path,
    }
    return {key: value for key, value in payload.items() if value is not None}


def build_quarantine_block(
    result: RunResult,
    *,
    reasons_top_n: Sequence[Mapping[str, Any]],  # Any: reasons
) -> dict[str, Any] | None:  # Any: quarantine block
    """Aggregate quarantine-oriented reason counts when present."""
    quarantined = int(result.records_quarantined or 0)
    quarantine_reasons = [
        {
            "reason_code": item.get("reason_code"),
            "outcome": item.get("outcome"),
            "count": item.get("count"),
        }
        for item in reasons_top_n
        if item.get("outcome") == "quarantined"
    ]
    if quarantined <= 0 and not quarantine_reasons:
        return None
    return {
        "records_quarantined": quarantined,
        "top_reasons": quarantine_reasons,
    }


def build_dq_summary(
    result: RunResult,
    *,
    reasons_top_n: Sequence[Mapping[str, Any]],  # Any: reasons
) -> dict[str, Any] | None:  # Any: dq summary
    """Coarse DQ rollup from known quarantine/filter outcomes."""
    dq_reasons = [
        dict(item)
        for item in reasons_top_n
        if item.get("reason_family") == "dq"
        or str(item.get("reason_code", "")).upper().startswith("DQ_")
        or item.get("reason_code") == "SCHEMA_VALIDATION_FAILURE"
    ]
    filtered = int(result.records_filtered_out or 0)
    quarantined = int(result.records_quarantined or 0)
    if not dq_reasons and filtered <= 0 and quarantined <= 0:
        return None
    return {
        "records_filtered_out": filtered,
        "records_quarantined": quarantined,
        "reasons": dq_reasons,
    }


def build_schema_versions(
    *,
    reason_catalog_version: str,
    package_version: str | None = None,
    config_digest: str | None = None,
    execution_fingerprint: str | None = None,
    entity_contract_id: str | None = None,
) -> dict[str, Any]:  # Any: schema versions
    """Fingerprints available without inventing hashes."""
    payload: dict[str, Any] = {  # Any: schema versions
        "reason_catalog_version": reason_catalog_version,
    }
    if package_version:
        payload["bioetl_version"] = package_version
    if config_digest:
        payload["config_digest"] = config_digest
    if execution_fingerprint:
        payload["execution_fingerprint"] = execution_fingerprint
    if entity_contract_id:
        payload["entity_contract_id"] = entity_contract_id
    return payload


def build_stage_timings(
    timings: Mapping[str, float | int | None] | None,
) -> dict[str, Any] | None:  # Any: timings
    """Pass through stage durations only when at least one value is known."""
    if not timings:
        return None
    cleaned: dict[str, Any] = {}  # Any: timings
    for key, value in timings.items():
        if value is None:
            continue
        try:
            cleaned[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return cleaned or None


def build_http_summary(
    summary: Mapping[str, Any] | None,  # Any: http summary
) -> dict[str, Any] | None:  # Any: http summary
    """Pass through HTTP aggregates when instrumented."""
    if not summary:
        return None
    allowed = (
        "request_count",
        "retry_count",
        "status_4xx",
        "status_5xx",
        "rate_limit_hits",
        "bytes_in",
        "bytes_out",
    )
    cleaned = {
        key: summary[key]
        for key in allowed
        if key in summary and summary[key] is not None
    }
    return cleaned or None


def _hash_ids(values: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for value in sorted(str(item) for item in values):
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:16]
