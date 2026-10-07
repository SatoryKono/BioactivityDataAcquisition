"""P02 F2: stage result values cannot mutate stored run evidence."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from bioetl.domain.aggregates import PipelineRun, StageResult
from bioetl.domain.aggregates.pipeline_run_stage_result import StageStatus
from bioetl.domain.normalization.json import to_jsonable
from bioetl.domain.types import RunID, RunType

pytestmark = pytest.mark.unit
NOW = datetime(2026, 10, 7, tzinfo=UTC)


def test_json_result_is_snapshotted_immediately_and_in_terminal_run() -> None:
    result = {"nested": {"items": [1]}}
    run = PipelineRun(RunID(UUID(int=1)), RunType.INCREMENTAL)
    run.start(NOW)
    run.record_stage_success(
        "extract",
        result=result,
        records_processed=7,
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
    )
    result["nested"]["items"].append(2)
    stage = run.stages[0]
    assert stage.result == {"nested": {"items": [1]}}
    with pytest.raises(TypeError):
        stage.result["nested"]["items"][0] = 3  # type: ignore[index]
    run.complete(NOW + timedelta(seconds=2))
    assert run.successful_stages[0].result == {"nested": {"items": [1]}}
    assert run.total_records_processed == 7
    assert to_jsonable(stage)["result"] == {"nested": {"items": [1]}}


@pytest.mark.parametrize(
    "value", [None, True, 1, 1.5, "text", [1, {"x": 2}], (1, [2]), {1, 2}]
)
def test_supported_result_values_keep_equality(value: object) -> None:
    stage = StageResult("extract", StageStatus.SUCCESS, NOW, NOW, result=value)
    assert stage.result == value


def test_complex_copyable_result_remains_value_preserving_and_detached() -> None:
    @dataclass
    class ResultValue:
        metrics: dict[str, list[int]]
        lineage: str

    original = ResultValue({"rows": [1]}, "source")
    stage = StageResult("extract", StageStatus.SUCCESS, NOW, NOW, result=original)
    original.metrics["rows"].append(2)
    obtained = stage.result
    assert isinstance(obtained, ResultValue)
    assert obtained == ResultValue({"rows": [1]}, "source")
    obtained.metrics["rows"].append(3)
    assert stage.result == ResultValue({"rows": [1]}, "source")

    nested = StageResult(
        "extract", StageStatus.SUCCESS, NOW, NOW, result={"value": original}
    )
    restored = deepcopy(nested)
    accessor = restored.result
    accessor["value"].metrics["rows"].append(4)  # type: ignore[index]
    assert restored.result == {"value": ResultValue({"rows": [1, 2]}, "source")}


def test_success_copy_also_snapshots_result() -> None:
    pending = StageResult("extract", StageStatus.RUNNING, NOW)
    payload = {"rows": [1]}
    success = pending.with_success(NOW, payload, records_processed=1)
    payload["rows"].append(2)
    assert success.result == {"rows": [1]}
