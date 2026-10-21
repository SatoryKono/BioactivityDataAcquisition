"""Already persisted Gold outcome quarantine cannot be duplicated or called written."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pandera.pandas as pa
import pytest

from bioetl.application.core._batch_write_schema_quarantine import (
    _records_without_outcome_quarantine,
    quarantine_schema_violation,
)
from bioetl.application.core._batch_write_support import (
    LayerWriteContext,
    safe_write_gold,
)
from bioetl.domain.config.validation import FieldValidation
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types.dq_contracts import DQDisposition
from tests.helpers.deterministic_ids import deterministic_batch_uuid_from_callsite
from tests.unit.application.core.test_gold_outcome_quarantine_routing import (
    _config,
    _gold_validator,
    _writer,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("indexes", [None, (), (True,), ("0",)])
def test_malformed_or_empty_quarantine_indexes_do_not_drop_unpersisted_rows(indexes):
    writer = SimpleNamespace(_gold_outcome_quarantine_indexes=indexes)
    records = [{"entity_id": "not-persisted"}]
    assert _records_without_outcome_quarantine(writer, records, "gold") == records
    assert writer._gold_outcome_quarantine_indexes == ()


@pytest.mark.asyncio
async def test_schema_failure_after_outcome_flush_does_not_quarantine_same_row_twice():
    writer = Mock(_gold_outcome_quarantine_indexes=(0,))
    manager = SimpleNamespace(quarantine_records=AsyncMock())
    context = SimpleNamespace(layer="gold", emit_failed=Mock(), logger=Mock())
    error = SchemaViolationError("gold", ["schema failure"])
    await quarantine_schema_violation(
        writer=writer,
        quarantine_manager=manager,
        event_context=context,
        records=[{"entity_id": "already-persisted"}],
        error=error,
    )
    manager.quarantine_records.assert_not_awaited()
    writer.track_batch_failed.assert_not_called()
    context.emit_failed.assert_called_once_with(error)


@pytest.mark.asyncio
async def test_all_outcome_quarantine_returns_no_written_count_and_skips_gold_storage():
    schema = pa.DataFrameSchema(
        {"entity_id": pa.Column(str), "name": pa.Column(str, nullable=True)}
    )
    config = _config(
        field_validations=(FieldValidation(field="name", validation_type="required"),),
        disposition_overrides=(("field.name.required", DQDisposition.QUARANTINE),),
    )
    quarantine = AsyncMock()
    writer, storage = _writer(
        _gold_validator(schema, config), quarantine, schema=schema
    )
    batch_id = deterministic_batch_uuid_from_callsite("all_outcome_quarantine")

    async def execute(name, operation, *args, **kwargs):
        return await operation

    context = LayerWriteContext(
        execute, writer, Mock(), writer._context.logger, writer._context.run_id, None
    )
    outcome = await safe_write_gold(
        context,
        [{"entity_id": "invalid", "name": None}],
        batch_id,
        datetime(2026, 10, 21, tzinfo=UTC),
        None,
        (OSError,),
    )
    assert outcome.status == "quarantined" and outcome.confirmed_count == 0
    assert outcome.quarantined_count == 1 and outcome.candidate_count == 1
    quarantine.write_many.assert_awaited_once()
    storage.write_gold.assert_not_awaited()
