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
"""Same-path owner tests for infrastructure exception mapper module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.domain.exceptions import ServiceUnavailableError
from bioetl.infrastructure.errors.exception_mapper import (
    DomainErrorMappingInput,
    DomainInfraExceptionMapper,
)


pytestmark = pytest.mark.unit


def test_exception_mapper_maps_service_unavailable_to_retryable_disposition() -> None:
    mapper = DomainInfraExceptionMapper(logger=MagicMock())

    disposition = mapper.map_domain_to_infra_disposition(
        ServiceUnavailableError("downstream unavailable", service_name="chembl")
    )

    assert disposition.severity == "recoverable"
    assert disposition.retryable is True


def test_exception_mapper_uses_default_retry_after_for_rate_limit_status() -> None:
    mapper = DomainInfraExceptionMapper(logger=MagicMock())

    error = mapper.map_to_domain_error(
        DomainErrorMappingInput(
            error=RuntimeError("too many requests"),
            provider="crossref",
            error_type=ServiceUnavailableError.error_type,
            status_code=429,
        )
    )

    assert error.retry_after == pytest.approx(60.0)
    assert error.service_name == "crossref"
