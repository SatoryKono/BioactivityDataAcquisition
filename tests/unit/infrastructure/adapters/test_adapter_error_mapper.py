"""Golden matrix tests for adapter -> domain error mapping."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.domain.exceptions import (
    CriticalError,
    ExternalServiceError,
    RateLimitExceededError,
    ServiceUnavailableError,
)
from bioetl.domain.types import ErrorType
from bioetl.infrastructure.adapters.adapter_error_mapper import (
    AdapterErrorMapper,
    DomainErrorMappingInput,
)

_PROVIDERS = ["chembl", "pubchem", "uniprot", "crossref"]


@pytest.fixture
def mapper() -> AdapterErrorMapper:
    return AdapterErrorMapper(logger=MagicMock())


@pytest.mark.parametrize("provider", _PROVIDERS)
def test_map_auth_status_to_critical(
    mapper: AdapterErrorMapper,
    provider: str,
) -> None:
    payload = DomainErrorMappingInput(
        error=ValueError("unauthorized"),
        provider=provider,
        error_type=ErrorType.INVALID_DATA,
        status_code=401,
    )

    with pytest.raises(CriticalError):
        mapper.map_to_domain_error(payload)


@pytest.mark.parametrize("provider", _PROVIDERS)
def test_map_rate_limit_status_to_domain_error(
    mapper: AdapterErrorMapper,
    provider: str,
) -> None:
    payload = DomainErrorMappingInput(
        error=ValueError("limited"),
        provider=provider,
        error_type=ErrorType.INVALID_DATA,
        status_code=429,
    )
    mapped = mapper.map_to_domain_error(payload)

    assert isinstance(mapped, RateLimitExceededError)
    assert mapped.service_name == provider
    assert mapped.retry_after == 60.0
    assert mapped.get_reason_code() == "ADAPTER_HTTP_RATE_LIMIT"


@pytest.mark.parametrize("provider", _PROVIDERS)
def test_map_server_status_to_service_unavailable(
    mapper: AdapterErrorMapper,
    provider: str,
) -> None:
    payload = DomainErrorMappingInput(
        error=ValueError("down"),
        provider=provider,
        error_type=ErrorType.NETWORK_ERROR,
        status_code=503,
    )
    mapped = mapper.map_to_domain_error(payload)

    assert isinstance(mapped, ServiceUnavailableError)
    assert mapped.service_name == provider
    assert mapped.status_code == 503
    assert mapped.get_reason_code() == "ADAPTER_HTTP_SERVER_ERROR"


@pytest.mark.parametrize("provider", _PROVIDERS)
def test_map_timeout_type_without_status(
    mapper: AdapterErrorMapper,
    provider: str,
) -> None:
    payload = DomainErrorMappingInput(
        error=TimeoutError("timeout"),
        provider=provider,
        error_type=ErrorType.TIMEOUT,
    )
    mapped = mapper.map_to_domain_error(payload)

    assert isinstance(mapped, ServiceUnavailableError)
    assert mapped.service_name == provider
    assert mapped.status_code is None
    assert mapped.get_reason_code() == "ADAPTER_TIMEOUT_ERROR"


@pytest.mark.parametrize("provider", _PROVIDERS)
def test_map_generic_type_without_status(
    mapper: AdapterErrorMapper,
    provider: str,
) -> None:
    payload = DomainErrorMappingInput(
        error=RuntimeError("network"),
        provider=provider,
        error_type=ErrorType.NETWORK_ERROR,
    )
    mapped = mapper.map_to_domain_error(payload)

    assert isinstance(mapped, ExternalServiceError)
    assert not isinstance(mapped, ServiceUnavailableError | RateLimitExceededError)
    assert mapped.service_name == provider
    assert mapped.get_reason_code() == "ADAPTER_EXTERNAL_ERROR"
