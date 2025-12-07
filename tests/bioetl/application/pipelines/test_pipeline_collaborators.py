"""Unit tests for pipeline collaborator classes."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.pipelines.hooks_impl import ContinueOnErrorPolicyImpl
from bioetl.application.pipelines.stage_runtime_manager import StageRuntimeManager
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, StageResult
from bioetl.domain.pipelines.contracts import PipelineHookABC
from bioetl.domain.providers import ProviderId


def _build_context() -> RunContext:
    return RunContext(entity_name="test", provider="chembl")


@pytest.mark.unit
def test_stage_runtime_notifies_hooks(mock_logger):
    hook = MagicMock(spec=PipelineHookABC)
    manager = StageRuntimeManager(
        logger=mock_logger,
        provider_id=ProviderId("chembl"),
        entity_name="entity",
        hooks=[hook],
        error_policy=ContinueOnErrorPolicyImpl(),
        default_on_skip=lambda _: None,
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
def test_stage_runtime_retry_and_skip(mock_logger):
    policy = ContinueOnErrorPolicyImpl(max_retries=1)
    manager = StageRuntimeManager(
        logger=mock_logger,
        provider_id=ProviderId("chembl"),
        entity_name="entity",
        error_policy=policy,
        default_on_skip=lambda stage: f"skipped-{stage}",
    )
    context = _build_context()

    action = MagicMock(side_effect=[ValueError("temporary"), "ok"])
    assert manager.execute_stage("extract", context, action) == "ok"
    assert action.call_count == 2
    assert manager.last_error is None

    failing_action = MagicMock(side_effect=RuntimeError("boom"))
    result = manager.execute_stage("transform", context, failing_action)
    assert result == "skipped-transform"
    assert isinstance(manager.last_error, PipelineStageError)
    assert "boom" in manager.get_last_error_messages()[-1]


@pytest.mark.unit
def test_stage_runtime_process_and_failure(mock_logger):
    manager = StageRuntimeManager(
        logger=mock_logger,
        provider_id=ProviderId("chembl"),
        entity_name="entity",
        error_policy=ContinueOnErrorPolicyImpl(),
        default_on_skip=lambda stage: f"skipped-{stage}",
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
    ) = manager.process_chunk(
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

    transform_stage = manager.make_stage_result(
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
    failure = manager.handle_stage_failure("validate", [transform_stage], context)
    assert not failure.success
    assert failure.errors


@pytest.mark.unit
def test_stage_runtime_handles_skip_and_counts(mock_logger):
    manager = StageRuntimeManager(
        logger=mock_logger,
        provider_id=ProviderId("chembl"),
        entity_name="entity",
        error_policy=ContinueOnErrorPolicyImpl(),
        default_on_skip=lambda stage: pd.DataFrame(),
    )
    context = _build_context()
    validated_chunks: list[pd.DataFrame] = []

    (
        transform_started,
        transform_chunks,
        transform_count,
        validate_started,
        validate_chunks,
        validate_count,
    ) = manager.process_chunk(
        pd.DataFrame({"id": [1]}),
        context,
        transform_started=False,
        transform_chunks=0,
        transform_count=0,
        validate_started=False,
        validate_chunks=0,
        validate_count=0,
        validated_chunks=validated_chunks,
        dry_run=False,
        transform_fn=lambda _: (_ for _ in ()).throw(ValueError("fail")),
        apply_transformers=lambda df, _: df,
        validate_fn=lambda df: df,
    )

    assert transform_started and validate_started
    assert transform_chunks == 1 and validate_chunks == 1
    assert transform_count == 0 and validate_count == 0
    assert len(validated_chunks) == 1 and validated_chunks[0].empty


@pytest.mark.unit
def test_stage_runtime_raises_on_missing_result(mock_logger):
    manager = StageRuntimeManager(
        logger=mock_logger,
        provider_id=ProviderId("chembl"),
        entity_name="entity",
        error_policy=ContinueOnErrorPolicyImpl(),
        default_on_skip=lambda stage: pd.DataFrame(),
    )
    context = _build_context()

    manager.execute_stage = MagicMock(return_value=None)  # type: ignore[method-assign]

    with pytest.raises(PipelineStageError):
        manager.process_chunk(
            pd.DataFrame({"id": [1]}),
            context,
            transform_started=False,
            transform_chunks=0,
            transform_count=0,
            validate_started=False,
            validate_chunks=0,
            validate_count=0,
            validated_chunks=[],
            dry_run=False,
            transform_fn=lambda df: df,
            apply_transformers=lambda df, _: df,
            validate_fn=lambda df: df,
        )

    manager.execute_stage.assert_called_once()
