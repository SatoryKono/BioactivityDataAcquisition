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
"""Runtime contract tests for Semantic Scholar health/metadata protocols."""

from __future__ import annotations

import asyncio
from types import TracebackType
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.semanticscholar import SemanticScholarAdapter
from bioetl.infrastructure.adapters.semanticscholar.health_metadata_mixin import (
    SemanticScholarAdapterMetricsProtocol,
    SemanticScholarHTTPClientProtocol,
    SemanticScholarHealthMetadataDependencies,
    SemanticScholarRequestCollectorProtocol,
)
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs


class _ResponseStub:
    status_code: int = 200


class _HTTPClientStub:
    async def get_once(
        self,
        url: str,
        params: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> _ResponseStub:
        await asyncio.sleep(0)
        del url, params, headers
        return _ResponseStub()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        del exc_type, exc_value, traceback
        return None


@pytest.mark.unit
def test_http_client_protocol_contract() -> None:
    """HTTP client stub satisfies runtime protocol contract."""
    assert isinstance(_HTTPClientStub(), SemanticScholarHTTPClientProtocol)


@pytest.mark.unit
def test_request_collector_protocol_contract() -> None:
    """APIRequestCollector satisfies runtime protocol contract."""
    assert isinstance(APIRequestCollector(), SemanticScholarRequestCollectorProtocol)


@pytest.mark.unit
def test_adapter_metrics_protocol_contract() -> None:
    """AdapterMetricsRecorder satisfies runtime protocol contract."""
    metrics = AdapterMetricsRecorder(metrics=NoOpMetrics(), provider="semanticscholar")
    assert isinstance(metrics, SemanticScholarAdapterMetricsProtocol)


@pytest.mark.unit
def test_adapter_satisfies_health_metadata_dependency_protocol() -> None:
    """SemanticScholarAdapter satisfies host dependency contract."""
    http_client = MagicMock()
    http_client.get_once = AsyncMock(return_value=_ResponseStub())
    http_client.__aexit__ = AsyncMock(return_value=None)

    logger = MagicMock()
    logger.warning = MagicMock()

    adapter = SemanticScholarAdapter(
        http_client=http_client,
        logger=logger,
        **build_http_adapter_runtime_kwargs(
            "semanticscholar",
            logger=logger,
            include_fallback_service=True,
        ),
    )
    assert isinstance(adapter, SemanticScholarHealthMetadataDependencies)
