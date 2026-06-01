"""Tests for health service.

Coverage target: ≥80%
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.health_service import (
    DataSourceFactoryPort,
    HealthCheckSummary,
    HealthResult,
    HealthService,
)
from bioetl.domain.ports.health_check import HealthCheckResult
from bioetl.domain.types import HealthStatus
from tests.helpers.clock import FixedClock


pytestmark = pytest.mark.unit

class TestHealthResult:
    """Tests for HealthResult dataclass."""

    def test_health_result_creation(self) -> None:
        """Test HealthResult initialization."""
        result = HealthResult(
            provider="chembl",
            status="healthy",
            latency_ms=150.5,
            endpoint="https://www.ebi.ac.uk/chembl/api/data/status.json",
        )
        assert result.provider == "chembl"
        assert result.status == "healthy"
        assert result.latency_ms == pytest.approx(150.5)
        assert result.endpoint == "https://www.ebi.ac.uk/chembl/api/data/status.json"

    def test_health_result_default_values(self) -> None:
        """Test HealthResult default values."""
        result = HealthResult(provider="test", status="unknown")
        assert result.latency_ms is None
        assert result.endpoint is None
        assert result.error is None
        assert result.checked_at is None

    def test_is_healthy(self) -> None:
        """Test is_healthy property."""
        healthy = HealthResult(provider="test", status="healthy")
        unhealthy = HealthResult(provider="test", status="unhealthy")

        assert healthy.is_healthy is True
        assert unhealthy.is_healthy is False

    def test_is_degraded(self) -> None:
        """Test is_degraded property."""
        degraded = HealthResult(provider="test", status="degraded")
        healthy = HealthResult(provider="test", status="healthy")

        assert degraded.is_degraded is True
        assert healthy.is_degraded is False

    def test_is_unhealthy(self) -> None:
        """Test is_unhealthy property."""
        unhealthy = HealthResult(provider="test", status="unhealthy")
        unknown = HealthResult(provider="test", status="unknown")
        healthy = HealthResult(provider="test", status="healthy")

        assert unhealthy.is_unhealthy is True
        assert unknown.is_unhealthy is True
        assert healthy.is_unhealthy is False

    def test_to_dict_basic(self) -> None:
        """Test to_dict with basic status."""
        result = HealthResult(provider="test", status="healthy")
        d = result.to_dict()

        assert d == {"status": "healthy"}

    def test_to_dict_with_latency(self) -> None:
        """Test to_dict includes latency when set."""
        result = HealthResult(provider="test", status="healthy", latency_ms=123.456)
        d = result.to_dict()

        assert d["latency_ms"] == "123.46"

    def test_to_dict_with_endpoint(self) -> None:
        """Test to_dict includes endpoint when set."""
        result = HealthResult(
            provider="test", status="healthy", endpoint="https://example.com"
        )
        d = result.to_dict()

        assert d["endpoint"] == "https://example.com"

    def test_to_dict_with_error(self) -> None:
        """Test to_dict includes error when set."""
        result = HealthResult(
            provider="test", status="unhealthy", error="Connection refused"
        )
        d = result.to_dict()

        assert d["error"] == "Connection refused"

    def test_to_dict_complete(self) -> None:
        """Test to_dict with all fields."""
        result = HealthResult(
            provider="test",
            status="degraded",
            latency_ms=500.0,
            endpoint="https://api.example.com/health",
            error="Slow response",
        )
        d = result.to_dict()

        assert d["status"] == "degraded"
        assert d["latency_ms"] == "500.00"
        assert d["endpoint"] == "https://api.example.com/health"
        assert d["error"] == "Slow response"


class TestHealthCheckSummary:
    """Tests for HealthCheckSummary dataclass."""

    def test_summary_creation(self) -> None:
        """Test HealthCheckSummary initialization."""
        results = {
            "chembl": HealthResult(provider="chembl", status="healthy"),
            "uniprot": HealthResult(provider="uniprot", status="healthy"),
        }
        summary = HealthCheckSummary(results=results, all_healthy=True)

        assert summary.all_healthy is True
        assert len(summary.results) == 2

    def test_healthy_count(self) -> None:
        """Test healthy_count property."""
        results = {
            "chembl": HealthResult(provider="chembl", status="healthy"),
            "uniprot": HealthResult(provider="uniprot", status="unhealthy"),
            "pubchem": HealthResult(provider="pubchem", status="healthy"),
        }
        summary = HealthCheckSummary(results=results, all_healthy=False)

        assert summary.healthy_count == 2

    def test_unhealthy_count(self) -> None:
        """Test unhealthy_count property."""
        results = {
            "chembl": HealthResult(provider="chembl", status="healthy"),
            "uniprot": HealthResult(provider="uniprot", status="unhealthy"),
            "pubchem": HealthResult(provider="pubchem", status="unknown"),
        }
        summary = HealthCheckSummary(results=results, all_healthy=False)

        assert summary.unhealthy_count == 2

    def test_to_dict(self) -> None:
        """Test to_dict method."""
        results = {
            "chembl": HealthResult(provider="chembl", status="healthy"),
        }
        summary = HealthCheckSummary(results=results, all_healthy=True)
        d = summary.to_dict()

        assert "chembl" in d
        assert d["chembl"]["status"] == "healthy"


class TestDataSourceFactoryPort:
    """Tests for DataSourceFactoryPort protocol."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test DataSourceFactoryPort is runtime checkable."""

        class MockFactory:
            @staticmethod
            def list_providers() -> list[str]:
                return ["chembl"]

            @staticmethod
            def create(_provider_name: str) -> Any:
                return MagicMock()

        assert isinstance(MockFactory(), DataSourceFactoryPort)


class TestHealthService:
    """Tests for HealthService."""

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_factory(self) -> MagicMock:
        """Create mock data source factory."""
        factory = MagicMock()
        factory.list_providers.return_value = ["chembl", "uniprot", "pubchem"]
        return factory

    @pytest.fixture
    def service(self, mock_logger: MagicMock, mock_factory: MagicMock) -> HealthService:
        """Create HealthService with mocked dependencies."""
        return HealthService(
            logger=mock_logger,
            _factory=mock_factory,
            clock=FixedClock(datetime(2026, 4, 24, 12, 0, tzinfo=UTC)),
        )

    @pytest.mark.asyncio
    async def test_check_providers_all_healthy(
        self, service: HealthService, mock_factory: MagicMock
    ) -> None:
        """Test check_providers when all providers are healthy."""
        # Setup mock adapter with HealthCheckPort
        # Must have provider_name property for isinstance(adapter, HealthCheckPort) to pass
        mock_adapter = MagicMock()
        mock_adapter.provider_name = "test"
        mock_adapter.check_health = AsyncMock(
            return_value=HealthCheckResult(
                status=HealthStatus.HEALTHY,
                latency_ms=100.0,
                provider="test",
                endpoint="https://api.example.com/status",
                checked_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            )
        )
        mock_factory.create.return_value = mock_adapter

        summary = await service.check_providers()

        assert summary.all_healthy is True
        assert len(summary.results) == 3
        assert summary.healthy_count == 3

    @pytest.mark.asyncio
    async def test_check_providers_specific_providers(
        self, service: HealthService, mock_factory: MagicMock
    ) -> None:
        """Test check_providers with specific provider list."""
        mock_adapter = MagicMock()
        mock_adapter.provider_name = "chembl"
        mock_adapter.check_health = AsyncMock(
            return_value=HealthCheckResult(
                status=HealthStatus.HEALTHY,
                latency_ms=50.0,
                provider="chembl",
                checked_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            )
        )
        mock_factory.create.return_value = mock_adapter

        summary = await service.check_providers(providers=["chembl"])

        assert len(summary.results) == 1
        assert "chembl" in summary.results

    @pytest.mark.asyncio
    async def test_check_providers_with_unhealthy(
        self, service: HealthService, mock_factory: MagicMock
    ) -> None:
        """Test check_providers when some providers are unhealthy."""
        mock_adapter = MagicMock()
        mock_adapter.provider_name = "uniprot"
        mock_adapter.check_health = AsyncMock(
            return_value=HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=0.0,
                provider="uniprot",
                last_error="Connection failed",
                checked_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            )
        )
        mock_factory.create.return_value = mock_adapter

        summary = await service.check_providers(providers=["uniprot"])

        assert summary.all_healthy is False
        assert summary.results["uniprot"].status == "unhealthy"

    @pytest.mark.asyncio
    async def test_check_single_provider_no_health_check_port(
        self, service: HealthService, mock_factory: MagicMock
    ) -> None:
        """Test _check_single_provider when adapter doesn't implement HealthCheckPort."""
        # Create adapter without HealthCheckPort implementation
        mock_adapter = MagicMock(spec=[])  # Empty spec = no methods
        mock_factory.create.return_value = mock_adapter

        result = await service._check_single_provider("test_provider")

        assert result.status == "unknown"
        assert "does not implement HealthCheckPort" in (result.error or "")

    @pytest.mark.asyncio
    async def test_check_single_provider_exception(
        self, service: HealthService, mock_factory: MagicMock
    ) -> None:
        """Test _check_single_provider handles exceptions."""
        mock_factory.create.side_effect = RuntimeError("Factory error")

        result = await service._check_single_provider("bad_provider")

        assert result.status == "unhealthy"
        assert result.error == "Factory error"

    def test_list_available_providers(
        self, service: HealthService, mock_factory: MagicMock
    ) -> None:
        """Test list_available_providers returns factory providers."""
        providers = service.list_available_providers()

        assert providers == ["chembl", "uniprot", "pubchem"]
        mock_factory.list_providers.assert_called_once()


class TestHealthServiceEdgeCases:
    """Edge case tests for HealthService."""

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create mock logger."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_check_providers_empty_list(self, mock_logger: MagicMock) -> None:
        """Test check_providers with empty available providers."""
        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = []
        service = HealthService(
            logger=mock_logger,
            _factory=mock_factory,
            clock=FixedClock(datetime(2026, 4, 24, 12, 0, tzinfo=UTC)),
        )

        summary = await service.check_providers()

        assert len(summary.results) == 0
        assert summary.all_healthy is True  # No providers = all healthy vacuously

    @pytest.mark.asyncio
    async def test_check_providers_logs_correctly(self, mock_logger: MagicMock) -> None:
        """Test that check_providers logs appropriately."""
        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["test"]

        mock_adapter = MagicMock()
        mock_adapter.provider_name = "test"
        mock_adapter.check_health = AsyncMock(
            return_value=HealthCheckResult(
                status=HealthStatus.HEALTHY,
                latency_ms=100.0,
                provider="test",
                checked_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            )
        )
        mock_factory.create.return_value = mock_adapter

        service = HealthService(
            logger=mock_logger,
            _factory=mock_factory,
            clock=FixedClock(datetime(2026, 4, 24, 12, 0, tzinfo=UTC)),
        )
        await service.check_providers()

        # Verify logging calls
        mock_logger.debug.assert_called()
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_health_result_with_degraded_status(
        self, mock_logger: MagicMock
    ) -> None:
        """Test handling of degraded health status."""
        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["test"]

        mock_adapter = MagicMock()
        mock_adapter.provider_name = "test"
        mock_adapter.check_health = AsyncMock(
            return_value=HealthCheckResult(
                status=HealthStatus.DEGRADED,
                latency_ms=5000.0,
                provider="test",
                last_error="High latency",
                checked_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            )
        )
        mock_factory.create.return_value = mock_adapter

        service = HealthService(
            logger=mock_logger,
            _factory=mock_factory,
            clock=FixedClock(datetime(2026, 4, 24, 12, 0, tzinfo=UTC)),
        )
        summary = await service.check_providers()

        assert summary.results["test"].status == "degraded"
        assert summary.results["test"].is_degraded is True
