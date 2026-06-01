"""Unit tests for public composition service entrypoints.

Tests the service entrypoint functions exposed via
``bioetl.composition.services_api``. Dedicated entrypoint-boundary coverage is
allowed to patch the internal ``bioetl.composition._services`` seam directly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.composition.registry_api import PipelineRegistry


# =============================================================================
# Helper
# =============================================================================


def _patch_services(*args: str, **kwargs: MagicMock):
    """Return a list of patches for service entrypoint internals."""
    pass


# =============================================================================
# Tests for get_checkpoint_service
# =============================================================================


@pytest.mark.unit
class TestGetCheckpointService:
    """Tests for get_checkpoint_service function."""

    def test_get_checkpoint_service__and_bootstrap__c510ca52(self) -> None:
        """Test that get_checkpoint_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="CheckpointService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_checkpoint_service

            result = get_checkpoint_service()

        mock_ensure.assert_called_once_with(scope="providers")
        mock_bootstrap.assert_called_once_with("bootstrap_checkpoint_service")
        assert result is mock_service


# =============================================================================
# Tests for get_quarantine_service
# =============================================================================


@pytest.mark.unit
class TestGetQuarantineService:
    """Tests for get_quarantine_service function."""

    def test_bootstraps_without_registration_gate(self) -> None:
        """Quarantine admin service must not block on pipeline registration."""
        mock_service = MagicMock(name="QuarantineService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_quarantine_service

            result = get_quarantine_service()

        mock_ensure.assert_not_called()
        mock_bootstrap.assert_called_once_with("bootstrap_quarantine_service")
        assert result is mock_service


# =============================================================================
# Tests for get_bronze_cleanup_service
# =============================================================================


@pytest.mark.unit
class TestGetBronzeCleanupService:
    """Tests for get_bronze_cleanup_service function."""

    def test_bronze_cleanup_service__and_bootstrap__60b9f1fb(self) -> None:
        """Test that get_bronze_cleanup_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="BronzeCleanupService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_bronze_cleanup_service

            result = get_bronze_cleanup_service()

        mock_ensure.assert_called_once_with(scope="providers")
        mock_bootstrap.assert_called_once_with("bootstrap_bronze_cleanup_service")
        assert result is mock_service


# =============================================================================
# Tests for get_vacuum_service
# =============================================================================


@pytest.mark.unit
class TestGetVacuumService:
    """Tests for get_vacuum_service function."""

    def test_get_vacuum_service__and_bootstrap__a074c478(self) -> None:
        """Test that get_vacuum_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="VacuumService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_vacuum_service

            result = get_vacuum_service()

        mock_ensure.assert_called_once_with(scope="providers")
        mock_bootstrap.assert_called_once_with("bootstrap_vacuum_service")
        assert result is mock_service


# =============================================================================
# Tests for get_export_service
# =============================================================================


@pytest.mark.unit
class TestGetExportService:
    """Tests for get_export_service function."""

    def test_get_export_service__and_bootstrap__effadfdd(self) -> None:
        """Test that get_export_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="ExportService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_export_service

            result = get_export_service()

        mock_ensure.assert_called_once_with(scope="providers")
        mock_bootstrap.assert_called_once_with("bootstrap_export_service")
        assert result is mock_service


# =============================================================================
# Tests for get_lock_service
# =============================================================================


@pytest.mark.unit
class TestGetLockService:
    """Tests for get_lock_service function."""

    def test_get_lock_service__and_bootstrap__db289cf0(self) -> None:
        """Test that get_lock_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="LockService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_lock_service

            result = get_lock_service()

        mock_ensure.assert_called_once_with(scope="providers")
        mock_bootstrap.assert_called_once_with("bootstrap_lock_service")
        assert result is mock_service


# =============================================================================
# Tests for cleanup_bronze (async convenience function)
# =============================================================================


@pytest.mark.unit
class TestCleanupBronze:
    """Tests for cleanup_bronze async function."""

    @pytest.mark.asyncio
    async def test_cleanup_bronze_calls_service_cleanup(self) -> None:
        """Test that cleanup_bronze calls service.cleanup with correct args."""
        mock_result = MagicMock()
        mock_result.files_removed = 15

        mock_service = MagicMock()
        mock_service.cleanup = AsyncMock(return_value=mock_result)

        with (
            patch(
                "bioetl.composition._services.get_bronze_cleanup_service",
                return_value=mock_service,
            ),
        ):
            from bioetl.composition.services_api import cleanup_bronze

            result = await cleanup_bronze(retention_days=90, dry_run=False)

        mock_service.cleanup.assert_called_once_with(
            retention_days=90,
            dry_run=False,
        )
        assert result is mock_result

    @pytest.mark.asyncio
    async def test_cleanup_bronze_default_args(self) -> None:
        """Test that cleanup_bronze uses default retention_days=90 and dry_run=False."""
        mock_service = MagicMock()
        mock_service.cleanup = AsyncMock(return_value=MagicMock())

        with (
            patch(
                "bioetl.composition._services.get_bronze_cleanup_service",
                return_value=mock_service,
            ),
        ):
            from bioetl.composition.services_api import cleanup_bronze

            await cleanup_bronze()

        call_kwargs = mock_service.cleanup.call_args.kwargs
        assert call_kwargs["retention_days"] == 90
        assert call_kwargs["dry_run"] is False

    @pytest.mark.asyncio
    async def test_cleanup_bronze_dry_run_mode(self) -> None:
        """Test that cleanup_bronze respects dry_run=True."""
        mock_service = MagicMock()
        mock_service.cleanup = AsyncMock(return_value=MagicMock())

        with (
            patch(
                "bioetl.composition._services.get_bronze_cleanup_service",
                return_value=mock_service,
            ),
        ):
            from bioetl.composition.services_api import cleanup_bronze

            await cleanup_bronze(retention_days=30, dry_run=True)

        call_kwargs = mock_service.cleanup.call_args.kwargs
        assert call_kwargs["dry_run"] is True
        assert call_kwargs["retention_days"] == 30


# =============================================================================
# Tests for get_pipeline_runner_service
# =============================================================================


@pytest.mark.unit
class TestGetPipelineRunnerService:
    """Tests for get_pipeline_runner_service function."""

    def test_runner_service__and_bootstrap__9eb6ffb6(self) -> None:
        """Test that get_pipeline_runner_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="PipelineRunnerService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_pipeline_runner_service

            result = get_pipeline_runner_service()

        mock_ensure.assert_called_once_with(registry=None, scope="pipelines")
        mock_bootstrap.assert_called_once_with(
            "bootstrap_pipeline_runner_service", registry=None
        )
        assert result is mock_service

    def test_passes_explicit_registry_to_registration_and_bootstrap(self) -> None:
        """Explicit registry should flow through the runner service bootstrap path."""
        mock_service = MagicMock(name="PipelineRunnerService")
        registry = PipelineRegistry()

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_pipeline_runner_service

            result = get_pipeline_runner_service(registry=registry)

        mock_ensure.assert_called_once_with(registry=registry, scope="pipelines")
        mock_bootstrap.assert_called_once_with(
            "bootstrap_pipeline_runner_service",
            registry=registry,
        )
        assert result is mock_service


# =============================================================================
# Tests for get_config_service
# =============================================================================


@pytest.mark.unit
class TestGetConfigService:
    """Tests for get_config_service function."""

    def test_get_config_service__and_bootstrap__2f7acc18(self) -> None:
        """Test that get_config_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="ConfigService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_config_service

            result = get_config_service()

        mock_ensure.assert_called_once_with(scope="providers")
        mock_bootstrap.assert_called_once_with("bootstrap_config_service")
        assert result is mock_service


# =============================================================================
# Tests for get_health_service
# =============================================================================


@pytest.mark.unit
class TestGetHealthService:
    """Tests for get_health_service function."""

    def test_get_health_service__and_bootstrap__f5d64bb6(self) -> None:
        """Test that get_health_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="HealthService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_health_service

            result = get_health_service()

        mock_ensure.assert_called_once_with(scope="providers")
        mock_bootstrap.assert_called_once_with("bootstrap_health_service")
        assert result is mock_service


# =============================================================================
# Tests for get_health_server_dependencies
# =============================================================================


@pytest.mark.unit
class TestGetHealthServerDependencies:
    """Tests for get_health_server_dependencies function."""

    def test_server_dependencies__registration_gate__ab2e95af(self) -> None:
        """Health listener bootstrap must not block on pipeline registration."""
        mock_deps = MagicMock(name="HealthServerDependencies")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_deps,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_health_server_dependencies

            result = get_health_server_dependencies()

        mock_ensure.assert_not_called()
        mock_bootstrap.assert_called_once_with("bootstrap_health_server_dependencies")
        assert result is mock_deps


# =============================================================================
# Tests for get_metrics_service
# =============================================================================


@pytest.mark.unit
class TestGetMetricsService:
    """Tests for get_metrics_service function."""

    def test_get_metrics_service__and_bootstrap__aefe34bf(self) -> None:
        """Test that get_metrics_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="MetricsService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_metrics_service

            result = get_metrics_service()

        mock_ensure.assert_called_once_with(scope="providers")
        mock_bootstrap.assert_called_once_with("bootstrap_metrics_service")
        assert result is mock_service


# =============================================================================
# Tests for get_adr_service
# =============================================================================


@pytest.mark.unit
class TestGetAdrService:
    """Tests for get_adr_service function."""

    def test_get_adr_service__and_bootstrap__eed8d980(self) -> None:
        """Test that get_adr_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="AdrServicePort")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_adr_service

            result = get_adr_service()

        mock_ensure.assert_called_once_with(scope="providers")
        mock_bootstrap.assert_called_once_with("bootstrap_adr_service")
        assert result is mock_service


# =============================================================================
# Tests for get_quarantine_port
# =============================================================================


@pytest.mark.unit
class TestGetQuarantinePort:
    """Tests for get_quarantine_port function."""

    def test_get_quarantine_port__registration_gate__0bc3dfab(self) -> None:
        """Shared quarantine storage must not depend on pipeline registration."""
        mock_port = MagicMock(name="QuarantinePort")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_port,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.services_api import get_quarantine_port

            result = get_quarantine_port()

        mock_ensure.assert_not_called()
        mock_bootstrap.assert_called_once_with("bootstrap_quarantine_adapter")
        assert result is mock_port

    def test_returns_shared_port_without_pipeline_context(self) -> None:
        """Test that the accessor no longer exposes a misleading pipeline parameter."""
        mock_port = MagicMock(name="QuarantinePort")

        with (
            patch(
                "bioetl.composition._services._invoke_bootstrap",
                return_value=mock_port,
            ),
        ):
            from bioetl.composition.services_api import get_quarantine_port

            result = get_quarantine_port()
            assert result is mock_port
