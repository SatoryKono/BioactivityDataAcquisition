"""The compatibility Delta writer preserves the normalized quarantine row."""

from datetime import UTC, datetime

import pytest
from deltalake import DeltaTable

from bioetl.infrastructure.quarantine.unified import UnifiedQuarantineAdapter
from tests.helpers.deterministic_ids import deterministic_batch_uuid_from_callsite

pytestmark = pytest.mark.unit


def test_quarantine_delta_facade_writes_a_partitioned_normalized_record(tmp_path):
    writer = UnifiedQuarantineAdapter(str(tmp_path / "quarantine"))
    request = {
        "pipeline": "chembl_assay",
        "error_code": "DATA_QUALITY",
        "payload": {"id": "invalid"},
        "bronze_batch_id": deterministic_batch_uuid_from_callsite(
            "quarantine_delta_facade"
        ),
        "ingestion_ts": datetime(2026, 10, 21, tzinfo=UTC),
    }
    record = writer._normalize_record(request)
    writer._write_to_delta([record])
    table = DeltaTable(writer.base_path)
    assert table.metadata().partition_columns == ["pipeline"]
    assert table.to_pyarrow_table().to_pylist() == [record]
