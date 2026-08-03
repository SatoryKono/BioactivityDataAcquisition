# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for storage-backed workflow row reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from bioetl.domain.ports.workflow_row_reconciliation import (
    RowReconciliationConfig,
    RowReconciliationExecutionError,
    RowReconciliationMissingColumnError,
    RowReconciliationTypePolicyError,
)
from bioetl.infrastructure.storage.workflow_row_reconciliation import (
    StorageRowReconciliationAdapter,
)

pytestmark = pytest.mark.unit


@dataclass
class _Reader:
    rows_by_table: dict[str, list[dict[str, object]]]
    calls: list[tuple[str, str, list[str] | None, bool | None]] = field(
        default_factory=list
    )

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[dict[str, object]]:
        self.calls.append(("silver", table_name, columns, None))
        return _project(self.rows_by_table[table_name], columns)

    async def read_gold(
        self,
        table_name: str,
        columns: list[str] | None = None,
        current_only: bool = True,
    ) -> list[dict[str, object]]:
        self.calls.append(("gold", table_name, columns, current_only))
        return _project(self.rows_by_table[table_name], columns)


@dataclass
class _Logger:
    messages: list[tuple[str, str, dict[str, object]]] = field(default_factory=list)

    def info(self, message: str, **context: object) -> None:
        self.messages.append(("info", message, dict(context)))


@dataclass
class _Metrics:
    calls: list[tuple[str, int, dict[str, str]]] = field(default_factory=list)

    def increment_counter(
        self,
        name: str,
        value: int = 1,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.calls.append((name, value, dict(labels or {})))


def _project(
    rows: list[dict[str, object]],
    columns: list[str] | None,
) -> list[dict[str, object]]:
    if columns is None:
        return [dict(row) for row in rows]
    return [
        {column: row[column] for column in columns if column in row} for row in rows
    ]


def _silver_config(**overrides: object) -> RowReconciliationConfig:
    payload: dict[str, object] = {
        "layer": "silver",
        "left_table": "left",
        "right_table": "right",
        "left_columns": ("id",),
        "right_columns": ("key",),
        "left_primary_keys": ("row_id",),
        "nulls_equal": False,
    }
    payload.update(overrides)
    return RowReconciliationConfig(**payload)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_reconcile_rows_preserves_left_order_duplicates_and_no_right_multiply() -> (
    None
):
    reader = _Reader(
        {
            "left": [
                {"row_id": "r1", "id": 1, "payload": "a"},
                {"row_id": "r2", "id": 1, "payload": "a-duplicate"},
                {"row_id": "r3", "id": 2, "payload": "b"},
                {"row_id": "r4", "id": None, "payload": "null-left"},
            ],
            "right": [
                {"key": 1},
                {"key": 1},
                {"key": 3},
                {"key": None},
            ],
        }
    )
    metrics = _Metrics()
    adapter = StorageRowReconciliationAdapter(
        silver_reader=reader,
        gold_reader=reader,
        logger=_Logger(),
        metrics=metrics,
    )

    result = await adapter.reconcile_rows(_silver_config())

    assert [row["row_id"] for row in result.rows] == ["r1", "r2"]
    assert result.input_left_rows == 4
    assert result.input_right_rows == 4
    assert result.kept_rows == 2
    assert result.excluded_rows == 2
    assert result.null_key_rows_left == 1
    assert result.null_key_rows_right == 1
    assert result.distinct_right_keys == 2
    assert result.mutated is False
    assert reader.calls == [
        ("silver", "left", None, None),
        ("silver", "right", None, None),
    ]
    assert metrics.calls[0][2] == {"layer": "silver"}


@pytest.mark.asyncio
async def test_reconcile_rows_can_match_null_keys_when_enabled() -> None:
    reader = _Reader(
        {
            "left": [{"row_id": "r1", "id": None}, {"row_id": "r2", "id": 5}],
            "right": [{"key": None}],
        }
    )
    adapter = StorageRowReconciliationAdapter(
        silver_reader=reader,
        gold_reader=reader,
        logger=_Logger(),
    )

    result = await adapter.reconcile_rows(_silver_config(nulls_equal=True))

    assert [row["row_id"] for row in result.rows] == ["r1"]
    assert result.null_key_rows_left == 1
    assert result.null_key_rows_right == 1
    assert result.distinct_right_keys == 1


@pytest.mark.asyncio
async def test_reconcile_rows_strict_type_policy_rejects_implicit_coercion() -> None:
    reader = _Reader(
        {
            "left": [{"row_id": "r1", "id": 1}],
            "right": [{"key": "1"}],
        }
    )
    adapter = StorageRowReconciliationAdapter(
        silver_reader=reader,
        gold_reader=reader,
        logger=_Logger(),
    )

    with pytest.raises(RowReconciliationTypePolicyError, match="strict type_policy"):
        await adapter.reconcile_rows(_silver_config())


@pytest.mark.asyncio
async def test_reconcile_rows_reports_missing_columns_explicitly() -> None:
    reader = _Reader(
        {
            "left": [{"row_id": "r1", "id": 1}],
            "right": [{"other_key": 1}],
        }
    )
    adapter = StorageRowReconciliationAdapter(
        silver_reader=reader,
        gold_reader=reader,
        logger=_Logger(),
    )

    with pytest.raises(RowReconciliationMissingColumnError, match="right key columns"):
        await adapter.reconcile_rows(_silver_config(right_columns=("key",)))


@pytest.mark.asyncio
async def test_reconcile_rows_uses_gold_reader_for_gold_layer() -> None:
    reader = _Reader(
        {
            "left_gold": [{"row_id": "r1", "id": "A"}],
            "right_gold": [{"key": "A"}],
        }
    )
    adapter = StorageRowReconciliationAdapter(
        silver_reader=reader,
        gold_reader=reader,
        logger=_Logger(),
    )

    result = await adapter.reconcile_rows(
        _silver_config(layer="gold", left_table="left_gold", right_table="right_gold")
    )

    assert result.kept_rows == 1
    assert reader.calls == [
        ("gold", "left_gold", None, True),
        ("gold", "right_gold", None, True),
    ]


@pytest.mark.asyncio
async def test_reconcile_rows_wraps_reader_lookup_failures_as_execution_errors() -> (
    None
):
    reader = _Reader({"right": [{"key": 1}]})
    adapter = StorageRowReconciliationAdapter(
        silver_reader=reader,
        gold_reader=reader,
        logger=_Logger(),
    )

    with pytest.raises(RowReconciliationExecutionError, match="left"):
        await adapter.reconcile_rows(_silver_config())
