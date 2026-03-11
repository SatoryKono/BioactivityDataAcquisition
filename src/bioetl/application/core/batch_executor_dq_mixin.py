"""DQ context and accumulation helpers for BatchExecutor."""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime
from typing import TYPE_CHECKING, TypeVar

from bioetl.domain.types import BatchID, BronzeRecord, GoldRecord

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.services.dq_report_service import DQReportContext
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort

_DQ_DATAFRAME_ERRORS: tuple[type[Exception], ...] = (
    ImportError,
    ModuleNotFoundError,
    ValueError,
    TypeError,
    RuntimeError,
)

# Maximum DQ sample size to prevent OOM on large pipeline runs.
# Uses reservoir sampling to maintain a statistically representative subset.
_DQ_MAX_SAMPLE_SIZE = 50_000
_ReservoirT = TypeVar("_ReservoirT")


class _BatchExecutorDQMixin:
    """Provides DQ data collection and report context construction."""

    _services: PipelineService
    _context: PipelineContext
    _config: RecordProcessorConfig
    _logger: LoggerPort
    _bronze_records_for_dq: list[bytes]
    _silver_records_for_dq: list[BronzeRecord]
    _gold_records_for_dq: list[GoldRecord]
    _source_batch_ids: list[str]
    _last_bronze_path: str | None
    _dq_total_seen: int
    records_fetched: int
    records_quarantined: int

    def _should_collect_dq_data(self) -> bool:
        """Return True when DQ report service is configured."""
        return self._services.dq_report_service is not None

    def _collect_dq_data(
        self,
        records: list[BronzeRecord],
        batch_id: BatchID,
        bronze_result: object,
        silver_records: list[BronzeRecord],
        gold_records: list[GoldRecord],
    ) -> None:
        """Collect Bronze/Silver/Gold payloads used by post-run DQ reports.

        Uses reservoir sampling to bound memory: once the sample reaches
        ``_DQ_MAX_SAMPLE_SIZE``, new records randomly replace existing ones
        with decreasing probability, keeping the sample representative.
        """
        _ = batch_id

        for record in records:
            try:
                encoded = json.dumps(record, default=str).encode("utf-8")
            except (TypeError, ValueError):
                continue
            self._reservoir_add(self._bronze_records_for_dq, encoded)

        if bronze_result is not None and hasattr(bronze_result, "path"):
            self._last_bronze_path = str(bronze_result.path)

        for rec in silver_records:
            self._reservoir_add(self._silver_records_for_dq, rec)
        for rec in gold_records:
            self._reservoir_add(self._gold_records_for_dq, rec)

    def _reservoir_add(
        self,
        reservoir: list[_ReservoirT],
        item: _ReservoirT,
    ) -> None:
        """Add item to a bounded reservoir using Algorithm R."""
        if not hasattr(self, "_dq_total_seen"):
            self._dq_total_seen = 0
        self._dq_total_seen += 1

        if len(reservoir) < _DQ_MAX_SAMPLE_SIZE:
            reservoir.append(item)
        else:
            idx = random.randrange(self._dq_total_seen)
            if idx < _DQ_MAX_SAMPLE_SIZE:
                reservoir[idx] = item

    def _build_dataframe_from_records(
        self,
        records: list[BronzeRecord] | list[GoldRecord],
    ) -> object | None:
        """Build Polars dataframe from records, returning None on failure."""
        if not records:
            return None
        try:
            import polars as pl

            return pl.DataFrame(records)
        except self._dataframe_error_types() as dataframe_error:
            normalized_records = self._normalize_records_for_polars(records)
            if normalized_records is not None:
                try:
                    import polars as pl

                    return pl.DataFrame(normalized_records)
                except self._dataframe_error_types() as normalized_error:
                    _ = normalized_error
            self._logger.warning(
                "Failed to build dataframe for DQ context",
                records_count=len(records),
                error_type=type(dataframe_error).__name__,
                reason="dq_dataframe_build_failed",
            )
            return None

    @staticmethod
    def _dataframe_error_types() -> tuple[type[Exception], ...]:
        """Resolve exception types raised while building Polars dataframes."""
        try:
            import polars as pl
        except (ImportError, ModuleNotFoundError):
            return _DQ_DATAFRAME_ERRORS
        except AttributeError:
            return _DQ_DATAFRAME_ERRORS
        return (*_DQ_DATAFRAME_ERRORS, pl.exceptions.PolarsError)

    @staticmethod
    def _stringify_value(
        value: object, keys_to_stringify: set[str], key: str
    ) -> object:
        """Stringify a value if its key requires normalization."""
        if key not in keys_to_stringify or value is None:
            return value
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, default=str, sort_keys=True)
        return str(value)

    @staticmethod
    def _normalize_records_for_polars(
        records: list[BronzeRecord] | list[GoldRecord],
    ) -> list[dict[str, object]] | None:
        """Normalize mixed nested/string columns to stable string representation.

        Polars may fail when one column mixes nested values (dict/list/tuple) with
        plain scalars/strings across rows. For such columns we stringify values so
        the dataframe builder sees a single consistent type.
        """
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

        _sv = _BatchExecutorDQMixin._stringify_value
        return [
            {key: _sv(value, keys_to_stringify, key) for key, value in record.items()}
            for record in records
        ]

    def _get_dq_thresholds(self) -> tuple[float, float]:
        """Resolve DQ thresholds from config, falling back to defaults."""
        if self._config.dq_config:
            return (
                self._config.dq_config.soft_fail_threshold,
                self._config.dq_config.hard_fail_threshold,
            )
        return (0.05, 0.20)

    def _extract_dq_entity(self) -> str:
        """Derive entity name for report naming from silver table naming."""
        silver_table = self._config.table_config.silver_table
        entity_type = self._config.entity_type
        if silver_table and "_" in silver_table:
            return silver_table.split("_", 1)[1]
        if silver_table and "." in silver_table:
            return silver_table.split(".")[-1]
        return silver_table or entity_type

    def get_dq_context(self) -> DQReportContext | None:
        """Build report context from DQ data accumulated during execution.

        Returns:
            Populated DQReportContext for post-run DQ report generation, or None if
            no DQ report service is configured.
        """
        if not self._should_collect_dq_data():
            return None

        from bioetl.application.services.dq_report_service import DQReportContext

        silver_data = self._build_dataframe_from_records(self._silver_records_for_dq)
        gold_data = self._build_dataframe_from_records(self._gold_records_for_dq)
        primary_keys = list(self._config.table_config.primary_keys)
        soft_threshold, hard_threshold = self._get_dq_thresholds()

        key_nullability_rules = None
        if self._config.dq_config is not None:
            key_nullability_rules = [
                {
                    "field": rule.field,
                    "key_type": rule.key_type,
                    "nullable": rule.nullable,
                }
                for rule in self._config.dq_config.key_nullability_rules
            ]

        now_utc = datetime.now(UTC)
        current_date_str = now_utc.strftime("%Y-%m-%d")
        dq_entity = self._extract_dq_entity()

        return DQReportContext(
            run_id=str(self._context.run_id),
            pipeline_name=self._config.pipeline_name,
            timestamp=now_utc,
            provider=self._config.provider,
            entity=dq_entity,
            bronze_records=self._bronze_records_for_dq or None,
            bronze_batch_id=self._source_batch_ids[-1]
            if self._source_batch_ids
            else None,
            bronze_source_file=self._last_bronze_path,
            bronze_output_path=self._config.bronze_output_path,
            bronze_date_str=current_date_str,
            silver_data=silver_data,
            silver_target_table=self._config.table_config.silver_table,
            silver_source_batch_ids=self._source_batch_ids or None,
            silver_primary_keys=primary_keys or None,
            silver_input_count=self.records_fetched,
            silver_quarantined_count=self.records_quarantined,
            silver_output_path=self._config.silver_output_path,
            silver_key_nullability_rules=key_nullability_rules,
            gold_data=gold_data,
            gold_target_table=self._config.table_config.gold_table,
            gold_scd_config=self._config.scd_config,
            gold_output_path=self._config.gold_output_path,
            dq_soft_threshold=soft_threshold,
            dq_hard_threshold=hard_threshold,
            flat_structure=self._config.flat_structure,
        )
