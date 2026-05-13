"""Focused unit tests for pipeline runner models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineNotFoundError,
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP


@pytest.mark.unit
class TestPipelineRunResultEnum:
    """Keep public status values stable for callers."""

    def test_enum_values_are_stable(self) -> None:
        assert PipelineRunResult.SUCCESS.value == "success"
        assert PipelineRunResult.SHUTDOWN.value == "shutdown"
        assert PipelineRunResult.FAILED.value == "failed"
        assert PipelineRunResult.DRY_RUN.value == "dry_run"


@pytest.mark.unit
class TestRunOptionsModel:
    """Direct tests for extended RunOptions fields."""

    def test_default_extended_fields_are_stable(self) -> None:
        options = RunOptions()

        assert options.multi_filter_ids is None
        assert options.fallback_column is None
        assert options.fallback_mapping is None
        assert options.ignore_yaml_filter is False
        assert options.skip_gold is False
        assert options.execution_context == "isolated"
        assert options.use_cached_bronze is False
        assert options.cached_bronze_path is None
        assert options.cached_bronze_date is None

    def test_extended_fields_accept_cli_overrides(self) -> None:
        options = RunOptions(
            filter_ids=("10.1000/a",),
            multi_filter_ids={"doi": ("10.1000/a",), "pmid": ("123",)},
            fallback_column="pmid",
            fallback_mapping={"10.1000/a": "123"},
            ignore_yaml_filter=True,
            skip_gold=True,
            execution_context="dependency",
            use_cached_bronze=True,
            cached_bronze_path="bronze/cache",
            cached_bronze_date="2026-03-19",
        )

        assert options.filter_ids == ("10.1000/a",)
        assert options.multi_filter_ids == {
            "doi": ("10.1000/a",),
            "pmid": ("123",),
        }
        assert options.fallback_column == "pmid"
        assert options.fallback_mapping == {"10.1000/a": "123"}
        assert options.ignore_yaml_filter is True
        assert options.skip_gold is True
        assert options.execution_context == "dependency"
        assert options.use_cached_bronze is True
        assert options.cached_bronze_path == "bronze/cache"
        assert options.cached_bronze_date == "2026-03-19"


@pytest.mark.unit
class TestRunResultModel:
    """Direct tests for result property behavior."""

    def test_default_timestamps_use_deterministic_sentinel(self) -> None:
        result = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="run-001",
            run_type="incremental",
        )

        assert result.started_at == MISSING_RUNTIME_TIMESTAMP
        assert result.completed_at == MISSING_RUNTIME_TIMESTAMP

    def test_success_rate_can_drop_to_zero(self) -> None:
        result = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="run-001",
            run_type="incremental",
            records_fetched=10,
            records_quarantined=10,
        )

        assert result.success_rate == pytest.approx(0.0)

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (PipelineRunResult.SUCCESS, True),
            (PipelineRunResult.DRY_RUN, True),
            (PipelineRunResult.SHUTDOWN, False),
            (PipelineRunResult.FAILED, False),
        ],
    )
    def test_is_success_depends_on_status(
        self,
        status: PipelineRunResult,
        expected: bool,
    ) -> None:
        result = RunResult(
            status=status,
            pipeline_name="chembl_activity",
            run_id="run-001",
            run_type="incremental",
        )

        assert result.is_success is expected

    def test_duration_seconds_uses_utc_datetimes(self) -> None:
        started_at = datetime(2026, 3, 19, 10, 0, 0, tzinfo=UTC)
        completed_at = datetime(2026, 3, 19, 10, 2, 30, tzinfo=UTC)
        result = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="run-001",
            run_type="incremental",
            started_at=started_at,
            completed_at=completed_at,
        )

        assert result.duration_seconds == pytest.approx(150.0)

    def test_manifest_id_is_preserved_when_present(self) -> None:
        result = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="run-001",
            run_type="incremental",
            manifest_id="manifest-001",
        )

        assert result.manifest_id == "manifest-001"


@pytest.mark.unit
class TestPipelineNotFoundErrorModel:
    """Direct tests for error payload preservation."""

    def test_error_keeps_pipeline_name_and_available_list(self) -> None:
        error = PipelineNotFoundError("missing_pipeline", ["a", "b"])

        assert error.pipeline_name == "missing_pipeline"
        assert error.available == ["a", "b"]
        assert "missing_pipeline" in str(error)
        assert "['a', 'b']" in str(error)
