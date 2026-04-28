# ruff: noqa: UP049
"""Pure helpers for BatchExecutor DQ context construction."""

from __future__ import annotations

__all__ = [
    "build_dataframe_from_records",
    "build_dq_report_context",
    "dataframe_error_types",
    "extract_dq_entity",
    "get_dq_thresholds",
    "normalize_records_for_polars",
    "stringify_value",
]

import json
from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.domain.context import current_utc_time

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.services.dq_report_service import DQReportContext
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.domain.types import BronzeRecord, GoldRecord

_DQ_DATAFRAME_ERRORS: tuple[type[Exception], ...] = (
    ImportError,
    ModuleNotFoundError,
    ValueError,
    TypeError,
    RuntimeError,
)


def dataframe_error_types() -> tuple[type[Exception], ...]:
    """Resolve exception types raised while building Polars dataframes."""
    try:
        import polars as pl
    except (ImportError, ModuleNotFoundError, AttributeError):
        return _DQ_DATAFRAME_ERRORS
    return (*_DQ_DATAFRAME_ERRORS, pl.exceptions.PolarsError)


def stringify_value(value: object, keys_to_stringify: set[str], key: str) -> object:
    """Stringify a value if its key requires normalization."""
    if key not in keys_to_stringify or value is None:
        return value
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, default=str, sort_keys=True)
    return str(value)


def normalize_records_for_polars[_RecordT: dict[str, object]](
    records: list[_RecordT],
) -> list[dict[str, object]] | None:
    """Normalize mixed nested/string columns to stable string representation."""
    nested_keys: set[str] = set()
    non_nested_keys: set[str] = set()

    for record in records:
        for key, value in record.items():
            if value is None:
                continue
            if isinstance(value, (dict, list, tuple)):
                nested_keys.add(key)
            else:
                non_nested_keys.add(key)

    keys_to_stringify = nested_keys & non_nested_keys
    if not keys_to_stringify:
        return None

    return [
        {
            key: stringify_value(value, keys_to_stringify, key)
            for key, value in record.items()
        }
        for record in records
    ]


def build_dataframe_from_records(
    *,
    records: list[dict[str, object]],
    logger: LoggerPort,
    metrics: MetricsPort | None = None,
    pipeline: str | None = None,
    stage: str = "other",
) -> object | None:
    """Build Polars dataframe from records, returning None on failure."""
    if not records:
        return None
    try:
        import polars as pl

        dataframe: object = pl.DataFrame(records, infer_schema_length=None)
        return dataframe
    except dataframe_error_types() as dataframe_error:
        normalized_records = normalize_records_for_polars(records)
        if normalized_records is not None:
            try:
                import polars as pl

                normalized_dataframe: object = pl.DataFrame(
                    normalized_records,
                    infer_schema_length=None,
                )
                return normalized_dataframe
            except dataframe_error_types():
                pass
        logger.warning(
            "Failed to build dataframe for DQ context",
            records_count=len(records),
            error_type=type(dataframe_error).__name__,
            reason="dq_dataframe_build_failed",
            stage=stage,
        )
        if metrics is not None and pipeline is not None:
            metrics.increment_counter(
                "bioetl_dq_context_build_failures_total",
                1,
                {
                    "pipeline": pipeline,
                    "stage": stage,
                    "reason": "dq_dataframe_build_failed",
                },
            )
        return None


def get_dq_thresholds(config: RecordProcessorConfig) -> tuple[float, float]:
    """Resolve DQ thresholds from config, falling back to defaults."""
    dq_config = getattr(config, "dq_config", None)
    if dq_config:
        return (
            dq_config.soft_fail_threshold,
            dq_config.hard_fail_threshold,
        )
    return (0.05, 0.20)


def extract_dq_entity(config: RecordProcessorConfig) -> str:
    """Derive entity name for report naming from silver table naming."""
    table_config = config.table_config
    silver_table = table_config.silver_table
    entity_type = config.entity_type
    if silver_table and "_" in silver_table:
        underscore_entity: str = silver_table.split("_", 1)[1]
        return underscore_entity
    if silver_table and "." in silver_table:
        dotted_entity: str = silver_table.split(".")[-1]
        return dotted_entity
    resolved_entity: str = silver_table or entity_type
    return resolved_entity


def build_dq_report_context(
    *,
    context: PipelineContext,
    config: RecordProcessorConfig,
    bronze_records: list[bytes],
    silver_records: list[dict[str, object]],
    gold_records: list[dict[str, object]],
    source_batch_ids: list[str],
    last_bronze_path: str | None,
    records_fetched: int,
    records_quarantined: int,
    build_dataframe: Callable[
        [list[BronzeRecord] | list[GoldRecord], str],
        object | None,
    ],
) -> DQReportContext:
    """Build DQ report context from accumulated execution samples."""
    from bioetl.application.services.dq_report_service import DQReportContext

    silver_data = build_dataframe(silver_records, "silver")
    gold_data = build_dataframe(gold_records, "gold")
    primary_keys = list(config.table_config.primary_keys)
    soft_threshold, hard_threshold = get_dq_thresholds(config)

    key_nullability_rules = None
    dq_config = config.dq_config
    if dq_config is not None:
        key_nullability_rules = [
            {
                "field": rule.field,
                "key_type": rule.key_type,
                "nullable": rule.nullable,
            }
            for rule in dq_config.key_nullability_rules
        ]

    replay_timestamp_anchor = getattr(context, "replay_timestamp_anchor", None)
    started_at = getattr(context, "started_at", current_utc_time())
    dq_timestamp = replay_timestamp_anchor or started_at
    current_date_str = dq_timestamp.strftime("%Y-%m-%d")
    dq_entity = extract_dq_entity(config)

    return DQReportContext(
        run_id=str(context.run_id),
        pipeline_name=config.pipeline_name,
        timestamp=dq_timestamp,
        provider=config.provider,
        entity=dq_entity,
        bronze_records=bronze_records or None,
        bronze_batch_id=source_batch_ids[-1] if source_batch_ids else None,
        bronze_source_file=last_bronze_path,
        bronze_output_path=config.bronze_output_path,
        bronze_date_str=current_date_str,
        silver_data=silver_data,
        silver_target_table=config.table_config.silver_table,
        silver_source_batch_ids=source_batch_ids or None,
        silver_primary_keys=primary_keys or None,
        silver_input_count=records_fetched,
        silver_quarantined_count=records_quarantined,
        silver_output_path=config.silver_output_path,
        silver_key_nullability_rules=key_nullability_rules,
        gold_data=gold_data,
        gold_target_table=config.table_config.gold_table,
        gold_scd_config=config.scd_config,
        gold_output_path=config.gold_output_path,
        dq_soft_threshold=soft_threshold,
        dq_hard_threshold=hard_threshold,
        flat_structure=config.flat_structure,
    )
