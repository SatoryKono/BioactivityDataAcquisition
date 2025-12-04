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


def test_client_network_error_properties(network_cause: Exception) -> None:
    error = ClientNetworkError(
        provider="chembl",
        message="connection failed",
        endpoint="/ping",
        cause=network_cause,
    )

    assert isinstance(error, ClientError)
    assert isinstance(error, ProviderError)
    assert isinstance(error, BioetlError)
    assert error.provider == "chembl"
    assert error.endpoint == "/ping"
    assert error.status_code is None
    assert error.cause is network_cause
    assert "ClientNetworkError" in str(error)
    assert "chembl" in str(error)
    assert "/ping" in str(error)


def test_client_rate_limit_error_properties() -> None:
    cause = RuntimeError("too many requests")
    error = ClientRateLimitError(
        provider="chembl",
        message="rate limited",
        endpoint="/activities",
        status_code=429,
        cause=cause,
    )

    assert isinstance(error, ClientError)
    assert isinstance(error, ProviderError)
    assert isinstance(error, BioetlError)
    assert error.provider == "chembl"
    assert error.endpoint == "/activities"
    assert error.status_code == 429
    assert error.cause is cause
    message = str(error)
    assert "ClientRateLimitError" in message
    assert "429" in message
    assert "chembl" in message
    assert "/activities" in message
    assert "rate limited" in message


def test_client_response_error_properties() -> None:
    cause = ValueError("invalid body")
    error = ClientResponseError(
        provider="chembl",
        message="unexpected response",
        endpoint="/targets",
        status_code=500,
        cause=cause,
    )

    assert isinstance(error, ClientError)
    assert isinstance(error, ProviderError)
    assert isinstance(error, BioetlError)
    assert error.provider == "chembl"
    assert error.endpoint == "/targets"
    assert error.status_code == 500
    assert error.cause is cause
    message = str(error)
    assert "ClientResponseError" in message
    assert "500" in message
    assert "chembl" in message
    assert "/targets" in message
    assert "unexpected response" in message
