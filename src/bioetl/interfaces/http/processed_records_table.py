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
PROMETHEUS_QUERY_TIMEOUT_SECONDS = 3.0

_Denominator = Literal["constant_100", "bronze", "silver_valid"]
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
        denominator="silver_valid",
        percent_format="fixed_1",
    ),
    ProcessedRecordRowSpec(
        parameter="08 gold_excluded_by_contract_records",
        metric="bioetl_processed_records_gold_excluded_by_contract_current",
        denominator="silver_valid",
        percent_format="trimmed_3",
    ),
    ProcessedRecordRowSpec(
        parameter="09 gold_quarantined_records",
        metric="bioetl_processed_records_gold_quarantined_current",
        denominator="silver_valid",
        percent_format="trimmed_3",
    ),
    ProcessedRecordRowSpec(
        parameter="10 gold_skipped_records",
        metric="bioetl_processed_records_gold_skipped_current",
        denominator="silver_valid",
        percent_format="trimmed_3",
    ),
    ProcessedRecordRowSpec(
        parameter="11 gold_deduplicated_records",
        metric="bioetl_processed_records_gold_deduplicated_current",
        denominator="silver_valid",
        percent_format="trimmed_3",
    ),
)

_BRONZE_METRIC = "bioetl_processed_records_bronze_current"
_SILVER_VALID_METRIC = "bioetl_processed_records_silver_valid_current"
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

    for spec in PROCESSED_RECORDS_ROW_SPECS:
        raw_value = _as_float(metric_values.get(spec.metric))
        parameter = spec.parameter
        if raw_value == 0:
            parameter = f"{parameter}__zero"

        rows.append(
            {
                "parameter": parameter,
                "value": _count_value(raw_value),
                "percintage": _format_percentage(
                    value=raw_value,
                    bronze_value=bronze_value,
                    silver_valid_value=silver_valid_value,
                    denominator=spec.denominator,
                    percent_format=spec.percent_format,
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
    for spec in PROCESSED_RECORDS_ROW_SPECS:
        metric_values[spec.metric] = _query_prometheus_scalar(
            prometheus_base_url=prometheus_base_url,
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


def _count_value(value: float | None) -> int | float | None:
    if value is None:
        return None
    rounded = round(value)
    if math.isclose(value, rounded, abs_tol=1e-9):
        return int(rounded)
    return value


def _format_percentage(
    *,
    value: float | None,
    bronze_value: float | None,
    silver_valid_value: float | None,
    denominator: _Denominator,
    percent_format: _PercentFormat,
) -> str:
    if denominator == "constant_100":
        return "100%" if value is not None else "No data"
    if value is None:
        return "No data"

    denominator_value = bronze_value if denominator == "bronze" else silver_valid_value
    if denominator_value is None or denominator_value == 0:
        return "No data"

    percentage = value / denominator_value * 100
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
