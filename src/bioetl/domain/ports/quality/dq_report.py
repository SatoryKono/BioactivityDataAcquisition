"""DQ Report port interfaces (Protocols).

Defines interfaces for DQ report generation and writing following
the Ports & Adapters architecture (RULES.md §1.1).

These protocols enable decoupling between:
- Domain: DQ report value objects and analysis logic
- Infrastructure: Report serialization and storage
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime
    from pathlib import Path

    from bioetl.domain.ports.quality.dq_config import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        SilverDQConfigPort,
    )
    from bioetl.domain.value_objects.dq_report import (
        BronzeDQReport,
        DQReportFormat,
        GoldDQReport,
        SilverDQReport,
    )
from bioetl.domain.types import GoldBusinessRuleSpec, JsonDict, ScdConfig

DataContainer = (
    Any  # Any: polars.DataFrame | pyarrow.Table (avoids infra import in domain)
)
"""Type alias for data containers (polars.DataFrame or pyarrow.Table).

Uses Any to avoid infrastructure imports in domain layer per Ports & Adapters.
"""

DataContainerDict = dict[
    str, Any  # Any: port contract allows heterogeneous values
]  # Any: polars.DataFrame | pyarrow.Table (avoids infra import)
"""Type alias for dictionary of named data containers.

Maps table names to polars.DataFrame or pyarrow.Table instances.
Uses Any to avoid infrastructure imports in domain layer.
"""


@dataclass(frozen=True, slots=True)
class SilverDQAnalyzeRequest:
    """Canonical Silver DQ analysis request shared across report seams."""

    data: DataContainer
    run_id: str
    pipeline: str
    target_table: str
    source_batch_ids: list[str]
    config: SilverDQConfigPort
    timestamp: datetime
    primary_keys: list[str]
    soft_fail_threshold: float = 0.05
    hard_fail_threshold: float = 0.20
    input_record_count: int | None = None
    quarantined_count: int = 0
    previous_schema: dict[str, str] | None = None
    key_nullability_rules: list[JsonDict] | None = None


_SILVER_DQ_ANALYZE_POSITIONAL_FIELDS = (
    "data",
    "run_id",
    "pipeline",
    "target_table",
    "source_batch_ids",
    "config",
    "timestamp",
    "primary_keys",
    "soft_fail_threshold",
    "hard_fail_threshold",
    "input_record_count",
    "quarantined_count",
    "previous_schema",
    "key_nullability_rules",
)
_SILVER_DQ_ANALYZE_REQUIRED_FIELDS = (
    "data",
    "run_id",
    "pipeline",
    "target_table",
    "source_batch_ids",
    "config",
    "timestamp",
    "primary_keys",
)
_SILVER_DQ_ANALYZE_DEFAULTS: dict[str, object] = {
    "soft_fail_threshold": 0.05,
    "hard_fail_threshold": 0.20,
    "input_record_count": None,
    "quarantined_count": 0,
    "previous_schema": None,
    "key_nullability_rules": None,
}
_SILVER_DQ_ANALYZE_ALLOWED_FIELDS = frozenset(
    {*_SILVER_DQ_ANALYZE_POSITIONAL_FIELDS, *tuple(_SILVER_DQ_ANALYZE_DEFAULTS)}
)


def coerce_silver_dq_analyze_request(
    request: SilverDQAnalyzeRequest | DataContainer | None = None,
    *,
    args: tuple[object, ...] = (),
    kwargs: Mapping[str, object] | None = None,
) -> SilverDQAnalyzeRequest:
    """Normalize legacy or request-style Silver DQ analysis arguments."""
    if isinstance(request, SilverDQAnalyzeRequest):
        if args or kwargs:
            raise TypeError(
                "SilverDQAnalyzeRequest cannot be combined with legacy args/kwargs"
            )
        return request
    resolved_kwargs = _resolve_silver_dq_analyze_kwargs(
        request=request,
        args=args,
        kwargs=kwargs,
    )
    return SilverDQAnalyzeRequest(
        data=resolved_kwargs["data"],  # type: ignore[arg-type]
        run_id=resolved_kwargs["run_id"],  # type: ignore[arg-type]
        pipeline=resolved_kwargs["pipeline"],  # type: ignore[arg-type]
        target_table=resolved_kwargs["target_table"],  # type: ignore[arg-type]
        source_batch_ids=resolved_kwargs["source_batch_ids"],  # type: ignore[arg-type]
        config=resolved_kwargs["config"],  # type: ignore[arg-type]
        timestamp=resolved_kwargs["timestamp"],  # type: ignore[arg-type]
        primary_keys=resolved_kwargs["primary_keys"],  # type: ignore[arg-type]
        soft_fail_threshold=resolved_kwargs["soft_fail_threshold"],  # type: ignore[arg-type]
        hard_fail_threshold=resolved_kwargs["hard_fail_threshold"],  # type: ignore[arg-type]
        input_record_count=resolved_kwargs["input_record_count"],  # type: ignore[arg-type]
        quarantined_count=resolved_kwargs["quarantined_count"],  # type: ignore[arg-type]
        previous_schema=resolved_kwargs["previous_schema"],  # type: ignore[arg-type]
        key_nullability_rules=resolved_kwargs["key_nullability_rules"],  # type: ignore[arg-type]
    )


def _resolve_silver_dq_analyze_kwargs(
    *,
    request: SilverDQAnalyzeRequest | DataContainer | None,
    args: tuple[object, ...],
    kwargs: Mapping[str, object] | None,
) -> dict[str, object]:
    resolved_kwargs = dict(kwargs or {})
    legacy_values = list(args) if request is None else [request, *args]
    _merge_silver_dq_analyze_legacy_values(resolved_kwargs, legacy_values)
    _raise_on_unexpected_silver_dq_fields(resolved_kwargs)
    _raise_on_missing_silver_dq_fields(resolved_kwargs)
    for field_name, default in _SILVER_DQ_ANALYZE_DEFAULTS.items():
        resolved_kwargs.setdefault(field_name, default)
    return resolved_kwargs


def _merge_silver_dq_analyze_legacy_values(
    resolved_kwargs: dict[str, object],
    legacy_values: list[object],
) -> None:
    if len(legacy_values) > len(_SILVER_DQ_ANALYZE_POSITIONAL_FIELDS):
        raise TypeError("analyze() received too many positional arguments")
    positional_fields = _SILVER_DQ_ANALYZE_POSITIONAL_FIELDS[: len(legacy_values)]
    for field_name, value in zip(positional_fields, legacy_values, strict=False):
        if field_name in resolved_kwargs:
            raise TypeError(
                f"analyze() got multiple values for argument '{field_name}'"
            )
        resolved_kwargs[field_name] = value


def _raise_on_unexpected_silver_dq_fields(resolved_kwargs: dict[str, object]) -> None:
    unexpected_fields = sorted(set(resolved_kwargs) - _SILVER_DQ_ANALYZE_ALLOWED_FIELDS)
    if unexpected_fields:
        unexpected = ", ".join(unexpected_fields)
        raise TypeError(f"analyze() got unexpected keyword arguments: {unexpected}")


def _raise_on_missing_silver_dq_fields(resolved_kwargs: dict[str, object]) -> None:
    missing_fields = [
        field_name
        for field_name in _SILVER_DQ_ANALYZE_REQUIRED_FIELDS
        if field_name not in resolved_kwargs
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise TypeError(f"analyze() missing required arguments: {missing}")


@runtime_checkable
class BronzeDQAnalyzerPort(Protocol):
    """Port for Bronze layer DQ analysis.

    Analyzes raw data for basic DQ checks: record count, file integrity,
    schema snapshot, field presence, and encoding validation.
    """

    def analyze(
        self,
        records: Iterator[bytes],
        *,
        run_id: str,
        pipeline: str,
        batch_id: str,
        source_file: str,
        config: BronzeDQConfigPort,
        timestamp: datetime,
    ) -> BronzeDQReport:
        """Analyze Bronze data and generate DQ report.

        Args:
            records: Iterator of raw JSON bytes records.
            run_id: Pipeline run identifier.
            pipeline: Pipeline name.
            batch_id: Batch identifier.
            source_file: Path to the Bronze file.
            config: DQ report configuration.
            timestamp: Report generation timestamp (UTC).

        Returns:
            BronzeDQReport: Complete DQ report for Bronze layer.
        """
        ...


@runtime_checkable
class SilverDQAnalyzerPort(Protocol):
    """Port for Silver layer DQ analysis.

    Analyzes normalized data for DQ checks: null rates, uniqueness,
    type conformance, schema drift, and deduplication stats.
    """

    def analyze(
        self,
        request: SilverDQAnalyzeRequest | DataContainer | None = None,
        *args: object,
        **kwargs: object,
    ) -> SilverDQReport:
        """Analyze Silver data and generate DQ report.

        Args:
            data: Polars DataFrame or PyArrow Table with Silver data.
            run_id: Pipeline run identifier.
            pipeline: Pipeline name.
            target_table: Silver table path.
            source_batch_ids: List of Bronze batch IDs processed.
            config: DQ report configuration.
            timestamp: Report generation timestamp (UTC).
            primary_keys: List of primary key columns.
            soft_fail_threshold: Warning threshold for error rate.
            hard_fail_threshold: Failure threshold for error rate.
            input_record_count: Original record count before transforms.
            quarantined_count: Number of quarantined records.
            previous_schema: Previous schema for drift detection.
            key_nullability_rules: Optional per-column nullability override rules
                used to adjust DQ checks for columns that permit null primary keys
                under specific conditions.

        Returns:
            SilverDQReport: Complete DQ report for Silver layer.
        """
        del request, args, kwargs
        ...


@runtime_checkable
class GoldDQAnalyzerPort(Protocol):
    """Port for Gold layer DQ analysis.

    Analyzes data marts for strict DQ validation: completeness,
    business rules, referential integrity, and anomaly detection.
    """

    def analyze(
        self,
        data: DataContainer,
        *,
        run_id: str,
        pipeline: str,
        target_table: str,
        config: GoldDQConfigPort,
        timestamp: datetime,
        required_fields: list[str] | None = None,
        completeness_threshold: float = 0.90,
        business_rules: list[GoldBusinessRuleSpec] | None = None,
        reference_tables: DataContainerDict | None = None,
        baseline_stats: (
            dict[str, Any] | None  # Any: baseline stat values are float|int|str|None
        ) = None,
        scd_config: ScdConfig | None = None,
    ) -> GoldDQReport:
        """Analyze Gold data and generate DQ report.

        Args:
            data: Polars DataFrame or PyArrow Table with Gold data.
            run_id: Pipeline run identifier.
            pipeline: Pipeline name.
            target_table: Gold table path.
            config: DQ report configuration.
            timestamp: Report generation timestamp (UTC).
            required_fields: List of required fields for completeness.
            completeness_threshold: Minimum completeness score threshold.
            business_rules: List of business rule definitions.
            reference_tables: Tables for referential integrity checks.
            baseline_stats: Historical baseline for anomaly detection.
            scd_config: SCD configuration if applicable.

        Returns:
            GoldDQReport: Complete DQ report for Gold layer.
        """
        ...


@runtime_checkable
class DQReportWriterPort(Protocol):
    """Port for writing DQ reports to storage.

    Handles serialization of DQ reports to various formats
    (JSON, YAML, HTML) and writing to file system.
    """

    async def write_bronze_report(
        self,
        report: BronzeDQReport,
        output_path: Path | None = None,
        report_format: DQReportFormat | None = None,
        *,
        provider: str | None = None,
        entity: str | None = None,
    ) -> Path:
        """Write Bronze DQ report to file.

        Args:
            report: Bronze DQ report to write.
            output_path: Output path (None = alongside data).
            report_format: Output format (None = JSON).
            provider: Provider name for filename generation.
            entity: Entity name for filename generation.

        Returns:
            Path to the written report file.
        """
        ...

    async def write_silver_report(
        self,
        report: SilverDQReport,
        output_path: Path | None = None,
        report_format: DQReportFormat | None = None,
        *,
        provider: str | None = None,
        entity: str | None = None,
    ) -> Path:
        """Write Silver DQ report to file.

        Args:
            report: Silver DQ report to write.
            output_path: Output path (None = alongside data).
            report_format: Output format (None = JSON).
            provider: Provider name for path generation.
            entity: Entity name for path generation.

        Returns:
            Path to the written report file.
        """
        ...

    async def write_gold_report(
        self,
        report: GoldDQReport,
        output_path: Path | None = None,
        report_format: DQReportFormat | None = None,
        *,
        provider: str | None = None,
        entity: str | None = None,
    ) -> Path:
        """Write Gold DQ report to file.

        Args:
            report: Gold DQ report to write.
            output_path: Output path (None = alongside data).
            report_format: Output format (None = JSON).
            provider: Provider name for path generation.
            entity: Entity name for path generation.

        Returns:
            Path to the written report file.
        """
        ...


__all__ = [
    "BronzeDQAnalyzerPort",
    "DQReportWriterPort",
    "GoldDQAnalyzerPort",
    "SilverDQAnalyzerPort",
]
