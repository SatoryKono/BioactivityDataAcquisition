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
"""Focused tests for postrun final metadata write helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.postrun._metadata_writes import (
    _build_gold_metadata_write_coro,
    _build_silver_metadata_write_coro,
    build_final_metadata_write_coroutines,
    get_run_statistics,
    resolve_report_path,
)
from bioetl.domain.config import PipelineConfig, RuntimeConfig, TableConfig
from bioetl.domain.types import RunType


pytestmark = pytest.mark.unit


def test_get_run_statistics_returns_empty_dict_without_hook() -> None:
    """Executors without a run-statistics hook should not break postrun writes."""
    executor = object()

    assert get_run_statistics(executor) == {}


@pytest.mark.asyncio
async def test_build_final_metadata_write_coroutines_builds_silver_only() -> None:
    """Silver metadata finalization should remain executable after extraction."""
    storage = MagicMock()
    storage.get_table_path = MagicMock(return_value="test-output/test_silver")
    # Silver finalization requires an initialized table (parity with gold gate).
    storage.is_table_initialized = MagicMock(return_value=True)

    metadata_coordinator = MagicMock()
    metadata_writer = MagicMock()
    metadata_writer.finalize_silver_metadata = AsyncMock(return_value="silver.yaml")
    metadata_writer.finalize_gold_metadata = AsyncMock(return_value="gold.yaml")

    config = PipelineConfig(
        pipeline_name="test_postrun_pipeline",
        provider="chembl",
        entity_type="activity",
        table=TableConfig(
            primary_keys=("activity_id",),
            silver_table="silver_table",
            gold_table="gold_table",
        ),
    )
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, skip_gold=True)
    context = MagicMock()
    context.started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    coroutines = build_final_metadata_write_coroutines(
        metadata_coordinator=metadata_coordinator,
        metadata_writer=metadata_writer,
        storage=storage,
        config=config,
        runtime=runtime,
        context=context,
        stats={"records_silver": 5, "source_batch_ids": ["batch-1"]},
        dq_reports=None,
        completed_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        resolve_delta_version=lambda _table_path, layer: 7,
    )

    assert len(coroutines) == 1
    await coroutines[0]

    metadata_coordinator.create_silver_metadata.assert_not_called()
    metadata_writer.finalize_silver_metadata.assert_awaited_once()
    metadata_writer.finalize_gold_metadata.assert_not_awaited()


@pytest.mark.asyncio
async def test_build_final_metadata_write_coroutines_skips_uninitialized_silver() -> (
    None
):
    """Silver finalize must no-op when the silver table is not initialized."""
    storage = MagicMock()
    storage.get_table_path = MagicMock(return_value="test-output/test_silver")
    storage.is_table_initialized = MagicMock(return_value=False)

    metadata_coordinator = MagicMock()
    metadata_writer = MagicMock()
    metadata_writer.finalize_silver_metadata = AsyncMock(return_value="silver.yaml")
    metadata_writer.finalize_gold_metadata = AsyncMock(return_value="gold.yaml")

    config = PipelineConfig(
        pipeline_name="test_postrun_pipeline",
        provider="chembl",
        entity_type="activity",
        table=TableConfig(
            primary_keys=("activity_id",),
            silver_table="silver_table",
            gold_table="gold_table",
        ),
    )
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, skip_gold=True)
    context = MagicMock()
    context.started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    coroutines = build_final_metadata_write_coroutines(
        metadata_coordinator=metadata_coordinator,
        metadata_writer=metadata_writer,
        storage=storage,
        config=config,
        runtime=runtime,
        context=context,
        stats={"records_silver": 5, "source_batch_ids": ["batch-1"]},
        dq_reports=None,
        completed_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        resolve_delta_version=lambda _table_path, layer: 7,
    )

    assert coroutines == []
    storage.is_table_initialized.assert_called_once_with("silver_table", layer="silver")
    storage.get_table_path.assert_not_called()
    metadata_writer.finalize_silver_metadata.assert_not_awaited()


@pytest.mark.parametrize(
    ("layer", "expected"),
    [
        ("silver", "reports/silver.json"),
        ("gold", "reports/gold.json"),
        ("bronze", None),
    ],
)
def test_resolve_report_path_is_bounded_to_supported_layers(
    layer: str,
    expected: str | None,
) -> None:
    """Only Silver and Gold report paths are exposed to metadata sidecars."""
    reports = SimpleNamespace(
        silver_report_path=Path("reports/silver.json"),
        gold_report_path=Path("reports/gold.json"),
    )

    assert resolve_report_path(reports, layer=layer) == expected
    assert resolve_report_path(None, layer=layer) is None


def test_resolve_report_path_normalizes_empty_paths_to_none() -> None:
    """Missing per-layer reports must not serialize a misleading path."""
    reports = SimpleNamespace(silver_report_path=None, gold_report_path=None)

    assert resolve_report_path(reports, layer="silver") is None
    assert resolve_report_path(reports, layer="gold") is None


def test_get_run_statistics_accepts_only_mapping_results() -> None:
    """Optional executor hooks are bounded to dictionary-shaped statistics."""
    stats = {"records_silver": 7}
    executor = SimpleNamespace(get_run_statistics=MagicMock(return_value=stats))
    assert get_run_statistics(executor) is stats

    executor.get_run_statistics.return_value = ["unexpected"]
    assert get_run_statistics(executor) == {}


@pytest.mark.parametrize(
    ("writer", "silver_table", "initialized"),
    [
        (None, "silver_table", True),
        (MagicMock(), None, True),
        (MagicMock(), "silver_table", False),
    ],
)
def test_silver_metadata_builder_enforces_all_presence_guards(
    writer: object | None,
    silver_table: str | None,
    initialized: bool,
) -> None:
    """Silver finalization is omitted unless writer, table, and storage exist."""
    storage = MagicMock()
    storage.is_table_initialized.return_value = initialized
    config = SimpleNamespace(
        table=SimpleNamespace(silver_table=silver_table),
        provider="chembl",
        entity_type="activity",
    )

    result = _build_silver_metadata_write_coro(
        metadata_coordinator=None,
        metadata_writer=writer,
        storage=storage,
        config=config,
        context=MagicMock(),
        stats={},
        dq_reports=None,
        completed_at=datetime(2026, 1, 1, tzinfo=UTC),
        resolve_delta_version=lambda _path, _layer: 1,
    )

    assert result is None


@pytest.mark.parametrize(
    ("writer", "skip_gold", "gold_table", "initialized"),
    [
        (None, False, "gold_table", True),
        (MagicMock(), True, "gold_table", True),
        (MagicMock(), False, None, True),
        (MagicMock(), False, "gold_table", False),
    ],
)
def test_gold_metadata_builder_enforces_all_presence_guards(
    writer: object | None,
    skip_gold: bool,
    gold_table: str | None,
    initialized: bool,
) -> None:
    """Gold finalization is omitted for every absent/disabled dependency."""
    storage = MagicMock()
    storage.is_table_initialized.return_value = initialized
    config = SimpleNamespace(
        table=SimpleNamespace(gold_table=gold_table),
        provider="chembl",
        entity_type="activity",
    )

    result = _build_gold_metadata_write_coro(
        metadata_coordinator=None,
        metadata_writer=writer,
        storage=storage,
        config=config,
        runtime=SimpleNamespace(skip_gold=skip_gold),
        stats={},
        dq_reports=None,
        completed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert result is None


@pytest.mark.asyncio
async def test_build_final_metadata_write_coroutines_builds_both_layers() -> None:
    """Initialized Silver and Gold tables produce complete, layer-specific calls."""
    storage = MagicMock()
    storage.is_table_initialized.return_value = True
    storage.get_table_path.side_effect = lambda table, *, layer: Path(
        f"tables/{layer}/{table}"
    )
    metadata_writer = MagicMock()
    metadata_writer.finalize_silver_metadata = AsyncMock(return_value="silver.yaml")
    metadata_writer.finalize_gold_metadata = AsyncMock(return_value="gold.yaml")
    config = PipelineConfig(
        pipeline_name="test_postrun_pipeline",
        provider="chembl",
        entity_type="activity",
        table=TableConfig(
            primary_keys=("activity_id",),
            silver_table="silver_table",
            gold_table="gold_table",
        ),
    )
    reports = SimpleNamespace(
        silver_report_path=Path("reports/silver.json"),
        gold_report_path=Path("reports/gold.json"),
    )
    completed_at = datetime(2026, 1, 2, tzinfo=UTC)

    coroutines = build_final_metadata_write_coroutines(
        metadata_coordinator=MagicMock(),
        metadata_writer=metadata_writer,
        storage=storage,
        config=config,
        runtime=RuntimeConfig(run_type=RunType.INCREMENTAL, skip_gold=False),
        context=MagicMock(),
        stats={"records_silver": 2},
        dq_reports=reports,
        completed_at=completed_at,
        resolve_delta_version=lambda path, layer: (
            9 if path.endswith("silver_table") and layer == "silver" else None
        ),
    )

    assert len(coroutines) == 2
    assert await coroutines[0] == "silver.yaml"
    assert await coroutines[1] == "gold.yaml"
    metadata_writer.finalize_silver_metadata.assert_awaited_once_with(
        "tables/silver/silver_table",
        dq_report_path="reports/silver.json",
        completed_at=completed_at,
        delta_version_after=9,
        provider="chembl",
        entity="activity",
    )
    metadata_writer.finalize_gold_metadata.assert_awaited_once_with(
        "tables/gold/gold_table",
        dq_report_path="reports/gold.json",
        completed_at=completed_at,
        provider="chembl",
        entity="activity",
    )
