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
"""Dedicated tests for DQReportGenerationMixin layer-specific flows."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.dq_report_service import (
    DQReportContext,
    DQReportService,
)
from bioetl.domain.ports import (
    BronzeDQConfigPort,
    GoldDQConfigPort,
    SilverDQConfigPort,
)


def _make_report(status_value: str = "PASS") -> MagicMock:
    report = MagicMock()
    report.summary.overall_status.value = status_value
    return report


def _make_context(**overrides: object) -> DQReportContext:
    payload: dict[str, object] = {
        "run_id": "run-001",
        "pipeline_name": "test_pipeline",
        "timestamp": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        "provider": "test_provider",
        "entity": "test_entity",
        "bronze_source_file": "bronze/source.jsonl",
        "bronze_batch_id": "batch-001",
        "bronze_records": [b'{"id":1}'],
        "silver_data": MagicMock(name="silver_df"),
        "silver_target_table": "silver.table",
        "silver_source_batch_ids": ["batch-001"],
        "silver_primary_keys": ["id"],
        "silver_input_count": 10,
        "silver_quarantined_count": 1,
        "gold_data": MagicMock(name="gold_df"),
        "gold_target_table": "gold.table",
    }
    payload.update(overrides)
    return DQReportContext(**payload)


@pytest.fixture
def service() -> DQReportService:
    return DQReportService(
        logger=MagicMock(),
        metrics=MagicMock(),
    )


@pytest.fixture
def silver_config() -> MagicMock:
    config = MagicMock(spec=SilverDQConfigPort)
    config.enabled = True
    config.output_path = None
    config.get_format_enum.return_value = MagicMock(value="json")
    return config


@pytest.fixture
def bronze_config() -> MagicMock:
    config = MagicMock(spec=BronzeDQConfigPort)
    config.enabled = True
    config.output_path = None
    config.get_format_enum.return_value = MagicMock(value="json")
    return config


@pytest.fixture
def gold_config() -> MagicMock:
    config = MagicMock(spec=GoldDQConfigPort)
    config.enabled = True
    config.output_path = None
    config.get_format_enum.return_value = MagicMock(value="json")
    return config


@pytest.mark.unit
def test_path_to_str_returns_string_or_none(service: DQReportService) -> None:
    report_path = Path("bronze/report.json")
    assert service._path_to_str(report_path) == str(report_path)
    assert service._path_to_str(None) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_generate_bronze_requires_enabled_and_config(
    service: DQReportService,
    bronze_config: MagicMock,
) -> None:
    service._generate_bronze_report = AsyncMock(return_value=Path("bronze.json"))  # type: ignore[method-assign]
    context = _make_context()

    disabled = await service._try_generate_bronze(context, bronze_config, enabled=False)
    assert disabled is None
    service._generate_bronze_report.assert_not_awaited()  # type: ignore[attr-defined]

    missing_config = await service._try_generate_bronze(context, None, enabled=True)
    assert missing_config is None
    service._generate_bronze_report.assert_not_awaited()  # type: ignore[attr-defined]

    generated = await service._try_generate_bronze(context, bronze_config, enabled=True)
    assert generated == Path("bronze.json")
    service._generate_bronze_report.assert_awaited_once_with(context, bronze_config)  # type: ignore[attr-defined]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_bronze_report_skips_when_analyzer_or_writer_missing(
    service: DQReportService,
    bronze_config: MagicMock,
) -> None:
    context = _make_context()

    result = await service._generate_bronze_report(context, bronze_config)

    assert result is None
    service._logger.warning.assert_called_with(
        "bronze_dq_report_skipped",
        reason="analyzer or writer not available",
        run_id=context.run_id,
    )
    service._metrics.increment_counter.assert_called_once_with(
        "bioetl_dq_report_skipped_total",
        1,
        {
            "pipeline": context.pipeline_name,
            "stage": "bronze",
            "reason": "analyzer_or_writer_unavailable",
        },
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_bronze_report_skips_when_data_missing(
    service: DQReportService,
    bronze_config: MagicMock,
) -> None:
    service._bronze_analyzer = MagicMock()
    service._report_writer = AsyncMock()
    context = _make_context(bronze_records=None, bronze_batch_id=None)

    result = await service._generate_bronze_report(context, bronze_config)

    assert result is None
    service._logger.warning.assert_called_with(
        "bronze_dq_report_skipped",
        reason="no bronze data available",
        run_id=context.run_id,
    )
    service._metrics.increment_counter.assert_called_once_with(
        "bioetl_dq_report_skipped_total",
        1,
        {
            "pipeline": context.pipeline_name,
            "stage": "bronze",
            "reason": "no_bronze_data",
        },
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_silver_report_emits_generated_metric(
    service: DQReportService,
    silver_config: MagicMock,
    tmp_path: Path,
) -> None:
    service._silver_analyzer = MagicMock()
    service._silver_analyzer.analyze.return_value = _make_report("PASS")
    service._report_writer = AsyncMock()
    expected_path = tmp_path / "silver-report.json"
    service._report_writer.write_silver_report.return_value = expected_path
    context = _make_context()

    result = await service._generate_silver_report(context, silver_config)

    assert result == expected_path
    service._metrics.increment_counter.assert_called_once_with(
        "bioetl_dq_report_generated_total",
        1,
        {
            "pipeline": context.pipeline_name,
            "stage": "silver",
        },
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_bronze_report_uses_context_output_path_precedence(
    service: DQReportService,
    bronze_config: MagicMock,
    tmp_path: Path,
) -> None:
    service._bronze_analyzer = MagicMock()
    service._bronze_analyzer.analyze.return_value = _make_report("WARNING")
    service._report_writer = AsyncMock()
    expected_path = tmp_path / "bronze-report.json"
    service._report_writer.write_bronze_report.return_value = expected_path
    bronze_config.output_path = str(tmp_path / "bronze-config-path.json")
    context_output = str(tmp_path / "bronze-context-path.json")
    context = _make_context(bronze_output_path=context_output)

    result = await service._generate_bronze_report(context, bronze_config)

    assert result == expected_path
    service._report_writer.write_bronze_report.assert_awaited_once()
    assert service._report_writer.write_bronze_report.await_args.kwargs[
        "output_path"
    ] == Path(context_output)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_bronze_report_uses_config_output_path_fallback(
    service: DQReportService,
    bronze_config: MagicMock,
    tmp_path: Path,
) -> None:
    service._bronze_analyzer = MagicMock()
    service._bronze_analyzer.analyze.return_value = _make_report()
    service._report_writer = AsyncMock()
    expected_path = tmp_path / "bronze-report.json"
    service._report_writer.write_bronze_report.return_value = expected_path
    bronze_config.output_path = str(tmp_path / "bronze-config-only-path.json")
    context = _make_context(bronze_output_path=None)

    result = await service._generate_bronze_report(context, bronze_config)

    assert result == expected_path
    assert service._report_writer.write_bronze_report.await_args.kwargs[
        "output_path"
    ] == Path(bronze_config.output_path)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_bronze_report_returns_none_when_analyzer_fails(
    service: DQReportService,
    bronze_config: MagicMock,
) -> None:
    service._bronze_analyzer = MagicMock()
    service._bronze_analyzer.analyze.side_effect = RuntimeError("bronze analyze failed")
    service._report_writer = AsyncMock()
    context = _make_context()

    result = await service._generate_bronze_report(context, bronze_config)

    assert result is None
    service._logger.error.assert_called_with(
        "bronze_dq_report_failed",
        run_id=context.run_id,
        error="bronze analyze failed",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_bronze_report_returns_none_when_writer_fails(
    service: DQReportService,
    bronze_config: MagicMock,
) -> None:
    service._bronze_analyzer = MagicMock()
    service._bronze_analyzer.analyze.return_value = _make_report()
    service._report_writer = AsyncMock()
    service._report_writer.write_bronze_report.side_effect = ValueError(
        "bronze write failed"
    )
    context = _make_context()

    result = await service._generate_bronze_report(context, bronze_config)

    assert result is None
    service._logger.error.assert_called_with(
        "bronze_dq_report_failed",
        run_id=context.run_id,
        error="bronze write failed",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_generate_silver_requires_enabled_and_config(
    service: DQReportService,
    silver_config: MagicMock,
) -> None:
    service._generate_silver_report = AsyncMock(return_value=Path("silver.json"))  # type: ignore[method-assign]
    context = _make_context()

    disabled = await service._try_generate_silver(context, silver_config, enabled=False)
    assert disabled is None
    service._generate_silver_report.assert_not_awaited()  # type: ignore[attr-defined]

    missing_config = await service._try_generate_silver(context, None, enabled=True)
    assert missing_config is None
    service._generate_silver_report.assert_not_awaited()  # type: ignore[attr-defined]

    generated = await service._try_generate_silver(context, silver_config, enabled=True)
    assert generated == Path("silver.json")
    service._generate_silver_report.assert_awaited_once_with(context, silver_config)  # type: ignore[attr-defined]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_generate_gold_requires_enabled_and_config(
    service: DQReportService,
    gold_config: MagicMock,
) -> None:
    service._generate_gold_report = AsyncMock(return_value=Path("gold.json"))  # type: ignore[method-assign]
    context = _make_context()

    disabled = await service._try_generate_gold(context, gold_config, enabled=False)
    assert disabled is None
    service._generate_gold_report.assert_not_awaited()  # type: ignore[attr-defined]

    missing_config = await service._try_generate_gold(context, None, enabled=True)
    assert missing_config is None
    service._generate_gold_report.assert_not_awaited()  # type: ignore[attr-defined]

    generated = await service._try_generate_gold(context, gold_config, enabled=True)
    assert generated == Path("gold.json")
    service._generate_gold_report.assert_awaited_once_with(context, gold_config)  # type: ignore[attr-defined]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_silver_report_skips_when_analyzer_or_writer_missing(
    service: DQReportService,
    silver_config: MagicMock,
) -> None:
    context = _make_context()

    result = await service._generate_silver_report(context, silver_config)

    assert result is None
    service._logger.warning.assert_called_with(
        "silver_dq_report_skipped",
        reason="analyzer or writer not available",
        run_id=context.run_id,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_silver_report_skips_when_data_missing(
    service: DQReportService,
    silver_config: MagicMock,
) -> None:
    service._silver_analyzer = MagicMock()
    service._report_writer = AsyncMock()
    context = _make_context(silver_data=None, silver_target_table=None)

    result = await service._generate_silver_report(context, silver_config)

    assert result is None
    service._logger.warning.assert_called_with(
        "silver_dq_report_skipped",
        reason="no silver data available",
        run_id=context.run_id,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_silver_report_uses_context_output_path_precedence(
    service: DQReportService,
    silver_config: MagicMock,
    tmp_path: Path,
) -> None:
    service._silver_analyzer = MagicMock()
    service._silver_analyzer.analyze.return_value = _make_report("WARNING")
    service._report_writer = AsyncMock()
    expected_path = tmp_path / "silver-report.json"
    service._report_writer.write_silver_report.return_value = expected_path
    silver_config.output_path = str(tmp_path / "config-path.json")
    context_output = str(tmp_path / "context-path.json")
    context = _make_context(silver_output_path=context_output)

    result = await service._generate_silver_report(context, silver_config)

    assert result == expected_path
    service._report_writer.write_silver_report.assert_awaited_once()
    assert service._report_writer.write_silver_report.await_args.kwargs[
        "output_path"
    ] == Path(context_output)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_silver_report_uses_config_output_path_fallback(
    service: DQReportService,
    silver_config: MagicMock,
    tmp_path: Path,
) -> None:
    service._silver_analyzer = MagicMock()
    service._silver_analyzer.analyze.return_value = _make_report()
    service._report_writer = AsyncMock()
    expected_path = tmp_path / "silver-report.json"
    service._report_writer.write_silver_report.return_value = expected_path
    silver_config.output_path = str(tmp_path / "config-only-path.json")
    context = _make_context(silver_output_path=None)

    result = await service._generate_silver_report(context, silver_config)

    assert result == expected_path
    assert service._report_writer.write_silver_report.await_args.kwargs[
        "output_path"
    ] == Path(silver_config.output_path)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_silver_report_returns_none_when_analyzer_fails(
    service: DQReportService,
    silver_config: MagicMock,
) -> None:
    service._silver_analyzer = MagicMock()
    service._silver_analyzer.analyze.side_effect = RuntimeError("silver analyze failed")
    service._report_writer = AsyncMock()
    context = _make_context()

    result = await service._generate_silver_report(context, silver_config)

    assert result is None
    service._logger.error.assert_called_with(
        "silver_dq_report_failed",
        run_id=context.run_id,
        error="silver analyze failed",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_silver_report_returns_none_when_writer_fails(
    service: DQReportService,
    silver_config: MagicMock,
) -> None:
    service._silver_analyzer = MagicMock()
    service._silver_analyzer.analyze.return_value = _make_report()
    service._report_writer = AsyncMock()
    service._report_writer.write_silver_report.side_effect = ValueError(
        "silver write failed"
    )
    context = _make_context()

    result = await service._generate_silver_report(context, silver_config)

    assert result is None
    service._logger.error.assert_called_with(
        "silver_dq_report_failed",
        run_id=context.run_id,
        error="silver write failed",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_gold_report_skips_when_analyzer_or_writer_missing(
    service: DQReportService,
    gold_config: MagicMock,
) -> None:
    context = _make_context()

    result = await service._generate_gold_report(context, gold_config)

    assert result is None
    service._logger.warning.assert_called_with(
        "gold_dq_report_skipped",
        reason="analyzer or writer not available",
        run_id=context.run_id,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_gold_report_skips_when_data_missing(
    service: DQReportService,
    gold_config: MagicMock,
) -> None:
    service._gold_analyzer = MagicMock()
    service._report_writer = AsyncMock()
    context = _make_context(gold_data=None, gold_target_table=None)

    result = await service._generate_gold_report(context, gold_config)

    assert result is None
    service._logger.warning.assert_called_with(
        "gold_dq_report_skipped",
        reason="no gold data available",
        run_id=context.run_id,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_gold_report_uses_context_output_path_precedence(
    service: DQReportService,
    gold_config: MagicMock,
    tmp_path: Path,
) -> None:
    service._gold_analyzer = MagicMock()
    service._gold_analyzer.analyze.return_value = _make_report()
    service._report_writer = AsyncMock()
    expected_path = tmp_path / "gold-report.json"
    service._report_writer.write_gold_report.return_value = expected_path
    gold_config.output_path = str(tmp_path / "gold-config-path.json")
    context_output = str(tmp_path / "gold-context-path.json")
    context = _make_context(gold_output_path=context_output)

    result = await service._generate_gold_report(context, gold_config)

    assert result == expected_path
    assert service._report_writer.write_gold_report.await_args.kwargs[
        "output_path"
    ] == Path(context_output)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_gold_report_uses_config_output_path_fallback(
    service: DQReportService,
    gold_config: MagicMock,
    tmp_path: Path,
) -> None:
    service._gold_analyzer = MagicMock()
    service._gold_analyzer.analyze.return_value = _make_report()
    service._report_writer = AsyncMock()
    expected_path = tmp_path / "gold-report.json"
    service._report_writer.write_gold_report.return_value = expected_path
    gold_config.output_path = str(tmp_path / "gold-config-only-path.json")
    context = _make_context(gold_output_path=None)

    result = await service._generate_gold_report(context, gold_config)

    assert result == expected_path
    assert service._report_writer.write_gold_report.await_args.kwargs[
        "output_path"
    ] == Path(gold_config.output_path)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_gold_report_returns_none_when_analyzer_fails(
    service: DQReportService,
    gold_config: MagicMock,
) -> None:
    service._gold_analyzer = MagicMock()
    service._gold_analyzer.analyze.side_effect = RuntimeError("gold analyze failed")
    service._report_writer = AsyncMock()
    context = _make_context()

    result = await service._generate_gold_report(context, gold_config)

    assert result is None
    service._logger.error.assert_called_with(
        "gold_dq_report_failed",
        run_id=context.run_id,
        error="gold analyze failed",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_gold_report_returns_none_when_writer_fails(
    service: DQReportService,
    gold_config: MagicMock,
) -> None:
    service._gold_analyzer = MagicMock()
    service._gold_analyzer.analyze.return_value = _make_report()
    service._report_writer = AsyncMock()
    service._report_writer.write_gold_report.side_effect = ValueError(
        "gold write failed"
    )
    context = _make_context()

    result = await service._generate_gold_report(context, gold_config)

    assert result is None
    service._logger.error.assert_called_with(
        "gold_dq_report_failed",
        run_id=context.run_id,
        error="gold write failed",
    )
