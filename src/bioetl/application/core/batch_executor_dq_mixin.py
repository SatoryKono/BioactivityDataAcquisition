"""DQ context and accumulation helpers for BatchExecutor."""

from __future__ import annotations

import hashlib
import json
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
from bioetl.domain.normalization import canonicalize_json_string
from bioetl.domain.types import BatchID, BronzeRecord, GoldRecord

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_aux_service_protocols import (
        PipelineExecutionServicesProtocol,
    )
    from bioetl.application.core.record_processor_config import RecordProcessorConfig
    from bioetl.application.services.dq_report_service import DQReportContext
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort

# Maximum DQ sample size to prevent OOM on large pipeline runs.
# Uses deterministic content-ranked sampling to keep exact-replay side effects
# stable across repeated runs over the same input corpus.
_DQ_MAX_SAMPLE_SIZE = 50_000
_ReservoirT = TypeVar("_ReservoirT")


class _BatchExecutorDQMixin:
    """Provides DQ data collection and report context construction.

    Accumulates Bronze/Silver/Gold record samples during pipeline execution using
    deterministic content-ranked selection to keep memory bounded at
    ``_DQ_MAX_SAMPLE_SIZE`` records. Once the sample is full, only records with a
    lexicographically smaller stable content rank replace existing entries. This
    keeps replay-facing DQ side effects deterministic across repeated runs over the
    same input corpus.
    """

    _services: PipelineExecutionServicesProtocol
    _context: PipelineContext
    _config: RecordProcessorConfig
    _logger: LoggerPort
    _bronze_records_for_dq: list[bytes]
    _silver_records_for_dq: list[BronzeRecord]
    _gold_records_for_dq: list[GoldRecord]
    _source_batch_ids: list[str]
    _last_bronze_path: str | None
    _dq_total_seen: int
    _dq_reservoir_ranks: dict[int, list[str]]
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
                encoded = json.dumps(
                    record,
                    default=str,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
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
        """Add item to a bounded deterministic sample ranked by stable content."""
        if not hasattr(self, "_dq_total_seen"):
            self._dq_total_seen = 0
        if not hasattr(self, "_dq_reservoir_ranks"):
            self._dq_reservoir_ranks = {}
        self._dq_total_seen += 1
        reservoir_ranks = self._dq_reservoir_ranks.setdefault(id(reservoir), [])
        item_rank = self._dq_sample_rank(item)

        if len(reservoir) < _DQ_MAX_SAMPLE_SIZE:
            reservoir.append(item)
            reservoir_ranks.append(item_rank)
            return

        worst_index = max(
            range(len(reservoir_ranks)),
            key=reservoir_ranks.__getitem__,
        )
        if item_rank >= reservoir_ranks[worst_index]:
            return

        reservoir[worst_index] = item
        reservoir_ranks[worst_index] = item_rank

    @classmethod
    def _dq_sample_rank(cls, item: object) -> str:
        """Return a stable rank key for one DQ sample item."""
        payload = cls._serialize_dq_sample_item(item)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _serialize_dq_sample_item(item: object) -> str:
        """Serialize one DQ sample item into a stable comparable payload."""
        if isinstance(item, bytes):
            try:
                decoded = item.decode("utf-8")
            except UnicodeDecodeError:
                return item.hex()
            canonical_json = canonicalize_json_string(decoded)
            return canonical_json if canonical_json is not None else decoded
        return json.dumps(
            item,
            default=str,
            sort_keys=True,
            separators=(",", ":"),
        )

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
