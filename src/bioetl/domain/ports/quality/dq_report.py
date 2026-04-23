"""DQ Report port interfaces (Protocols).

Defines interfaces for DQ report generation and writing following
the Ports & Adapters architecture (RULES.md §1.1).

These protocols enable decoupling between:
- Domain: DQ report value objects and analysis logic
- Infrastructure: Report serialization and storage
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime
    from pathlib import Path

    from bioetl.domain.ports.quality.dq_config import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
    )
    from bioetl.domain.value_objects.dq_report import (
        BronzeDQReport,
        DQReportFormat,
        GoldDQReport,
        SilverDQReport,
    )
from bioetl.domain.ports.quality.silver_dq_request import (
    SilverDQAnalyzeRequest,
    coerce_silver_dq_analyze_request,
)
from bioetl.domain.types import GoldBusinessRuleSpec, ScdConfig

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
    "SilverDQAnalyzeRequest",
    "SilverDQAnalyzerPort",
    "coerce_silver_dq_analyze_request",
]
