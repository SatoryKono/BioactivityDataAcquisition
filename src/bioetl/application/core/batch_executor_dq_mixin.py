"""DQ context and accumulation helpers for BatchExecutor."""

from __future__ import annotations

import json
import random
from typing import TYPE_CHECKING, TypeVar

from bioetl.application.core.batch_executor_dq_helpers import (
    build_dataframe_from_records,
    build_dq_report_context,
    dataframe_error_types,
    extract_dq_entity,
    get_dq_thresholds,
    normalize_records_for_polars,
    stringify_value,
)
from bioetl.domain.types import BatchID, BronzeRecord, GoldRecord

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.services.dq_report_service import DQReportContext
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort

# Maximum DQ sample size to prevent OOM on large pipeline runs.
# Uses reservoir sampling to maintain a statistically representative subset.
_DQ_MAX_SAMPLE_SIZE = 50_000
_ReservoirT = TypeVar("_ReservoirT")


class _BatchExecutorDQMixin:
    """Provides DQ data collection and report context construction.

    Accumulates Bronze/Silver/Gold record samples during pipeline execution using
    reservoir sampling (Algorithm R) to keep memory bounded at ``_DQ_MAX_SAMPLE_SIZE``
    records. Once the reservoir is full, new records replace existing ones with
    decreasing probability, maintaining a statistically representative subset
    for post-run DQ report generation.
    """

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
        stage: str = "other",
    ) -> object | None:
        """Build Polars dataframe from records, returning None on failure."""
        return build_dataframe_from_records(
            records=records,
            logger=self._logger,
            metrics=self._services.metrics,
            pipeline=self._config.pipeline_name,
            stage=stage,
        )

    @staticmethod
    def _dataframe_error_types() -> tuple[type[Exception], ...]:
        """Resolve exception types raised while building Polars dataframes."""
        return dataframe_error_types()

    @staticmethod
    def _stringify_value(
        value: object, keys_to_stringify: set[str], key: str
    ) -> object:
        """Stringify a value if its key requires normalization."""
        return stringify_value(value, keys_to_stringify, key)

    @staticmethod
    def _normalize_records_for_polars(
        records: list[BronzeRecord] | list[GoldRecord],
    ) -> list[dict[str, object]] | None:
        """Normalize mixed nested/string columns to stable string representation.

        Polars may fail when one column mixes nested values (dict/list/tuple) with
        plain scalars/strings across rows. For such columns we stringify values so
        the dataframe builder sees a single consistent type.
        """
        return normalize_records_for_polars(records)

    def _get_dq_thresholds(self) -> tuple[float, float]:
        """Resolve DQ thresholds from config, falling back to defaults."""
        return get_dq_thresholds(self._config)

    def _extract_dq_entity(self) -> str:
        """Derive entity name for report naming from silver table naming."""
        return extract_dq_entity(self._config)

    def get_dq_context(self) -> DQReportContext | None:
        """Build report context from DQ data accumulated during execution.

        Returns:
            Populated DQReportContext for post-run DQ report generation, or None if
            no DQ report service is configured.
        """
        if not self._should_collect_dq_data():
            return None
        return build_dq_report_context(
            context=self._context,
            config=self._config,
            bronze_records=self._bronze_records_for_dq,
            silver_records=self._silver_records_for_dq,
            gold_records=self._gold_records_for_dq,
            source_batch_ids=self._source_batch_ids,
            last_bronze_path=self._last_bronze_path,
            records_fetched=self.records_fetched,
            records_quarantined=self.records_quarantined,
            build_dataframe=self._build_dataframe_from_records,
        )
