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
"""Unit tests for workflow foreign-key reconciliation storage adapter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pytest
from deltalake.exceptions import CommitFailedError

from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.storage import gold_writer
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    SilverForeignKeyReconciliationAdapter,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine import (
    expire_gold_orphan_rows,
)

pytestmark = pytest.mark.unit


@dataclass
class _GoldReader:
    rows_by_table: dict[str, list[dict[str, object]]]

    async def read_gold(
        self,
        table_name: str,
        columns: list[str] | None = None,
        current_only: bool = True,
    ) -> list[dict[str, object]]:
        del current_only
        if table_name not in self.rows_by_table:
            raise FileNotFoundError(table_name)
        rows = self.rows_by_table[table_name]
        if columns is None:
            return [dict(row) for row in rows]
        return [
            {column: row[column] for column in columns if column in row} for row in rows
        ]


@dataclass
class _SilverWriter:
    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[dict[str, object]]:
        del table_name, columns
        raise AssertionError("Silver should not be read for Gold reconciliation")


@dataclass
class _Logger:
    events: list[tuple[str, str, dict[str, object]]] = field(default_factory=list)

    def info(self, message: str, **context: object) -> None:
        self.events.append(("info", message, dict(context)))

    def warning(self, message: str, **context: object) -> None:
        self.events.append(("warning", message, dict(context)))


@dataclass
class _Quarantine:
    writes: list[dict[str, object]] = field(default_factory=list)

    async def write_many(self, records: list[dict[str, object]]) -> None:
        self.writes.extend(records)


@dataclass
class _GoldMutationWriter:
    execute_errors: list[BaseException] = field(default_factory=list)
    merge_attempts: int = 0

    def _resolve_table_path(self, table_name: str) -> str:
        return f"/tmp/{table_name.replace('.', '/')}"

    async def _run_in_executor(
        self,
        func: Callable[..., object],
        *args: object,
    ) -> object:
        return func(*args)


@dataclass
class _MutationHost:
    gold_writer: _GoldMutationWriter
    silver_writer: object = field(default_factory=object)
    quarantine: object | None = None
    quarantine_pipeline_name: str | None = None
    logger: _Logger = field(default_factory=_Logger)


class _FakeAsyncio:
    def __init__(self) -> None:
        self.sleep_calls: list[float] = []

    async def sleep(self, delay: float) -> None:
        self.sleep_calls.append(delay)


class _FakeMergeBuilder:
    def __init__(self, writer: _GoldMutationWriter) -> None:
        self._writer = writer

    def when_matched_update(self, **_: object) -> _FakeMergeBuilder:
        return self

    def execute(self) -> dict[str, int]:
        self._writer.merge_attempts += 1
        if self._writer.execute_errors:
            raise self._writer.execute_errors.pop(0)
        return {"num_updated_rows": 1}


class _FakeDeltaTable:
    def __init__(self, writer: _GoldMutationWriter) -> None:
        self._writer = writer

    def merge(self, **_: object) -> _FakeMergeBuilder:
        return _FakeMergeBuilder(self._writer)


class _FakeGoldModule:
    GOLD_WRITE_RETRY_ERRORS = (CommitFailedError,)

    def __init__(self, writer: _GoldMutationWriter) -> None:
        self.writer = writer
        self.asyncio = _FakeAsyncio()
        self.table_paths: list[str] = []

    def DeltaTable(self, table_path: str) -> _FakeDeltaTable:
        self.table_paths.append(table_path)
        return _FakeDeltaTable(self.writer)


@pytest.mark.asyncio
async def test_gold_dry_run_does_not_mutate_or_quarantine() -> None:
    quarantine = _Quarantine()
    adapter = SilverForeignKeyReconciliationAdapter(
        silver_writer=_SilverWriter(),  # type: ignore[arg-type]
        gold_writer=_GoldReader(
            {
                "chembl.assay": [
                    {
                        "assay_id": "CHEMBL_A1",
                        "target_id": "CHEMBL_T999",
                        "_is_current": True,
                    }
                ],
                "chembl.target": [],
            }
        ),
        logger=_Logger(),  # type: ignore[arg-type]
        quarantine=quarantine,  # type: ignore[arg-type]
    )

    result = await adapter.reconcile_foreign_keys(
        ForeignKeyReconciliationRequest(
            source_layer="gold",
            reference_layer="gold",
            mutation_layer="gold",
            source_table="chembl.assay",
            reference_table="chembl.target",
            source_key="target_id",
            reference_key="target_id",
            primary_keys=("assay_id",),
            dry_run=True,
        )
    )

    assert result.dry_run is True
    assert result.would_mutate is True
    assert result.mutated is False
    assert result.orphan_rows_deleted == 1
    assert quarantine.writes == []


def test_gold_writer_retries_delta_commit_failures() -> None:
    assert CommitFailedError in gold_writer.GOLD_WRITE_RETRY_ERRORS


@pytest.mark.asyncio
async def test_gold_source_table_missing_skips_reconciliation() -> None:
    logger = _Logger()
    adapter = SilverForeignKeyReconciliationAdapter(
        silver_writer=_SilverWriter(),  # type: ignore[arg-type]
        gold_writer=_GoldReader(
            {
                "chembl.target": [
                    {
                        "target_id": "CHEMBL_T1",
                        "_is_current": True,
                    }
                ]
            }
        ),
        logger=logger,  # type: ignore[arg-type]
    )

    result = await adapter.reconcile_foreign_keys(
        ForeignKeyReconciliationRequest(
            source_layer="gold",
            reference_layer="gold",
            mutation_layer="gold",
            source_table="chembl.assay",
            reference_table="chembl.target",
            source_key="target_id",
            reference_key="target_id",
            primary_keys=("assay_id",),
        )
    )

    assert result.mutation_mode == "missing_source"
    assert result.scanned_rows == 0
    assert result.retained_rows == 0
    assert result.orphan_rows_deleted == 0
    assert result.mutated is False
    assert result.would_mutate is False
    assert any(
        level == "warning"
        and message
        == "workflow foreign-key reconciliation skipped missing source table"
        and context["source_layer"] == "gold"
        and context["source_table"] == "chembl.assay"
        for level, message, context in logger.events
    )


@pytest.mark.asyncio
async def test_gold_expiry_retries_commit_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writer = _GoldMutationWriter(execute_errors=[CommitFailedError("conflict")])
    fake_module = _FakeGoldModule(writer)
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine.load_gold_writer_module",
        lambda: fake_module,
    )

    await expire_gold_orphan_rows(
        _MutationHost(gold_writer=writer),  # type: ignore[arg-type]
        ForeignKeyReconciliationRequest(
            source_layer="gold",
            reference_layer="gold",
            mutation_layer="gold",
            source_table="chembl.assay",
            reference_table="chembl.target",
            source_key="target_id",
            reference_key="target_id",
            primary_keys=("assay_id",),
        ),
        orphan_rows=[
            {
                "assay_id": "CHEMBL_A1",
                "target_id": "CHEMBL_T999",
                "_is_current": True,
                "_valid_to": None,
            }
        ],
    )

    assert writer.merge_attempts == 2
    # One schema inspection open + two merge retry attempts.
    assert fake_module.table_paths == [
        "/tmp/chembl/assay",
        "/tmp/chembl/assay",
        "/tmp/chembl/assay",
    ]
    assert fake_module.asyncio.sleep_calls == [0.55]


@pytest.mark.asyncio
async def test_gold_reference_table_missing_fails_fast() -> None:
    adapter = SilverForeignKeyReconciliationAdapter(
        silver_writer=_SilverWriter(),  # type: ignore[arg-type]
        gold_writer=_GoldReader(
            {
                "chembl.assay": [
                    {
                        "assay_id": "CHEMBL_A1",
                        "target_id": "CHEMBL_T999",
                        "_is_current": True,
                    }
                ],
            }
        ),
        logger=_Logger(),  # type: ignore[arg-type]
    )

    with pytest.raises(
        ValueError,
        match=r"Gold foreign-key reconciliation reference table not found: chembl\.target",
    ) as exc_info:
        await adapter.reconcile_foreign_keys(
            ForeignKeyReconciliationRequest(
                source_layer="gold",
                reference_layer="gold",
                mutation_layer="gold",
                source_table="chembl.assay",
                reference_table="chembl.target",
                source_key="target_id",
                reference_key="target_id",
                primary_keys=("assay_id",),
            )
        )

    assert isinstance(exc_info.value.__cause__, FileNotFoundError)
