"""Real Arrow scan regression coverage for quarantine read budgets."""

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
