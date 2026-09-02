"""Internal helpers and constants for Processed Records dashboard payloads."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import ARTIFACT_PUBLISHED_EVENT
from bioetl.domain.types import RunID
from bioetl.interfaces.http import _processed_records_prometheus as _prom
from bioetl.interfaces.http._processed_records_prometheus import (
    _candidate_prometheus_base_urls,
    _query_prometheus_vector_with_fallbacks,
)
from bioetl.interfaces.http._processed_records_value_support import (
    _as_float,
    _count_text,
    _optional_int,
    _optional_text,
    _promql_string,
    _selector_regex,
    _selector_tokens,
    _sum_metric_values,
)
from bioetl.interfaces.http._processed_records_value_support import (
    is_deficit as is_deficit,
)

# Re-export canonical Prometheus constants (deduplicated from _processed_records_prometheus).
DEFAULT_PROMETHEUS_BASE_URL = _prom.DEFAULT_PROMETHEUS_BASE_URL
DEFAULT_PROMETHEUS_BASE_URL_FALLBACKS = _prom.DEFAULT_PROMETHEUS_BASE_URL_FALLBACKS
PROMETHEUS_QUERY_TIMEOUT_SECONDS = _prom.PROMETHEUS_QUERY_TIMEOUT_SECONDS

PROCESSED_RECORDS_TABLE_CONTRACT = "processed_records_table_v1"

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
_UNKNOWN_SCOPE = "unknown"


def fetch_processed_record_values(
    *,
    prometheus_base_url: str,
    pipeline: str,
    run_type: str | None,
) -> dict[str, float | None]:
    """Fetch all visible Processed Records values in one Prometheus request.

    Parameters
    ----------
    prometheus_base_url : str
        Base URL of the Prometheus server.
    pipeline : str
        Pipeline name to filter metrics.
    run_type : str | None
        Run type to filter metrics, or None for all run types.

    Returns
    -------
    dict[str, float | None]
        Dictionary mapping metric names to their values, or None if unavailable.
    """
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
    """Return an exact RunID selector, treating dashboard placeholder tokens as empty.

    Parameters
    ----------
    raw : str | None
        Raw string value from query parameter.

    Returns
    -------
    RunID | None
        Parsed RunID if valid UUID string, None for placeholder tokens or invalid input.
    """
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
    """Extract the most recent metrics snapshot from ledger entries.

    Parameters
    ----------
    ledger_entries : tuple[RunLedgerEntry, ...]
        Run ledger entries to search, in chronological order.

    Returns
    -------
    dict[str, int] | None
        Most recent metrics snapshot dictionary, or None if no snapshot found.
    """
    for entry in reversed(ledger_entries):
        if entry.metrics_snapshot:
            return dict(entry.metrics_snapshot)
    return None


def published_layer_artifact_counts(
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, int]:
    """Extract record counts for published artifacts from ledger entries.

    Parameters
    ----------
    ledger_entries : tuple[RunLedgerEntry, ...]
        Run ledger entries containing artifact publication events.

    Returns
    -------
    dict[str, int]
        Mapping of layer names (bronze, silver, gold) to their record counts.
    """
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
    """Build a PromQL query to fetch a single processed record metric value.

    Parameters
    ----------
    metric : str
        Metric name to query.
    pipeline : str
        Pipeline name selector.
    run_type : str | None
        Run type selector, or None for all run types.

    Returns
    -------
    str
        PromQL query string with rounded sum aggregation.
    """
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
    """Build one vector query while retaining metric names as row keys.

    Parameters
    ----------
    pipeline : str
        Pipeline name selector.
    run_type : str | None
        Run type selector, or None for all run types.

    Returns
    -------
    str
        PromQL query string that aggregates all processed record metrics.
    """
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
    """Parse a raw selector string into individual tokens.

    Parameters
    ----------
    raw : str | None
        Raw selector string to parse.

    Returns
    -------
    tuple[str, ...]
        Tuple of individual selector tokens.
    """
    return _selector_tokens(raw)


def is_unknown_scope(raw: str | None) -> bool:
    """Check if a raw selector represents an unknown scope.

    Parameters
    ----------
    raw : str | None
        Raw selector string to check.

    Returns
    -------
    bool
        True if the selector represents unknown scope, False otherwise.
    """
    return _selector_tokens(raw) == (_UNKNOWN_SCOPE,)


def as_float(value: float | int | None) -> float | None:
    """Convert a numeric value to float.

    Parameters
    ----------
    value : float | int | None
        Numeric value to convert.

    Returns
    -------
    float | None
        Float representation of the value, or None if input is None.
    """
    return _as_float(value)


def sum_metric_values(
    metric_values: dict[str, float | int | None],
    metrics: tuple[str, ...],
) -> float | None:
    """Sum values for multiple metrics from a metric values dictionary.

    Parameters
    ----------
    metric_values : dict[str, float | int | None]
        Dictionary mapping metric names to their values.
    metrics : tuple[str, ...]
        Tuple of metric names to sum.

    Returns
    -------
    float | None
        Sum of the metric values, or None if all values are None.
    """
    return _sum_metric_values(metric_values, metrics)


def count_text(value: float | None) -> str:
    """Convert a numeric count to its string representation.

    Parameters
    ----------
    value : float | None
        Numeric count value.

    Returns
    -------
    str
        String representation of the count, or "UNKNOWN" if value is None.
    """
    return _count_text(value)


def padded_count_text(value: float | None, width: int) -> str:
    """Convert a numeric count to right-justified string representation.

    Parameters
    ----------
    value : float | None
        Numeric count value.
    width : int
        Minimum field width for right justification.

    Returns
    -------
    str
        Right-justified string representation, or "UNKNOWN" if value is None.
    """
    count_text = _count_text(value)
    if value is None:
        return count_text
    return count_text.rjust(width)


def display_token(parameter: str, display_text: str) -> str:
    """Return the operator-facing cell text for Processed Records.

    Historically this returned ``f"{parameter}|{display_text}"`` for a single
    concatenated column. Grafana now renders separate ``parameter`` / ``value`` /
    ``percentage`` columns, so the parameter prefix is redundant and looks like a
    fill bug in the UI. ``parameter`` is kept for call-site compatibility.
    """
    _ = parameter
    return display_text


def row_status(
    *,
    parameter: str,
    silver_deficit: bool,
    gold_deficit: bool,
) -> str:
    """Determine the status indicator for a processed records table row.

    Parameters
    ----------
    parameter : str
        Row parameter identifier.
    silver_deficit : bool
        Whether a silver layer deficit exists.
    gold_deficit : bool
        Whether a gold layer deficit exists.

    Returns
    -------
    str
        Status string ("silver_deficit", "gold_deficit", or empty string).
    """
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
    """Format a processed record value as a percentage string.

    Parameters
    ----------
    value : float | None
        Numerator value.
    bronze_value : float | None
        Denominator value (bronze record count).
    denominator : _Denominator
        Denominator type ("constant_100" or "bronze").
    percent_format : _PercentFormat
        Format style ("constant_100", "fixed_1", or "trimmed_3").

    Returns
    -------
    str
        Formatted percentage string, or "UNKNOWN" if values unavailable.
    """
    if denominator == "constant_100":
        return "100%" if value is not None else "UNKNOWN"
    if value is None or bronze_value is None or bronze_value == 0:
        return "UNKNOWN"

    percentage = value / bronze_value * 100
    if percent_format == "fixed_1":
        return f"{percentage:.1f}%"
    if percent_format == "trimmed_3":
        return f"{percentage:.3f}".rstrip("0").rstrip(".") + "%"
    return "100%"
