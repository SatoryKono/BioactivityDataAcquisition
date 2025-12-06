"""Unit tests for pipeline collaborator classes."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.pipelines.error_policy_manager import ErrorPolicyManager
from bioetl.application.pipelines.hooks_impl import ContinueOnErrorPolicyImpl
from bioetl.application.pipelines.hooks_manager import HooksManager
from bioetl.application.pipelines.stage_runner import StageRunner
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, StageResult
from bioetl.domain.pipelines.contracts import PipelineHookABC
from bioetl.domain.providers import ProviderId


def _build_context() -> RunContext:
    return RunContext(entity_name="test", provider="chembl")


@pytest.mark.unit
def test_hooks_manager_notifies_hooks(mock_logger):
    hook = MagicMock(spec=PipelineHookABC)
    manager = HooksManager(
        logger=mock_logger,
        provider_id=ProviderId("chembl"),
        entity_name="entity",
        hooks=[hook],
    )
    context = _build_context()
    stage_result = StageResult(
        stage_name="extract",
        success=True,
        records_processed=0,
        chunks_processed=0,
        duration_sec=0.0,
        errors=[],
    )

    manager.notify_stage_start("extract", context)
    manager.notify_stage_end("extract", stage_result)

    hook.on_stage_start.assert_called_once_with("extract", context)
    hook.on_stage_end.assert_called_once_with("extract", stage_result)
    assert manager.get_stage_start("extract") is not None


@pytest.mark.unit
def test_error_policy_manager_retry_and_skip(mock_logger):
    hooks_manager = HooksManager(
        logger=mock_logger,
        provider_id=ProviderId("chembl"),
        entity_name="entity",
    )
    policy = ContinueOnErrorPolicyImpl(max_retries=1)
    manager = ErrorPolicyManager(
        error_policy=policy,
        hooks_manager=hooks_manager,
        logger=mock_logger,
        provider_id=ProviderId("chembl"),
        entity_name="entity",
        default_on_skip=lambda stage: f"skipped-{stage}",
    )
    context = _build_context()

    action = MagicMock(side_effect=[ValueError("temporary"), "ok"])
    assert manager.execute("extract", context, action) == "ok"
    assert action.call_count == 2
    assert manager.last_error is None

    failing_action = MagicMock(side_effect=RuntimeError("boom"))
    result = manager.execute("transform", context, failing_action)
    assert result == "skipped-transform"
    assert isinstance(manager.last_error, PipelineStageError)
    assert "boom" in manager.get_last_error_messages()[-1]


@pytest.mark.unit
def test_stage_runner_process_and_failure(mock_logger):
    hooks_manager = HooksManager(
        logger=mock_logger,
        provider_id=ProviderId("chembl"),
        entity_name="entity",
    )
    manager = ErrorPolicyManager(
        error_policy=ContinueOnErrorPolicyImpl(),
        hooks_manager=hooks_manager,
        logger=mock_logger,
        provider_id=ProviderId("chembl"),
        entity_name="entity",
        default_on_skip=lambda stage: f"skipped-{stage}",
    )
    runner = StageRunner(
        hooks_manager=hooks_manager,
        error_policy_manager=manager,
        entity_name="entity",
        provider_id=ProviderId("chembl"),
    )
    context = _build_context()
    raw_chunk = pd.DataFrame({"id": [1]})
    validated_chunks: list[pd.DataFrame] = []

    (
        transform_started,
        transform_chunks,
        transform_count,
        validate_started,
        validate_chunks,
        validate_count,
    ) = runner.process_chunk(
        raw_chunk,
        context,
        transform_started=False,
        transform_chunks=0,
        transform_count=0,
        validate_started=False,
        validate_chunks=0,
        validate_count=0,
        validated_chunks=validated_chunks,
        dry_run=False,
        transform_fn=lambda df: df.assign(transformed=True),
        apply_transformers=lambda df, _: df,
        validate_fn=lambda df: df,
    )

    assert transform_started and validate_started
    assert transform_chunks == 1 and validate_chunks == 1
    assert transform_count == 1 and validate_count == 1
    assert len(validated_chunks) == 1

    transform_stage = runner.make_stage_result(
        "transform", transform_count, chunks=transform_chunks
    )
    assert transform_stage.records_processed == 1
    assert transform_stage.duration_sec >= 0

    manager._last_error = PipelineStageError(  # type: ignore[attr-defined]
        provider="chembl",
        entity="entity",
        stage="validate",
        attempt=1,
        run_id=context.run_id,
        cause=RuntimeError("fail"),
    )
    failure = runner.handle_stage_failure("validate", [transform_stage], context)
    assert not failure.success
    assert failure.errors
