# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
"""Regression suite for RC-APP-WRITE-OUTCOME-LOSS (issue #12097, FIX-01/FIX-04).

Every scenario drives the real ``safe_write_layer`` / ``write_silver_then_gold``
choreography and the executor state-update helpers. Only external fault seams
(writer port, quarantine port) are substituted — internal outcome passing is
exercised end to end.

Baseline fixture: 3 source records -> 3 Silver candidates -> 3 Gold
candidates, transform quarantine = 0.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.application.core._batch_processing_layer_write_support import (
    write_silver_then_gold,
)
from bioetl.application.core.batch_execution.contracts import (  # noqa: F401
    BatchExecutionStateProtocol,
)
from bioetl.application.core.batch_executor_helpers import (
    apply_processed_batch_outcome,
    build_processed_batch_outcome,
)
from bioetl.application.core.batch_executor_runtime_state import (
    BatchExecutorRuntimeState,
)
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_processing_contracts import (
    BatchProcessingOutcome,
    LayerWriteOutcome,
    SilverGoldWriteOutcome,
)
from bioetl.application.core.batch_transformer import TransformResult
from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types import BatchID

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord, GoldRecord

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

INGESTION_TS = datetime(2026, 10, 7, tzinfo=UTC)
BATCH_ID = BatchID(UUID("11111111-2222-4333-8444-555555555555"))


def _records(n: int, prefix: str = "r") -> list[dict[str, object]]:
    return [{"id": f"{prefix}{idx}"} for idx in range(n)]


def _make_transform_result(
    *,
    silver: list | None = None,
    gold: list | None = None,
    quarantined: int = 0,
    filtered_out: int = 0,
    gold_excluded: int = 0,
) -> TransformResult:
    return TransformResult(
        silver_records=silver if silver is not None else _records(3),
        gold_records=gold if gold is not None else _records(3, "g"),
        quarantined_count=quarantined,
        filtered_out_count=filtered_out,
        gold_excluded_by_contract_count=gold_excluded,
    )


def _make_writer(
    *,
    silver_error: BaseException | None = None,
    gold_error: BaseException | None = None,
) -> MagicMock:
    silver_result = MagicMock(name="silver_result")
    writer = MagicMock(name="writer")
    writer.write_silver = AsyncMock(
        side_effect=silver_error, return_value=silver_result
    )
    writer.write_gold = AsyncMock(side_effect=gold_error, return_value=None)
    return writer


def _make_quarantine(
    *, port_error: BaseException | None = None
) -> tuple[QuarantineRuntimeService, MagicMock]:
    port = MagicMock(name="quarantine_port")
    port.write_many = AsyncMock(side_effect=port_error, return_value=None)
    metrics = BatchMetricsRecorderService(None, "test_entity", "incremental")
    manager = QuarantineRuntimeService(port, "test_entity", batch_metrics=metrics)
    return manager, port


async def _passthrough_span(
    _name: object,
    operation: object,
    *_args: object,
    **_kwargs: object,
) -> object:
    return await cast("asyncio.Future[object]", operation)


async def _run_choreography(
    *,
    transform_result: TransformResult | None = None,
    writer: MagicMock | None = None,
    quarantine: QuarantineRuntimeService | None = None,
    batch_metrics: BatchMetricsRecorderService | None = None,
) -> SilverGoldWriteOutcome:
    return await write_silver_then_gold(
        execute_with_span=_passthrough_span,
        writer=writer or _make_writer(),
        quarantine_manager=quarantine or _make_quarantine()[0],
        logger=MagicMock(name="logger"),
        batch_metrics=batch_metrics
        or BatchMetricsRecorderService(None, "test_entity", "incremental"),
        run_id=None,
        domain_event_emitter=None,
        transform_result=transform_result or _make_transform_result(),
        batch_id=BATCH_ID,
        ingestion_ts=INGESTION_TS,
        bronze_refs=None,
    )


def _make_batch_outcome(
    *,
    transform_result: TransformResult,
    write_outcome: SilverGoldWriteOutcome,
) -> BatchProcessingOutcome:
    """Mirror BatchProcessingService._process_batch_work outcome assembly."""
    return BatchProcessingOutcome(
        batch_id=BATCH_ID,
        bronze_result=MagicMock(name="bronze_result"),
        silver_records=transform_result.silver_records,
        gold_records=transform_result.gold_records,
        quarantined_count=transform_result.quarantined_count,
        filtered_out_count=transform_result.filtered_out_count,
        silver_write=write_outcome.silver,
        gold_write=write_outcome.gold,
        gold_excluded_by_contract_count=(
            transform_result.gold_excluded_by_contract_count
        ),
    )


class _ExecutorStateHarness:
    """Executor-state double capturing counters and DQ payloads."""

    def __init__(self, *, collect_dq: bool = True) -> None:
        self._runtime = BatchExecutorRuntimeState()
        self._collect_dq = collect_dq
        self.dq_calls: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._runtime, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"_runtime", "_collect_dq", "dq_calls"}:
            object.__setattr__(self, name, value)
        else:
            setattr(self._runtime, name, value)

    def should_collect_dq_data(self) -> bool:
        return self._collect_dq

    def collect_dq_data(
        self,
        records: list[BronzeRecord],
        batch_id: BatchID,
        bronze_result: object,
        silver_records: list[BronzeRecord],
        gold_records: list[GoldRecord],
    ) -> None:
        self.dq_calls.append(
            {
                "records": records,
                "batch_id": batch_id,
                "bronze_result": bronze_result,
                "silver_records": silver_records,
                "gold_records": gold_records,
            }
        )


def _commit(
    state: _ExecutorStateHarness,
    *,
    records: list[dict[str, object]],
    outcome: BatchProcessingOutcome,
) -> None:
    apply_processed_batch_outcome(
        state=state,
        outcome=build_processed_batch_outcome(records=records, output=outcome),
    )


# ---------------------------------------------------------------------------
# S1 — Silver schema quarantine
# ---------------------------------------------------------------------------


async def test_s1_silver_schema_quarantine_blocks_gold() -> None:
    """Silver schema failure quarantines Silver and blocks Gold upstream."""
    writer = _make_writer(silver_error=SchemaViolationError("silver", ["bad"]))
    quarantine, port = _make_quarantine()
    transform_result = _make_transform_result()

    outcome = await _run_choreography(
        transform_result=transform_result,
        writer=writer,
        quarantine=quarantine,
    )

    assert outcome.silver.status == "quarantined"
    assert outcome.silver.candidate_count == 3
    assert outcome.silver.confirmed_count == 0
    assert outcome.silver.quarantined_count == 3
    # Gold must be marked blocked — never invoked, not quarantined.
    assert outcome.gold.status == "blocked"
    assert outcome.gold.candidate_count == 3
    assert outcome.gold.confirmed_count == 0
    assert outcome.gold.quarantined_count == 0
    writer.write_gold.assert_not_awaited()
    port.write_many.assert_awaited_once()

    state = _ExecutorStateHarness()
    _commit(
        state,
        records=_records(3),
        outcome=_make_batch_outcome(
            transform_result=transform_result, write_outcome=outcome
        ),
    )
    assert state.records_silver == 0
    assert state.records_gold == 0
    assert state.records_quarantined == 3
    assert state.records_quarantined_silver == 3
    assert state.records_quarantined_gold == 0
    # No fictitious persisted Silver/Gold payload reaches DQ buffers.
    assert state.dq_calls[0]["silver_records"] == []
    assert state.dq_calls[0]["gold_records"] == []


# ---------------------------------------------------------------------------
# S2 — Gold schema quarantine
# ---------------------------------------------------------------------------


async def test_s2_gold_schema_quarantine_preserves_confirmed_silver() -> None:
    """Gold quarantine keeps confirmed Silver result and lineage refs."""
    writer = _make_writer(gold_error=SchemaViolationError("gold", ["bad"]))
    quarantine, port = _make_quarantine()
    transform_result = _make_transform_result()

    outcome = await _run_choreography(
        transform_result=transform_result,
        writer=writer,
        quarantine=quarantine,
    )

    assert outcome.silver.status == "written"
    assert outcome.silver.confirmed_count == 3
    assert outcome.silver.write_result is not None
    assert outcome.gold.status == "quarantined"
    assert outcome.gold.quarantined_count == 3
    # Gold write received the confirmed Silver refs.
    gold_kwargs = writer.write_gold.await_args.kwargs
    assert gold_kwargs["silver_refs"] == [outcome.silver.write_result]
    port.write_many.assert_awaited_once()

    state = _ExecutorStateHarness()
    _commit(
        state,
        records=_records(3),
        outcome=_make_batch_outcome(
            transform_result=transform_result, write_outcome=outcome
        ),
    )
    assert state.records_silver == 3
    assert state.records_gold == 0
    assert state.records_quarantined == 3
    # Gold-stage rejection must not inflate the Silver-path counter.
    assert state.records_quarantined_silver == 0
    assert state.records_quarantined_gold == 3
    # Confirmed Silver payload persists in DQ; Gold is excluded.
    assert state.dq_calls[0]["silver_records"] == transform_result.silver_records
    assert state.dq_calls[0]["gold_records"] == []


# ---------------------------------------------------------------------------
# S3 — Transport error (control scenario)
# ---------------------------------------------------------------------------


async def test_s3_transport_error_propagates_without_commit() -> None:
    """Operational errors propagate; no outcome and no batch commit."""
    writer = _make_writer(silver_error=OSError("connection reset"))
    quarantine, port = _make_quarantine()

    with pytest.raises(OSError, match="connection reset"):
        await _run_choreography(writer=writer, quarantine=quarantine)

    writer.write_gold.assert_not_awaited()
    port.write_many.assert_not_awaited()


# ---------------------------------------------------------------------------
# S4 — Quarantine port failure
# ---------------------------------------------------------------------------


async def test_s4_quarantine_port_failure_propagates() -> None:
    """Quarantine-write errors propagate; no fictitious quarantine outcome."""
    writer = _make_writer(silver_error=SchemaViolationError("silver", ["bad"]))
    quarantine, port = _make_quarantine(port_error=OSError("delta io"))
    transform_result = _make_transform_result()

    with pytest.raises(OSError, match="delta io"):
        await _run_choreography(
            transform_result=transform_result,
            writer=writer,
            quarantine=quarantine,
        )

    port.write_many.assert_awaited_once()
    writer.write_gold.assert_not_awaited()


# ---------------------------------------------------------------------------
# S5 — Transform + write quarantine stay distinguishable
# ---------------------------------------------------------------------------


async def test_s5_transform_and_write_quarantine_are_distinguishable() -> None:
    """Transform-stage and write-stage quarantine origins remain separate."""
    writer = _make_writer(gold_error=SchemaViolationError("gold", ["bad"]))
    transform_result = _make_transform_result(quarantined=1)

    outcome = await _run_choreography(
        transform_result=transform_result,
        writer=writer,
        quarantine=_make_quarantine()[0],
    )
    batch_outcome = _make_batch_outcome(
        transform_result=transform_result, write_outcome=outcome
    )

    assert batch_outcome.quarantined_count == 1  # transform stage
    assert batch_outcome.write_quarantined_count == 3  # write stage
    assert batch_outcome.total_quarantined_count == 4
    assert batch_outcome.silver_quarantined_count == 1
    assert batch_outcome.gold_quarantined_count == 3

    state = _ExecutorStateHarness()
    _commit(state, records=_records(4), outcome=batch_outcome)
    assert state.records_quarantined == 4
    assert state.records_quarantined_silver == 1
    assert state.records_quarantined_gold == 3


# ---------------------------------------------------------------------------
# S6 — Filtering stays filtering
# ---------------------------------------------------------------------------


async def test_s6_filtered_rows_are_not_write_quarantine() -> None:
    transform_result = _make_transform_result(filtered_out=2)

    outcome = await _run_choreography(transform_result=transform_result)
    batch_outcome = _make_batch_outcome(
        transform_result=transform_result, write_outcome=outcome
    )
    state = _ExecutorStateHarness()
    _commit(state, records=_records(5), outcome=batch_outcome)

    assert state.records_filtered_out == 2
    assert state.records_quarantined == 0
    assert outcome.silver.status == "written"
    assert outcome.gold.status == "written"


# ---------------------------------------------------------------------------
# S7 — Gold contract exclusions are not quarantine
# ---------------------------------------------------------------------------


async def test_s7_gold_exclusions_keep_separate_disposition() -> None:
    transform_result = _make_transform_result(gold_excluded=1)

    outcome = await _run_choreography(transform_result=transform_result)
    batch_outcome = _make_batch_outcome(
        transform_result=transform_result, write_outcome=outcome
    )
    state = _ExecutorStateHarness()
    _commit(state, records=_records(4), outcome=batch_outcome)

    assert state.records_gold_excluded_by_contract == 1
    assert state.records_quarantined == 0
    assert state.records_quarantined_gold == 0


# ---------------------------------------------------------------------------
# S8 — One-to-many derived rows counted in layer units
# ---------------------------------------------------------------------------


async def test_s8_one_to_many_counts_in_candidate_units() -> None:
    """Derived Silver/Gold rows are counted per layer, not per source record."""
    transform_result = _make_transform_result(silver=_records(6), gold=_records(4, "g"))

    outcome = await _run_choreography(transform_result=transform_result)
    batch_outcome = _make_batch_outcome(
        transform_result=transform_result, write_outcome=outcome
    )
    state = _ExecutorStateHarness()
    _commit(state, records=_records(3), outcome=batch_outcome)

    assert state.records_bronze == 3
    assert state.records_silver == 6
    assert state.records_gold == 4
    # Yields may exceed 1.0 for expansion; no clamping is applied anywhere.
    assert outcome.silver.confirmed_count == 6


# ---------------------------------------------------------------------------
# S9 — Empty stages: skipped is not quarantine
# ---------------------------------------------------------------------------


async def test_s9_empty_stages_are_skipped_not_quarantined() -> None:
    transform_result = _make_transform_result(silver=[], gold=[])

    outcome = await _run_choreography(transform_result=transform_result)

    assert outcome.silver.status == "skipped"
    assert outcome.gold.status == "skipped"
    assert outcome.silver.quarantined_count == 0
    assert outcome.gold.quarantined_count == 0

    state = _ExecutorStateHarness()
    _commit(
        state,
        records=_records(2),
        outcome=_make_batch_outcome(
            transform_result=transform_result, write_outcome=outcome
        ),
    )
    assert state.records_quarantined == 0
    assert state.dq_calls[0]["silver_records"] == []


# ---------------------------------------------------------------------------
# S10 — Multiple batches accumulate each side effect once
# ---------------------------------------------------------------------------


async def test_s10_multiple_batches_accumulate_outcomes() -> None:
    transform_result = _make_transform_result()
    writer = _make_writer(gold_error=SchemaViolationError("gold", ["bad"]))
    state = _ExecutorStateHarness()

    first = await _run_choreography(transform_result=transform_result)
    second = await _run_choreography(transform_result=transform_result, writer=writer)
    for write_outcome in (first, second):
        _commit(
            state,
            records=_records(3),
            outcome=_make_batch_outcome(
                transform_result=transform_result, write_outcome=write_outcome
            ),
        )

    # Batch 1: 3/3/3, batch 2: 3 silver + 3 gold-quarantined.
    assert state.records_bronze == 6
    assert state.records_silver == 6
    assert state.records_gold == 3
    assert state.records_quarantined == 3
    assert state.records_quarantined_gold == 3
    assert len(state.dq_calls) == 2


# ---------------------------------------------------------------------------
# S11 — Replay determinism
# ---------------------------------------------------------------------------


async def test_s11_repeated_batches_produce_deterministic_counters() -> None:
    """Same input through the same chain yields identical counters (replay)."""

    async def _run_once() -> dict[str, int]:
        transform_result = _make_transform_result()
        outcome = await _run_choreography(transform_result=transform_result)
        state = _ExecutorStateHarness()
        _commit(
            state,
            records=_records(3),
            outcome=_make_batch_outcome(
                transform_result=transform_result, write_outcome=outcome
            ),
        )
        return {
            "bronze": state.records_bronze,
            "silver": state.records_silver,
            "gold": state.records_gold,
            "quarantined": state.records_quarantined,
        }

    assert await _run_once() == await _run_once()


# ---------------------------------------------------------------------------
# S12 — Cancellation is not converted into success/quarantine
# ---------------------------------------------------------------------------


async def test_s12_cancellation_propagates_unchanged() -> None:
    writer = _make_writer(silver_error=asyncio.CancelledError())
    quarantine, port = _make_quarantine()

    with pytest.raises(asyncio.CancelledError):
        await _run_choreography(writer=writer, quarantine=quarantine)

    writer.write_gold.assert_not_awaited()
    port.write_many.assert_not_awaited()


# ---------------------------------------------------------------------------
# S13 — Cancellation during quarantine write stays a cancellation
# ---------------------------------------------------------------------------


async def test_s13_cancellation_during_quarantine_is_not_masked() -> None:
    writer = _make_writer(silver_error=SchemaViolationError("silver", ["bad"]))
    quarantine, _port = _make_quarantine(port_error=asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await _run_choreography(writer=writer, quarantine=quarantine)


# ---------------------------------------------------------------------------
# S14 — Single owner per side effect (no double publish)
# ---------------------------------------------------------------------------


async def test_s14_write_side_effects_have_single_owner() -> None:
    transform_result = _make_transform_result()
    writer = _make_writer()
    batch_metrics = MagicMock(
        wraps=BatchMetricsRecorderService(None, "test_entity", "incremental")
    )

    await _run_choreography(
        transform_result=transform_result,
        writer=writer,
        batch_metrics=batch_metrics,
    )

    # track_batch_written is the single write-confirmation publisher per layer.
    assert writer.track_batch_written.call_count == 2
    writer.track_batch_written.assert_any_call(stage="silver", count=3)
    writer.track_batch_written.assert_any_call(stage="gold", count=3)


# ---------------------------------------------------------------------------
# DTO-level invariants
# ---------------------------------------------------------------------------


async def test_outcome_dto_blocks_fictitious_confirmed_records() -> None:
    """Confirmed-record projections empty when the layer did not write."""
    outcome = BatchProcessingOutcome(
        batch_id=BATCH_ID,
        bronze_result=None,
        silver_records=_records(3),
        gold_records=_records(3, "g"),
        quarantined_count=0,
        filtered_out_count=0,
        silver_write=LayerWriteOutcome(
            layer="silver",
            status="quarantined",
            candidate_count=3,
            quarantined_count=3,
        ),
        gold_write=LayerWriteOutcome(layer="gold", status="blocked", candidate_count=3),
    )
    assert outcome.confirmed_silver_records == []
    assert outcome.confirmed_gold_records == []
    assert outcome.silver_quarantined_count == 3
    assert outcome.gold_quarantined_count == 0
    assert outcome.total_quarantined_count == 3


async def test_dq_hook_skipped_when_disabled() -> None:
    state = _ExecutorStateHarness(collect_dq=False)
    _commit(
        state,
        records=_records(3),
        outcome=_make_batch_outcome(
            transform_result=_make_transform_result(),
            write_outcome=await _run_choreography(),
        ),
    )
    assert state.dq_calls == []
