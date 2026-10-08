# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
"""Integration regression for RC-APP-WRITE-OUTCOME-LOSS (issue #12097).

Drives the real ``write_silver_then_gold`` choreography with a real
``QuarantineRuntimeService`` backed by ``UnifiedQuarantineAdapter`` on a
temporary Delta table, then re-opens the store and reads back persisted
quarantine records.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast
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
)
from bioetl.application.core.batch_transformer import TransformResult
from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types import BatchID
from bioetl.infrastructure.quarantine.unified import UnifiedQuarantineAdapter

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

INGESTION_TS = datetime(2026, 10, 7, tzinfo=UTC)
BATCH_ID = BatchID(UUID("11111111-2222-4333-8444-555555555555"))


def _records(n: int, prefix: str = "r") -> list[dict[str, object]]:
    return [{"id": f"{prefix}{idx}"} for idx in range(n)]


def _transform_result(
    silver: list | None = None,
    gold: list | None = None,
) -> TransformResult:
    return TransformResult(
        silver_records=silver if silver is not None else _records(3),
        gold_records=gold if gold is not None else _records(3, "g"),
        quarantined_count=0,
        filtered_out_count=0,
        gold_excluded_by_contract_count=0,
    )


async def _passthrough_span(
    _name: object,
    operation: object,
    *_args: object,
    **_kwargs: object,
) -> object:
    return await cast("object", operation)


def _writer(*, silver_error=None, gold_error=None) -> MagicMock:
    writer = MagicMock(name="writer")
    writer.write_silver = AsyncMock(
        side_effect=silver_error, return_value=MagicMock(name="silver_result")
    )
    writer.write_gold = AsyncMock(side_effect=gold_error, return_value=None)
    return writer


def _quarantine(tmp_path, batch_metrics=None) -> QuarantineRuntimeService:
    return QuarantineRuntimeService(
        UnifiedQuarantineAdapter(str(tmp_path / "quarantine")),
        "test_entity",
        metrics=None,
        batch_metrics=batch_metrics
        or BatchMetricsRecorderService(None, "test_entity", "incremental"),
    )


async def _run(tmp_path, *, transform_result=None, writer=None) -> object:
    return await write_silver_then_gold(
        execute_with_span=_passthrough_span,
        writer=writer or _writer(),
        quarantine_manager=_quarantine(tmp_path),
        logger=MagicMock(name="logger"),
        batch_metrics=BatchMetricsRecorderService(None, "test_entity", "incremental"),
        run_id=None,
        domain_event_emitter=None,
        transform_result=transform_result or _transform_result(),
        batch_id=BATCH_ID,
        ingestion_ts=INGESTION_TS,
        bronze_refs=None,
    )


async def _inspect(tmp_path) -> list[dict]:
    # Re-open the store and read persisted rows back from the Delta log.
    # NOTE: UnifiedQuarantineAdapter.inspect() assumes a pipeline-partitioned
    # table; tables created by _write_records_to_delta are unpartitioned
    # (the TableNotFoundError branch never fires on first append), so we read
    # via DeltaTable directly. Recorded as a residual adapter finding.
    from deltalake import DeltaTable

    table = DeltaTable(str(tmp_path / "quarantine"))
    return table.to_pyarrow_table().to_pylist()


async def test_silver_schema_quarantine_persists_real_records(tmp_path) -> None:
    """Silver schema failure persists all candidates to real quarantine."""
    writer = _writer(silver_error=SchemaViolationError("silver", ["bad"]))
    transform_result = _transform_result()

    outcome = await _run(tmp_path, transform_result=transform_result, writer=writer)

    assert outcome.silver.status == "quarantined"
    assert outcome.silver.quarantined_count == 3
    assert outcome.gold.status == "blocked"
    writer.write_gold.assert_not_awaited()

    persisted = await _inspect(tmp_path)
    assert len(persisted) == 3
    payloads = {json.loads(entry["payload"])["id"] for entry in persisted}
    assert payloads == {"r0", "r1", "r2"}
    assert {entry["error_code"] for entry in persisted} == {"SCHEMA_VIOLATION"}
    assert {entry["dq_status"] for entry in persisted} == {"NEW"}
    assert {entry["bronze_batch_id"] for entry in persisted} == {str(BATCH_ID)}

    # Executor projection sees confirmed-zero Silver/Gold.
    class _State(BatchExecutorRuntimeState):
        def should_collect_dq_data(self) -> bool:
            return False

        def collect_dq_data(self, *a, **kw) -> None:
            raise AssertionError("unreachable")

    state = _State()
    apply_processed_batch_outcome(
        state=state,
        outcome=build_processed_batch_outcome(
            records=_records(3),
            output=BatchProcessingOutcome(
                batch_id=BATCH_ID,
                bronze_result=None,
                silver_records=transform_result.silver_records,
                gold_records=transform_result.gold_records,
                quarantined_count=0,
                filtered_out_count=0,
                silver_write=outcome.silver,
                gold_write=outcome.gold,
            ),
        ),
    )
    assert state.records_silver == 0
    assert state.records_gold == 0
    assert state.records_quarantined == 3
    assert state.records_quarantined_silver == 3
    assert state.records_quarantined_gold == 0


async def test_gold_schema_quarantine_keeps_silver_and_persists_gold(
    tmp_path,
) -> None:
    """Gold schema failure persists Gold candidates, keeps Silver confirmed."""
    writer = _writer(gold_error=SchemaViolationError("gold", ["bad"]))
    transform_result = _transform_result()

    outcome = await _run(tmp_path, transform_result=transform_result, writer=writer)

    assert outcome.silver.status == "written"
    assert outcome.gold.status == "quarantined"
    gold_refs = writer.write_gold.await_args.kwargs["silver_refs"]
    assert gold_refs == [outcome.silver.write_result]

    persisted = await _inspect(tmp_path)
    assert len(persisted) == 3
    payloads = {json.loads(entry["payload"])["id"] for entry in persisted}
    assert payloads == {"g0", "g1", "g2"}
    details = {entry["error_details"] for entry in persisted}
    assert any(
        "gold" in json.loads(d).get("message", d) or "gold" in d for d in details
    )
