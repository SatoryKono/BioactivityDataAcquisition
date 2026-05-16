"""Processed Records table payload helpers for dashboard HTTP surfaces."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

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
_ALL_SCOPE_TOKENS = {"All", "$__all", "*"}


def build_processed_records_table_payload(
    *,
    metric_values: dict[str, float | int | None],
    pipeline: str,
    run_type: str | None,
) -> dict[str, object]:
    """Build the Grafana table payload from current accounting metric values."""
    rows: list[dict[str, object]] = []
    bronze_value = _as_float(metric_values.get(_BRONZE_METRIC))
    silver_valid_value = _as_float(metric_values.get(_SILVER_VALID_METRIC))
    silver_sum = _sum_metric_values(metric_values, _SILVER_METRICS)
    gold_sum = _sum_metric_values(metric_values, _GOLD_METRICS)
    silver_deficit = _is_deficit(total=silver_sum, minimum=bronze_value)
    gold_deficit = _is_deficit(total=gold_sum, minimum=silver_valid_value)
    value_width = len(_count_text(bronze_value)) if bronze_value is not None else 0

    for spec in PROCESSED_RECORDS_ROW_SPECS:
        raw_value = _as_float(metric_values.get(spec.metric))

        value_text = _padded_count_text(raw_value, value_width)
        percentage_text = _format_percentage(
            value=raw_value,
            bronze_value=bronze_value,
            denominator=spec.denominator,
            percent_format=spec.percent_format,
        )
        rows.append(
            {
                "parameter": spec.parameter,
                "value": _display_token(spec.parameter, value_text),
                "percintage": _display_token(spec.parameter, percentage_text),
                "row_status": _row_status(
                    parameter=spec.parameter,
                    silver_deficit=silver_deficit,
                    gold_deficit=gold_deficit,
                ),
            }
        )

    return {
        "contract": PROCESSED_RECORDS_TABLE_CONTRACT,
        "pipeline": pipeline,
        "run_type": list(_selector_tokens(run_type)),
        "rows": rows,
    }


def fetch_processed_record_values(
    *,
    prometheus_base_url: str,
    pipeline: str,
    run_type: str | None,
) -> dict[str, float | None]:
    """Fetch one instant value per visible Processed Records row from Prometheus."""
    metric_values: dict[str, float | None] = {}
    prometheus_base_urls = _candidate_prometheus_base_urls(prometheus_base_url)
    for spec in PROCESSED_RECORDS_ROW_SPECS:
        metric_values[spec.metric] = _query_prometheus_scalar_with_fallbacks(
            prometheus_base_urls=prometheus_base_urls,
            query=_processed_record_value_query(
                metric=spec.metric,
                pipeline=pipeline,
                run_type=run_type,
            ),
        )
    return metric_values


def build_processed_records_table_payload_from_prometheus(
    *,
    prometheus_base_url: str,
    pipeline: str,
    run_type: str | None,
) -> dict[str, object]:
    """Fetch current accounting metrics and return the dashboard table payload."""
    metric_values = fetch_processed_record_values(
        prometheus_base_url=prometheus_base_url,
        pipeline=pipeline,
        run_type=run_type,
    )
    return build_processed_records_table_payload(
        metric_values=metric_values,
        pipeline=pipeline,
        run_type=run_type,
    )


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


def _query_prometheus_scalar(*, prometheus_base_url: str, query: str) -> float | None:
    url = (
        prometheus_base_url.rstrip("/") + "/api/v1/query?" + urlencode({"query": query})
    )
    try:
        with urlopen(url, timeout=PROMETHEUS_QUERY_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Prometheus query failed: {exc}") from exc

    if payload.get("status") != "success":
        error_message = payload.get("error") or payload.get("errorType") or "unknown"
        raise RuntimeError(f"Prometheus query failed: {error_message}")

    result = payload.get("data", {}).get("result", [])
    if not result:
        return None

    value = result[0].get("value")
    if not isinstance(value, list) or len(value) < 2:
        return None

    try:
        parsed = float(value[1])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


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


def _candidate_prometheus_base_urls(prometheus_base_url: str) -> tuple[str, ...]:
    primary = prometheus_base_url.rstrip("/")
    candidates = [primary]
    if primary == DEFAULT_PROMETHEUS_BASE_URL:
        candidates.extend(DEFAULT_PROMETHEUS_BASE_URL_FALLBACKS)
    return tuple(dict.fromkeys(candidate.rstrip("/") for candidate in candidates))


def _selector_regex(raw: str | None) -> str:
    tokens = _selector_tokens(raw)
    if not tokens:
        return ".*"
    if len(tokens) == 1:
        return re.escape(tokens[0])
    return "(?:" + "|".join(re.escape(token) for token in tokens) + ")"


def _selector_tokens(raw: str | None) -> tuple[str, ...]:
    if raw is None:
        return ()
    normalized = raw.strip()
    if not normalized or normalized in _ALL_SCOPE_TOKENS:
        return ()
    if normalized.startswith("{") and normalized.endswith("}"):
        normalized = normalized[1:-1]

    tokens: list[str] = []
    for part in normalized.split(","):
        token = part.strip()
        if not token or token in _ALL_SCOPE_TOKENS:
            return ()
        if token not in tokens:
            tokens.append(token)
    return tuple(tokens)


def _promql_string(raw: str) -> str:
    return raw.replace("\\", "\\\\").replace('"', '\\"')


def _as_float(value: float | int | None) -> float | None:
    if value is None:
        return None
    parsed = float(value)
    if not math.isfinite(parsed):
        return None
    return parsed


def _sum_metric_values(
    metric_values: dict[str, float | int | None],
    metrics: tuple[str, ...],
) -> float | None:
    values = tuple(_as_float(metric_values.get(metric)) for metric in metrics)
    if any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def _is_deficit(*, total: float | None, minimum: float | None) -> bool:
    return total is not None and minimum is not None and total < minimum


def _count_text(value: float | None) -> str:
    if value is None:
        return "No data"
    rounded = round(value)
    if math.isclose(value, rounded, abs_tol=1e-9):
        return f"{int(rounded):,}".replace(",", " ")
    return str(value)


def _padded_count_text(value: float | None, width: int) -> str:
    count_text = _count_text(value)
    if value is None:
        return count_text
    return count_text.rjust(width)


def _display_token(parameter: str, display_text: str) -> str:
    return f"{parameter}|{display_text}"


def _row_status(
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


def _format_percentage(
    *,
    value: float | None,
    bronze_value: float | None,
    denominator: _Denominator,
    percent_format: _PercentFormat,
) -> str:
    if denominator == "constant_100":
        return "100%" if value is not None else "No data"
    if value is None:
        return "No data"

    if bronze_value is None or bronze_value == 0:
        return "No data"

    percentage = value / bronze_value * 100
    if percent_format == "fixed_1":
        return f"{percentage:.1f}%"
    if percent_format == "trimmed_3":
        return f"{percentage:.3f}".rstrip("0").rstrip(".") + "%"
    return "100%"


__all__ = [
    "DEFAULT_PROMETHEUS_BASE_URL",
    "PROCESSED_RECORDS_ROW_SPECS",
    "PROCESSED_RECORDS_TABLE_CONTRACT",
    "build_processed_records_table_payload",
    "build_processed_records_table_payload_from_prometheus",
    "fetch_processed_record_values",
]
