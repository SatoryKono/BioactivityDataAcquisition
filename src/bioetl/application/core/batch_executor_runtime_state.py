# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Runtime state container for BatchExecutor orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord, GoldRecord

__all__ = ["BatchExecutorRuntimeState", "BatchExecutorRuntimeStateMixin"]


@dataclass(slots=True)
class BatchExecutorRuntimeState:
    """Mutable execution state owned outside the BatchExecutor coordinator."""

    records_fetched: int = 0
    records_bronze: int = 0
    records_silver: int = 0
    records_gold: int = 0
    records_gold_excluded_by_contract: int = 0
    records_quarantined: int = 0
    records_filtered_out: int = 0
    bronze_records_for_dq: list[bytes] = field(default_factory=list)
    silver_records_for_dq: list[BronzeRecord] = field(default_factory=list)
    gold_records_for_dq: list[GoldRecord] = field(default_factory=list)
    dq_total_seen: int = 0
    # Stage-keyed ranks ("bronze"/"silver"/"gold") — not id(list).
    dq_reservoir_ranks: dict[str, list[str]] = field(default_factory=dict)
    source_batch_ids: list[str] = field(default_factory=list)
    last_bronze_path: str | None = None
    debug_export_result: object | None = None
    resume_offset: int = 0
    query_string: str | None = None


class BatchExecutorRuntimeStateMixin:
    """Expose legacy executor state attributes backed by one state object."""

    # Host sets this in BatchExecutor.__init__ (or test fixtures) before access.
    _runtime_state: BatchExecutorRuntimeState = cast(Any, None)  # Any: host default (PD4)

    @property
    def records_fetched(self) -> int:
        return self._runtime_state.records_fetched

    @records_fetched.setter
    def records_fetched(self, value: int) -> None:
        self._runtime_state.records_fetched = value

    @property
    def records_bronze(self) -> int:
        return self._runtime_state.records_bronze

    @records_bronze.setter
    def records_bronze(self, value: int) -> None:
        self._runtime_state.records_bronze = value

    @property
    def records_silver(self) -> int:
        return self._runtime_state.records_silver

    @records_silver.setter
    def records_silver(self, value: int) -> None:
        self._runtime_state.records_silver = value

    @property
    def records_gold(self) -> int:
        return self._runtime_state.records_gold

    @records_gold.setter
    def records_gold(self, value: int) -> None:
        self._runtime_state.records_gold = value

    @property
    def records_gold_excluded_by_contract(self) -> int:
        return self._runtime_state.records_gold_excluded_by_contract

    @records_gold_excluded_by_contract.setter
    def records_gold_excluded_by_contract(self, value: int) -> None:
        self._runtime_state.records_gold_excluded_by_contract = value

    @property
    def records_quarantined(self) -> int:
        return self._runtime_state.records_quarantined

    @records_quarantined.setter
    def records_quarantined(self, value: int) -> None:
        self._runtime_state.records_quarantined = value

    @property
    def records_filtered_out(self) -> int:
        return self._runtime_state.records_filtered_out

    @records_filtered_out.setter
    def records_filtered_out(self, value: int) -> None:
        self._runtime_state.records_filtered_out = value

    @property
    def _bronze_records_for_dq(self) -> list[bytes]:
        return self._runtime_state.bronze_records_for_dq

    @_bronze_records_for_dq.setter
    def _bronze_records_for_dq(self, value: list[bytes]) -> None:
        self._runtime_state.bronze_records_for_dq = value

    @property
    def _silver_records_for_dq(self) -> list[BronzeRecord]:
        return self._runtime_state.silver_records_for_dq

    @_silver_records_for_dq.setter
    def _silver_records_for_dq(self, value: list[BronzeRecord]) -> None:
        self._runtime_state.silver_records_for_dq = value

    @property
    def _gold_records_for_dq(self) -> list[GoldRecord]:
        return self._runtime_state.gold_records_for_dq

    @_gold_records_for_dq.setter
    def _gold_records_for_dq(self, value: list[GoldRecord]) -> None:
        self._runtime_state.gold_records_for_dq = value

    @property
    def _dq_total_seen(self) -> int:
        return self._runtime_state.dq_total_seen

    @_dq_total_seen.setter
    def _dq_total_seen(self, value: int) -> None:
        self._runtime_state.dq_total_seen = value

    @property
    def _dq_reservoir_ranks(self) -> dict[str, list[str]]:
        return self._runtime_state.dq_reservoir_ranks

    @_dq_reservoir_ranks.setter
    def _dq_reservoir_ranks(self, value: dict[str, list[str]]) -> None:
        self._runtime_state.dq_reservoir_ranks = value

    @property
    def source_batch_ids(self) -> list[str]:
        """Public list of source batch IDs accumulated during the run."""
        return self._runtime_state.source_batch_ids

    @source_batch_ids.setter
    def source_batch_ids(self, value: list[str]) -> None:
        self._runtime_state.source_batch_ids = value

    @property
    def _last_bronze_path(self) -> str | None:
        return self._runtime_state.last_bronze_path

    @_last_bronze_path.setter
    def _last_bronze_path(self, value: str | None) -> None:
        self._runtime_state.last_bronze_path = value

    @property
    def _debug_export_result(self) -> object | None:
        return self._runtime_state.debug_export_result

    @_debug_export_result.setter
    def _debug_export_result(self, value: object | None) -> None:
        self._runtime_state.debug_export_result = value

    @property
    def _resume_offset(self) -> int:
        return self._runtime_state.resume_offset

    @_resume_offset.setter
    def _resume_offset(self, value: int) -> None:
        self._runtime_state.resume_offset = value

    @property
    def _query_string(self) -> str | None:
        return self._runtime_state.query_string

    @_query_string.setter
    def _query_string(self, value: str | None) -> None:
        self._runtime_state.query_string = value
