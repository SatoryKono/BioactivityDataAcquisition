import pytest

from bioetl.domain.errors import PipelineStageError


def test_pipeline_stage_error_properties() -> None:
    cause = RuntimeError("boom")

    error = PipelineStageError(
        provider="chembl",
        entity="activity",
        stage="extract",
        attempt=2,
        run_id="run-123",
        cause=cause,
    )

    assert error.provider == "chembl"
    assert error.entity == "activity"
    assert error.stage == "extract"
    assert error.attempt == 2
    assert error.run_id == "run-123"
    assert error.cause is cause


def test_pipeline_stage_error_str_contains_context() -> None:
    error = PipelineStageError(
        provider="chembl",
        entity="target",
        stage="validate",
        attempt=1,
        run_id="run-456",
    )

    message = str(error)

    assert "PipelineStageError" in message
    assert "chembl" in message
    assert "target" in message
    assert "validate" in message
    assert "run-456" in message
