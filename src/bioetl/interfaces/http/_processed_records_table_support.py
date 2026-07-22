"""Internal helpers and constants for Processed Records dashboard payloads."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from uuid import UUID

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import ARTIFACT_PUBLISHED_EVENT
from bioetl.domain.types import RunID
from bioetl.interfaces.http._processed_records_http import open_url as _open_url
from bioetl.interfaces.http._processed_records_value_support import (
    _as_float,
    _count_text,
    _optional_int,
    _optional_text,
    _promql_string,
    _selector_regex,
    _selector_tokens,
    _sum_metric_values,
    is_deficit,  # noqa: F401 - re-exported for the table facade
)

PROCESSED_RECORDS_TABLE_CONTRACT = "processed_records_table_v1"
DEFAULT_PROMETHEUS_BASE_URL = "http://localhost:9090"
DEFAULT_PROMETHEUS_BASE_URL_FALLBACKS = (
    "http://prometheus:9090",
    "http://host.docker.internal:9090",
)
PROMETHEUS_QUERY_TIMEOUT_SECONDS = 3.0

_Denominator = Literal["constant_100", "bronze"]
_PercentFormat = Literal["constant_100", "fixed_1", "trimmed_3"]


@dataclass(frozen=True)
class ProcessedRecordRowSpec:
    """One visible Processed Records table row."""

    parameter: str
    metric: str
    denominator: _Denominator
    percent_format: _PercentFormat


PROCESSED_RECORDS_ROW_SPECS: tuple[ProcessedRecordRowSpec, ...] = (
    ProcessedRecordRowSpec(
        parameter="01 bronze_records",
        metric="bioetl_processed_records_bronze_current",
        denominator="constant_100",
        percent_format="constant_100",
    ),
    ProcessedRecordRowSpec(
        parameter="02 silver_valid_records",
        metric="bioetl_processed_records_silver_valid_current",
        denominator="bronze",
        percent_format="fixed_1",
    ),
    ProcessedRecordRowSpec(
        parameter="03 silver_filtered_out_records",
        metric="bioetl_processed_records_silver_filtered_out_current",
        denominator="bronze",
        percent_format="trimmed_3",
    ),
    ProcessedRecordRowSpec(
        parameter="04 silver_quarantined_records",
        metric="bioetl_processed_records_silver_quarantined_current",
        denominator="bronze",
        percent_format="trimmed_3",
    ),
    ProcessedRecordRowSpec(
        parameter="05 silver_skipped_records",
        metric="bioetl_processed_records_silver_skipped_current",
        denominator="bronze",
        percent_format="trimmed_3",
    ),
    ProcessedRecordRowSpec(
        parameter="06 silver_deduplicated_records",
        metric="bioetl_processed_records_silver_deduplicated_current",
        denominator="bronze",
        percent_format="trimmed_3",
    ),
    ProcessedRecordRowSpec(
        parameter="07 gold_written_records",
        metric="bioetl_processed_records_gold_written_current",
        denominator="bronze",
        percent_format="fixed_1",
    ),
    ProcessedRecordRowSpec(
        parameter="08 gold_excluded_by_contract_records",
        metric="bioetl_processed_records_gold_excluded_by_contract_current",
        denominator="bronze",
        percent_format="trimmed_3",
    ),
    ProcessedRecordRowSpec(
        parameter="09 gold_quarantined_records",
        metric="bioetl_processed_records_gold_quarantined_current",
        denominator="bronze",
        percent_format="trimmed_3",
    ),
    ProcessedRecordRowSpec(
        parameter="10 gold_skipped_records",
        metric="bioetl_processed_records_gold_skipped_current",
        denominator="bronze",
        percent_format="trimmed_3",
    ),
    ProcessedRecordRowSpec(
        parameter="11 gold_deduplicated_records",
        metric="bioetl_processed_records_gold_deduplicated_current",
        denominator="bronze",
        percent_format="trimmed_3",
    ),
)

_BRONZE_METRIC = "bioetl_processed_records_bronze_current"
_SILVER_VALID_METRIC = "bioetl_processed_records_silver_valid_current"
_SILVER_METRICS = (
    "bioetl_processed_records_silver_valid_current",
    "bioetl_processed_records_silver_filtered_out_current",
    "bioetl_processed_records_silver_quarantined_current",
    "bioetl_processed_records_silver_skipped_current",
    "bioetl_processed_records_silver_deduplicated_current",
)
_GOLD_METRICS = (
    "bioetl_processed_records_gold_written_current",
    "bioetl_processed_records_gold_excluded_by_contract_current",
    "bioetl_processed_records_gold_quarantined_current",
    "bioetl_processed_records_gold_skipped_current",
    "bioetl_processed_records_gold_deduplicated_current",
)
_SILVER_PARAMETERS = frozenset(
    spec.parameter
    for spec in PROCESSED_RECORDS_ROW_SPECS
    if spec.parameter[3:9] == "silver"
)
_GOLD_PARAMETERS = frozenset(
    spec.parameter
    for spec in PROCESSED_RECORDS_ROW_SPECS
    if spec.parameter[3:7] == "gold"
)
_ALL_SCOPE_TOKENS = {"All", "$__all", "__all", "*"}
_UNKNOWN_SCOPE = "unknown"


def fetch_processed_record_values(
    *,
    prometheus_base_url: str,
    pipeline: str,
    run_type: str | None,
) -> dict[str, float | None]:
    """Fetch all visible Processed Records values in one Prometheus request."""
    metric_values: dict[str, float | None] = {
        spec.metric: None for spec in PROCESSED_RECORDS_ROW_SPECS
    }
    prometheus_base_urls = _candidate_prometheus_base_urls(prometheus_base_url)
    metric_values.update(
        _query_prometheus_vector_with_fallbacks(
            prometheus_base_urls=prometheus_base_urls,
            query=_processed_record_values_query(
                pipeline=pipeline,
                run_type=run_type,
            ),
        )
    )
    return metric_values


def read_processed_records_run_id(raw: str | None) -> RunID | None:
    """Return an exact RunID selector, treating dashboard placeholder tokens as empty."""
    tokens = _selector_tokens(raw)
    if len(tokens) != 1:
        return None
    token = tokens[0]
    if token in {"-", "unknown"}:
        return None
    try:
        return RunID(UUID(token))
    except ValueError:
        return None


def latest_metrics_snapshot(
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, int] | None:
    for entry in reversed(ledger_entries):
        if entry.metrics_snapshot:
            return dict(entry.metrics_snapshot)
    return None


def published_layer_artifact_counts(
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in ledger_entries:
        if entry.event_type != ARTIFACT_PUBLISHED_EVENT:
            continue
        details = entry.details if isinstance(entry.details, dict) else {}
        stage = _optional_text(details.get("stage") or entry.stage)
        record_count = _optional_int(details.get("record_count"))
        if stage in {"bronze", "silver", "gold"} and record_count is not None:
            counts[stage] = record_count
    return counts


def _processed_record_value_query(
    *,
    metric: str,
    pipeline: str,
    run_type: str | None,
) -> str:
    pipeline_regex = _promql_string(_selector_regex(pipeline))
    run_type_regex = _promql_string(_selector_regex(run_type))
    return (
        f'round(sum({metric}{{pipeline=~"{pipeline_regex}",'
        f'run_type=~"{run_type_regex}"}}))'
    )


def _processed_record_values_query(
    *,
    pipeline: str,
    run_type: str | None,
) -> str:
    """Build one vector query while retaining metric names as row keys."""
    pipeline_regex = _promql_string(_selector_regex(pipeline))
    run_type_regex = _promql_string(_selector_regex(run_type))
    metric_regex = (
        "(?:"
        + "|".join(re.escape(spec.metric) for spec in PROCESSED_RECORDS_ROW_SPECS)
        + ")"
    )
    return (
        'sum by (__name__) ({__name__=~"'
        f'{metric_regex}",pipeline=~"{pipeline_regex}",'
        f'run_type=~"{run_type_regex}"}})'
    )


def selector_tokens(raw: str | None) -> tuple[str, ...]:
    return _selector_tokens(raw)


def is_unknown_scope(raw: str | None) -> bool:
    return _selector_tokens(raw) == (_UNKNOWN_SCOPE,)


def as_float(value: float | int | None) -> float | None:
    return _as_float(value)


def sum_metric_values(
    metric_values: dict[str, float | int | None],
    metrics: tuple[str, ...],
) -> float | None:
    return _sum_metric_values(metric_values, metrics)


def count_text(value: float | None) -> str:
    return _count_text(value)


def padded_count_text(value: float | None, width: int) -> str:
    count_text = _count_text(value)
    if value is None:
        return count_text
    return count_text.rjust(width)


def display_token(parameter: str, display_text: str) -> str:
    return f"{parameter}|{display_text}"


def row_status(
    *,
    parameter: str,
    silver_deficit: bool,
    gold_deficit: bool,
) -> str:
    if silver_deficit and parameter in _SILVER_PARAMETERS:
        return "silver_deficit"
    if gold_deficit and parameter in _GOLD_PARAMETERS:
        return "gold_deficit"
    return ""


def format_percentage(
    *,
    value: float | None,
    bronze_value: float | None,
    denominator: _Denominator,
    percent_format: _PercentFormat,
) -> str:
    if denominator == "constant_100":
        return "100%" if value is not None else "No data"
    if value is None or bronze_value is None or bronze_value == 0:
        return "No data"

    percentage = value / bronze_value * 100
    if percent_format == "fixed_1":
        return f"{percentage:.1f}%"
    if percent_format == "trimmed_3":
        return f"{percentage:.3f}".rstrip("0").rstrip(".") + "%"
    return "100%"


def _fetch_prometheus_query_payload(
    *,
    prometheus_base_url: str,
    query: str,
) -> dict[str, object]:
    url = (
        prometheus_base_url.rstrip("/") + "/api/v1/query?" + urlencode({"query": query})
    )
    try:
        with _open_url(url, timeout=PROMETHEUS_QUERY_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Prometheus query failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Prometheus query failed: invalid payload")
    return payload


def _prometheus_error_message(payload: dict[str, object]) -> str:
    error = payload.get("error")
    if error:
        return str(error)
    error_type = payload.get("errorType")
    if error_type:
        return str(error_type)
    return "unknown"


def _require_prometheus_success(payload: dict[str, object]) -> None:
    if payload.get("status") == "success":
        return
    raise RuntimeError(f"Prometheus query failed: {_prometheus_error_message(payload)}")


def _prometheus_result_list(payload: dict[str, object]) -> list[object]:
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return []
    result = data.get("result", [])
    if not isinstance(result, list):
        return []
    return result


def _finite_float_from_value_pair(value: object) -> float | None:
    if not isinstance(value, list) or len(value) < 2:
        return None
    try:
        parsed = float(value[1])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _metric_name_from_sample(sample: dict[object, object]) -> str | None:
    metric = sample.get("metric")
    if not isinstance(metric, dict):
        return None
    name = metric.get("__name__")
    return name if isinstance(name, str) else None


def _parse_vector_sample(sample: object) -> tuple[str, float] | None:
    if not isinstance(sample, dict):
        return None
    metric = _metric_name_from_sample(sample)
    if metric is None:
        return None
    parsed = _finite_float_from_value_pair(sample.get("value"))
    if parsed is None:
        return None
    return metric, parsed


def _vector_samples_from_payload(payload: dict[str, object]) -> dict[str, float]:
    values: dict[str, float] = {}
    for sample in _prometheus_result_list(payload):
        parsed = _parse_vector_sample(sample)
        if parsed is not None:
            metric, number = parsed
            values[metric] = number
    return values


def _scalar_from_payload(payload: dict[str, object]) -> float | None:
    result = _prometheus_result_list(payload)
    if not result:
        return None
    first = result[0]
    if not isinstance(first, dict):
        return None
    return _finite_float_from_value_pair(first.get("value"))


def _query_prometheus_scalar(*, prometheus_base_url: str, query: str) -> float | None:
    payload = _fetch_prometheus_query_payload(
        prometheus_base_url=prometheus_base_url,
        query=query,
    )
    _require_prometheus_success(payload)
    return _scalar_from_payload(payload)


def _query_prometheus_vector(
    *,
    prometheus_base_url: str,
    query: str,
) -> dict[str, float]:
    """Return finite vector samples keyed by their retained metric name."""
    payload = _fetch_prometheus_query_payload(
        prometheus_base_url=prometheus_base_url,
        query=query,
    )
    _require_prometheus_success(payload)
    return _vector_samples_from_payload(payload)


def _query_prometheus_scalar_with_fallbacks(
    *,
    prometheus_base_urls: tuple[str, ...],
    query: str,
) -> float | None:
    errors: list[str] = []
    for prometheus_base_url in prometheus_base_urls:
        try:
            return _query_prometheus_scalar(
                prometheus_base_url=prometheus_base_url,
                query=query,
            )
        except RuntimeError as exc:
            errors.append(f"{prometheus_base_url}: {exc}")
    raise RuntimeError("; ".join(errors))


def _query_prometheus_vector_with_fallbacks(
    *,
    prometheus_base_urls: tuple[str, ...],
    query: str,
) -> dict[str, float]:
    """Try each configured Prometheus endpoint for one vector request."""
    errors: list[str] = []
    for prometheus_base_url in prometheus_base_urls:
        try:
            return _query_prometheus_vector(
                prometheus_base_url=prometheus_base_url,
                query=query,
            )
        except RuntimeError as exc:
            errors.append(f"{prometheus_base_url}: {exc}")
    raise RuntimeError("; ".join(errors))


def _candidate_prometheus_base_urls(prometheus_base_url: str) -> tuple[str, ...]:
    primary = prometheus_base_url.rstrip("/")
    candidates = [primary]
    if primary == DEFAULT_PROMETHEUS_BASE_URL:
        candidates.extend(DEFAULT_PROMETHEUS_BASE_URL_FALLBACKS)
    return tuple(dict.fromkeys(candidate.rstrip("/") for candidate in candidates))
