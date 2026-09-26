"""Missing-table behavior for pre-merge schema evolution."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.silver import merge_resilience_helpers as resilience
from bioetl.infrastructure.storage.silver.delta_helpers import _DeltaWriteRequest

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_pre_evolution_skips_a_table_that_does_not_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A first merge remains a create path when no Delta table exists yet."""
    request = _DeltaWriteRequest(
        validated_mode=SilverWriteMode.MERGE,
        table_path="/data/silver/chembl/activity",
        arrow_data=pa.table({"activity_id": ["A1"]}),
        primary_keys=["activity_id"],
        partition_cols=None,
        merge_schema=True,
    )
    load_table = AsyncMock(side_effect=DeltaTableNotFoundError("not found"))
    evolve = AsyncMock()
    monkeypatch.setattr(resilience, "_load_delta_table", load_table)
    monkeypatch.setattr(resilience, "_evolve_delta_schema_with_empty_append", evolve)

    active_request, pre_evolved = await resilience._pre_evolve_existing_table_schema(
        request=request,
        load_module=MagicMock(),
    )

    assert active_request is request
    assert pre_evolved is False
    evolve.assert_not_awaited()
