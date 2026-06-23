from __future__ import annotations

import pytest

import pyarrow as pa

from bioetl.infrastructure.storage.delta.schema_ops import (
    drop_nondeterministic_persisted_fields,
)


pytestmark = pytest.mark.unit


def test_drop_nondeterministic_persisted_fields_removes_runtime_provenance() -> None:
    table = pa.table(
        {
            "entity_id": ["chembl:1"],
            "_run_id": ["run-1"],
            "_run_type": ["incremental"],
            "_source_batch_id": ["batch-1"],
            "_ingestion_ts": ["2026-04-10T14:00:00Z"],
            "_composite_run_id": ["composite-1"],
            "_lineage_created_at": ["2026-04-10T14:00:01Z"],
        }
    )

    result = drop_nondeterministic_persisted_fields(table)

    assert result.column_names == ["entity_id"]
