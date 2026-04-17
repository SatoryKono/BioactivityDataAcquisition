"""Contract tests for unified domain<->infrastructure exception mapper."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.domain.exceptions import (
    CriticalError,
    DomainExceptionContext,
    PolicyViolationError,
    RateLimitExceededError,
    ServiceUnavailableError,
    StorageError,
)
from bioetl.domain.types import ErrorType
from bioetl.infrastructure.errors import (
    DomainErrorMappingInput,
    DomainInfraExceptionMapper,
)


@pytest.fixture
def mapper() -> DomainInfraExceptionMapper:
    return DomainInfraExceptionMapper(logger=MagicMock())


def test_map_to_domain_error_rate_limit(mapper: DomainInfraExceptionMapper) -> None:
    source = ValueError("limited")
    mapped = mapper.map_to_domain_error(
        DomainErrorMappingInput(
            error=source,
            provider="chembl",
            error_type=ErrorType.INVALID_DATA,
            status_code=429,
            entity="publication",
            pipeline="chembl_publication",
            operation="fetch_batch",
        )
    )
    assert isinstance(mapped, RateLimitExceededError)
    assert mapped.retry_after == pytest.approx(60.0)
    assert mapped.get_reason_code() == "ADAPTER_HTTP_RATE_LIMIT"
    assert mapped.__cause__ is source
    assert mapped.context.get("provider") == "chembl"
    assert mapped.context.get("entity") == "publication"
    assert mapped.context.get("pipeline") == "chembl_publication"
    assert mapped.context.get("operation") == "fetch_batch"


def test_map_to_domain_error_server_error(mapper: DomainInfraExceptionMapper) -> None:
    source = RuntimeError("down")
    mapped = mapper.map_to_domain_error(
        DomainErrorMappingInput(
            error=source,
            provider="pubchem",
            error_type=ErrorType.NETWORK_ERROR,
            status_code=503,
        )
    )
    assert isinstance(mapped, ServiceUnavailableError)
    assert mapped.status_code == 503
    assert mapped.get_reason_code() == "ADAPTER_HTTP_SERVER_ERROR"
    assert mapped.__cause__ is source


def test_map_to_domain_error_auth_raises_critical(
    mapper: DomainInfraExceptionMapper,
) -> None:
    source = PermissionError("unauthorized")
    with pytest.raises(CriticalError) as exc_info:
        mapper.map_to_domain_error(
            DomainErrorMappingInput(
                error=source,
                provider="uniprot",
                error_type=ErrorType.INVALID_DATA,
                status_code=401,
                entity="protein",
                pipeline="uniprot_protein",
            )
        )
    error = exc_info.value
    assert error.get_reason_code() == "ADAPTER_AUTH_FAILED"
    assert error.__cause__ is source
    assert error.context.get("provider") == "uniprot"
    assert error.context.get("entity") == "protein"
    assert error.context.get("pipeline") == "uniprot_protein"


def test_map_to_domain_error_timeout_without_status(
    mapper: DomainInfraExceptionMapper,
) -> None:
    source = TimeoutError("timeout")
    mapped = mapper.map_to_domain_error(
        DomainErrorMappingInput(
            error=source,
            provider="openalex",
            error_type=ErrorType.TIMEOUT,
        )
    )
    assert isinstance(mapped, ServiceUnavailableError)
    assert mapped.status_code is None
    assert mapped.get_reason_code() == "ADAPTER_TIMEOUT_ERROR"
    assert mapped.__cause__ is source


def test_map_domain_to_infra_disposition_recoverable(
    mapper: DomainInfraExceptionMapper,
) -> None:
    disposition = mapper.map_domain_to_infra_disposition(StorageError("temporary"))
    assert disposition.context == DomainExceptionContext.STORAGE
    assert disposition.severity == "recoverable"
    assert disposition.retryable is True


def test_map_domain_to_infra_disposition_critical(
    mapper: DomainInfraExceptionMapper,
) -> None:
    disposition = mapper.map_domain_to_infra_disposition(
        PolicyViolationError("invalid mode")
    )
    assert disposition.context == DomainExceptionContext.ORCHESTRATION
    assert disposition.severity == "critical"
    assert disposition.retryable is False
