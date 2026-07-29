# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integration contracts for postrun Silver compaction behavior."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from bioetl.application.core.postrun.compact_orchestrator import (
    CompactionResult,
    PostrunCompactService,
)
from bioetl.domain.config import PipelineConfig, TableConfig
from bioetl.domain.medallion import SilverWriteMode

pytestmark = pytest.mark.integration


@dataclass
class _RecordingStorage:
    deduplicate_result: int = 0
    deduplicate_error: BaseException | None = None
    optimize_error: BaseException | None = None
    deduplicate_calls: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)
    optimize_calls: list[str] = field(default_factory=list)

    async def deduplicate_silver(
        self,
        table_name: str,
        primary_keys: list[str],
    ) -> int:
        self.deduplicate_calls.append((table_name, tuple(primary_keys)))
        if self.deduplicate_error is not None:
            raise self.deduplicate_error
        return self.deduplicate_result

    async def optimize(self, *, table_name: str) -> None:
        self.optimize_calls.append(table_name)
        if self.optimize_error is not None:
            raise self.optimize_error


@dataclass
class _RecordingLogger:
    info_events: list[tuple[str, dict[str, object]]] = field(default_factory=list)
    warning_events: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    def info(self, event: str, **kwargs: object) -> None:
        self.info_events.append((event, kwargs))

    def warning(self, event: str, **kwargs: object) -> None:
        self.warning_events.append((event, kwargs))


def _build_config(
    *,
    silver_write_mode: SilverWriteMode = SilverWriteMode.APPEND,
    silver_table: str = "chembl_activity_silver",
    primary_keys: list[str] | None = None,
) -> PipelineConfig:
    return PipelineConfig(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
        table=TableConfig(
            primary_keys=primary_keys or ["activity_id"],
            silver_table=silver_table,
            silver_write_mode=silver_write_mode,
            gold_write_mode="scd2",
        ),
    )


@pytest.mark.asyncio
async def test_postrun_compact_service_runs_dedup_and_optimize_for_append_mode() -> (
    None
):
    storage = _RecordingStorage(deduplicate_result=7)
    logger = _RecordingLogger()
    service = PostrunCompactService(
        config=_build_config(),
        storage=storage,
        logger=logger,
        warning_allowlist=(RuntimeError,),
    )

    result = await service.run_if_needed()

    assert result == CompactionResult(status="success", duplicates_removed=7)
    assert storage.deduplicate_calls == [("chembl_activity_silver", ("activity_id",))]
    assert storage.optimize_calls == ["chembl_activity_silver"]
    assert [event for event, _payload in logger.info_events] == [
        "silver_compact_starting",
        "silver_compact_completed",
        "silver_optimize_starting",
        "silver_optimize_completed",
    ]
    assert logger.warning_events == []


@pytest.mark.asyncio
async def test_postrun_compact_service_keeps_success_when_optimize_is_allowlisted() -> (
    None
):
    storage = _RecordingStorage(
        deduplicate_result=3,
        optimize_error=RuntimeError("optimize busy"),
    )
    logger = _RecordingLogger()
    service = PostrunCompactService(
        config=_build_config(),
        storage=storage,
        logger=logger,
        warning_allowlist=(RuntimeError,),
    )

    result = await service.run_if_needed()

    assert result == CompactionResult(status="success", duplicates_removed=3)
    assert storage.deduplicate_calls == [("chembl_activity_silver", ("activity_id",))]
    assert storage.optimize_calls == ["chembl_activity_silver"]
    assert logger.warning_events == [
        ("silver_optimize_failed", {"error": "optimize busy"})
    ]


@pytest.mark.asyncio
async def test_postrun_compact_service_skips_delete_mode_without_storage_calls() -> (
    None
):
    storage = _RecordingStorage(deduplicate_result=99)
    logger = _RecordingLogger()
    service = PostrunCompactService(
        config=_build_config(silver_write_mode=SilverWriteMode.DELETE),
        storage=storage,
        logger=logger,
        warning_allowlist=(RuntimeError,),
    )

    result = await service.run_if_needed()

    assert result == CompactionResult(status="skipped")
    assert storage.deduplicate_calls == []
    assert storage.optimize_calls == []
    assert logger.info_events == []
    assert logger.warning_events == []
