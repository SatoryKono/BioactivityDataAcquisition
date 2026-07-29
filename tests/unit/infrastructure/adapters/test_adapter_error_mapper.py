# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Golden matrix tests for adapter -> domain error mapping.

Tests DomainInfraExceptionMapper directly (adapter_error_mapper.py facade removed).
"""

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
from bioetl.infrastructure.errors import (
    DomainErrorMappingInput,
    DomainInfraExceptionMapper,
)

_PROVIDERS = ["chembl", "pubchem", "uniprot", "crossref"]


@pytest.fixture
def mapper() -> DomainInfraExceptionMapper:
    return DomainInfraExceptionMapper(logger=MagicMock())


@pytest.mark.parametrize("provider", _PROVIDERS)
def test_map_auth_status_to_critical(
    mapper: DomainInfraExceptionMapper,
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
    mapper: DomainInfraExceptionMapper,
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
    assert mapped.retry_after == pytest.approx(60.0)
    assert mapped.get_reason_code() == "ADAPTER_HTTP_RATE_LIMIT"


@pytest.mark.parametrize("provider", _PROVIDERS)
def test_map_server_status_to_service_unavailable(
    mapper: DomainInfraExceptionMapper,
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
    mapper: DomainInfraExceptionMapper,
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
    mapper: DomainInfraExceptionMapper,
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
