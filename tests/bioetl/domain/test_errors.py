import pytest

from bioetl.domain.errors import (
    BioetlError,
    ClientError,
    ClientNetworkError,
    ClientRateLimitError,
    ClientResponseError,
    PipelineStageError,
    ProviderError,
)


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


@pytest.fixture
def network_cause() -> Exception:
    return ConnectionError("socket closed")


@pytest.mark.parametrize(
    ("error_factory", "expected_endpoint", "expected_status", "message_fragment"),
    [
        (
            lambda cause: ClientNetworkError(
                provider="chembl",
                message="connection failed",
                endpoint="/ping",
                cause=cause,
            ),
            "/ping",
            None,
            "connection failed",
        ),
        (
            lambda cause: ClientRateLimitError(
                provider="chembl",
                message="rate limited",
                endpoint="/activities",
                status_code=429,
                cause=cause,
            ),
            "/activities",
            429,
            "rate limited",
        ),
        (
            lambda cause: ClientResponseError(
                provider="chembl",
                message="unexpected response",
                endpoint="/targets",
                status_code=500,
                cause=cause,
            ),
            "/targets",
            500,
            "unexpected response",
        ),
    ],
)
def test_client_errors_properties(
    error_factory, expected_endpoint, expected_status, message_fragment
) -> None:
    cause = RuntimeError("reason")
    error = error_factory(cause)

    assert isinstance(error, ClientError)
    assert isinstance(error, ProviderError)
    assert isinstance(error, BioetlError)
    assert error.provider == "chembl"
    assert error.endpoint == expected_endpoint
    assert error.status_code == expected_status
    assert error.cause is cause
    message = str(error)
    assert error.__class__.__name__ in message
    assert "chembl" in message
    assert expected_endpoint in message
    if expected_status:
        assert str(expected_status) in message
    assert message_fragment in message
