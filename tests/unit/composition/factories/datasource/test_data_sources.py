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
"""Tests for DataSourceFactory."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from unittest.mock import Mock

import pytest

from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceFactory,
)
from bioetl.composition.providers.provider_registry import (
    ProviderConfig,
    create_provider_registry,
)
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.domain.types import HealthStatus


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_http_client():
    return Mock(spec=UnifiedHTTPClient)


@pytest.fixture
def mock_logger():
    return Mock()


def test_create_pubchem_adapter(mock_http_client, mock_logger):
    """Test creating PubChem adapter."""
    # PubChem doesn't use http_client
    adapter = DataSourceFactory.create(
        "pubchem", http_client=mock_http_client, logger=mock_logger, rate=1.0
    )

    # Use class name check to avoid reload issues
    assert adapter.__class__.__name__ == "PubChemAdapter"
    assert adapter.provider_name == "pubchem"


def test_create_uniprot_adapter(mock_http_client, mock_logger):
    """Test creating UniProt adapter."""
    adapter = DataSourceFactory.create(
        "uniprot", http_client=mock_http_client, logger=mock_logger, api_key="test_key"
    )

    # Use class name check to avoid reload issues
    assert adapter.__class__.__name__ == "UniProtAdapter"
    assert adapter.provider_name == "uniprot"
    assert adapter.api_key == "test_key"


def test_create_unknown_provider(mock_http_client):
    """Test creating unknown provider raises ValueError."""
    with pytest.raises(ValueError, match="Unknown provider: unknown"):
        DataSourceFactory.create("unknown", http_client=mock_http_client)


def test_create_uses_explicit_provider_registry(mock_http_client, mock_logger):
    """Factory should honor an injected provider registry instance."""
    isolated = create_provider_registry()

    @dataclass
    class LocalAdapter:
        http_client: object | None = None
        logger: object | None = None
        provider_name: str = "isolated"

        async def _close_async(self) -> None:
            await asyncio.sleep(0)
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
            del exc_type, exc_val, exc_tb
            return await self._close_async()

        async def fetch(self, *args, **kwargs):
            yield {}

        async def health_check(self) -> HealthStatus:
            await asyncio.sleep(0)
            return HealthStatus.HEALTHY

        async def aclose(self) -> None:
            return await self._close_async()

    isolated.register(
        "isolated",
        ProviderConfig(
            adapter_class=LocalAdapter,
            requires_http_client=True,
            requires_logger=True,
        ),
    )

    adapter = DataSourceFactory.create(
        "isolated",
        http_client=mock_http_client,
        logger=mock_logger,
        provider_registry=isolated,
    )

    assert adapter.__class__.__name__ == "LocalAdapter"
    assert adapter.http_client is mock_http_client
    assert adapter.logger is mock_logger
