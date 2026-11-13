"""Real Arrow scan regression coverage for quarantine read budgets."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
import pyarrow as pa
import pyarrow.dataset as ds
import pytest
from bioetl.infrastructure.quarantine.filtered_reads import (
    _load_bounded_scoped_pyarrow_table,
)

pytestmark = pytest.mark.unit


class Table:
    def __init__(self, table):
        self.table = table

    def metadata(self):
        return SimpleNamespace(partition_columns=[])

    def to_pyarrow_dataset(self, *, partitions):
        return ds.dataset(self.table)


@pytest.mark.parametrize("rows,width", [(10001, 1), (2, 5 * 1024 * 1024)])
def test_scan_rejects_excess_before_python_materialization(rows, width):
    table = pa.table({"pipeline": ["audit"] * rows, "value": ["x" * width] * rows})
    with pytest.raises(RuntimeError, match="budget exceeded"):
        _load_bounded_scoped_pyarrow_table(Table(table), pipeline_single="audit")


def test_scan_pushes_down_scope_and_returns_exact_bounded_rows():
    table = pa.table({"pipeline": ["audit", "other"], "value": [1, 2]})
    result = _load_bounded_scoped_pyarrow_table(
        Table(table), pipeline_single="audit", columns=["value"]
    )
    assert result.to_pylist() == [{"value": 1}]


def test_real_delta_scan_retains_partition_and_row_predicates(tmp_path):
    from deltalake import DeltaTable, write_deltalake

    path = tmp_path / "quarantine"
    write_deltalake(
        path,
        pa.table(
            {
                "pipeline": ["audit", "other", "audit"],
                "error_code": ["selected", "selected", "ignored"],
                "value": [1, 2, 3],
            }
        ),
        partition_by=["pipeline"],
    )
    result = _load_bounded_scoped_pyarrow_table(
        DeltaTable(path),
        pipeline_single="audit",
        filters=[("error_code", "=", "selected")],
        columns=["value"],
    )
    assert result.to_pylist() == [{"value": 1}]


@pytest.mark.parametrize("kind", ["text", "utc", "naive"])
def test_time_window_precedes_row_budget_with_legacy_and_typed_dates(monkeypatch, kind):
    from bioetl.infrastructure.quarantine import filtered_reads as reads

    old = "2026-01-01T00:00:00Z"
    values = [old] * 10000 + ["2026-01-02T00:00:00Z", "2026-01-03T03:00:00+03:00", None]
    if kind != "text":
        values = [
            datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(UTC)
            if v
            else None
            for v in values
        ]
        if kind == "naive":
            values = [
                v.astimezone(UTC).replace(tzinfo=None) if v else None for v in values
            ]
    dates = pa.array(
        values,
        type=pa.string()
        if kind == "text"
        else pa.timestamp("us", tz="UTC" if kind == "utc" else None),
    )
    table = pa.table(
        {
            "pipeline": ["audit"] * len(values),
            "ingestion_ts": dates,
            "error_code": ["FILTERED_OUT_SILVER"] * len(values),
            "payload_hash": [str(i) for i in range(len(values))],
        }
    )
    monkeypatch.setattr(reads, "DeltaTable", lambda *a, **kw: Table(table))
    result = reads._load_filtered_rows(
        "synthetic",
        None,
        pipeline="audit",
        run_type=None,
        reason_code=None,
        field=None,
        run_id=None,
        payload_hash=None,
        from_ts="2026-01-02T00:00:00Z",
        to_ts="2026-01-03T00:00:00Z",
        include_payload=False,
        include_payload_preview=False,
    )
    assert [row["payload_hash"] for row in result] == ["10000", "10001"]
    with pytest.raises(RuntimeError, match="budget exceeded"):
        _load_bounded_scoped_pyarrow_table(Table(table), pipeline_single="audit")


def test_legacy_time_filter_preserves_projection_and_ignores_invalid_dates():
    table = pa.table(
        {
            "pipeline": ["audit"] * 4,
            "ingestion_ts": [
                "bad",
                None,
                "2026-01-02T03:00:00.123+03:00",
                "2026-01-01T00:00:00",
            ],
            "value": [0, 1, 2, 3],
        }
    )
    result = _load_bounded_scoped_pyarrow_table(
        Table(table),
        pipeline_single="audit",
        columns=["value"],
        from_ts="2026-01-02T00:00:00Z",
        to_ts="2026-01-03T00:00:00Z",
    )
    assert result.to_pylist() == [{"value": 2}]
