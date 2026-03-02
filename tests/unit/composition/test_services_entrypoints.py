"""Unit tests for composition/_services.py.

Tests the service entrypoint functions that delegate to bootstrap functions.
All external dependencies (bootstrap, _ensure_registrations) are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# Helper
# =============================================================================


def _patch_services(*args: str, **kwargs: MagicMock):
    """Return a list of patches for _services module internals."""
    pass


# =============================================================================
# Tests for get_checkpoint_service
# =============================================================================


@pytest.mark.unit
class TestGetCheckpointService:
    """Tests for get_checkpoint_service function."""

    def test_calls_ensure_registrations_and_bootstrap(self) -> None:
        """Test that get_checkpoint_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="CheckpointService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services.bootstrap_checkpoint_service",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition._services import get_checkpoint_service

            result = get_checkpoint_service()

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
        assert result is mock_service


# =============================================================================
# Tests for get_quarantine_service
# =============================================================================


@pytest.mark.unit
class TestGetQuarantineService:
    """Tests for get_quarantine_service function."""

    def test_calls_ensure_registrations_and_bootstrap(self) -> None:
        """Test that get_quarantine_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="QuarantineService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services.bootstrap_quarantine_service",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition._services import get_quarantine_service

            result = get_quarantine_service()

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
        assert result is mock_service


# =============================================================================
# Tests for get_bronze_cleanup_service
# =============================================================================


@pytest.mark.unit
class TestGetBronzeCleanupService:
    """Tests for get_bronze_cleanup_service function."""

    def test_calls_ensure_registrations_and_bootstrap(self) -> None:
        """Test that get_bronze_cleanup_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="BronzeCleanupService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services.bootstrap_bronze_cleanup_service",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition._services import get_bronze_cleanup_service

            result = get_bronze_cleanup_service()

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
        assert result is mock_service


# =============================================================================
# Tests for get_vacuum_service
# =============================================================================


@pytest.mark.unit
class TestGetVacuumService:
    """Tests for get_vacuum_service function."""

    def test_calls_ensure_registrations_and_bootstrap(self) -> None:
        """Test that get_vacuum_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="VacuumService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services.bootstrap_vacuum_service",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition._services import get_vacuum_service

            result = get_vacuum_service()

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
        assert result is mock_service


# =============================================================================
# Tests for get_export_service
# =============================================================================


@pytest.mark.unit
class TestGetExportService:
    """Tests for get_export_service function."""

    def test_calls_ensure_registrations_and_bootstrap(self) -> None:
        """Test that get_export_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="ExportService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services.bootstrap_export_service",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition._services import get_export_service

            result = get_export_service()

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
        assert result is mock_service


# =============================================================================
# Tests for get_lock_service
# =============================================================================


@pytest.mark.unit
class TestGetLockService:
    """Tests for get_lock_service function."""

    def test_calls_ensure_registrations_and_bootstrap(self) -> None:
        """Test that get_lock_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="LockService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services.bootstrap_lock_service",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition._services import get_lock_service

            result = get_lock_service()

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
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
            patch("bioetl.composition._services._ensure_registrations"),
            patch(
                "bioetl.composition._services.bootstrap_bronze_cleanup_service",
                return_value=mock_service,
            ),
        ):
            from bioetl.composition._services import cleanup_bronze

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
            patch("bioetl.composition._services._ensure_registrations"),
            patch(
                "bioetl.composition._services.bootstrap_bronze_cleanup_service",
                return_value=mock_service,
            ),
        ):
            from bioetl.composition._services import cleanup_bronze

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
            patch("bioetl.composition._services._ensure_registrations"),
            patch(
                "bioetl.composition._services.bootstrap_bronze_cleanup_service",
                return_value=mock_service,
            ),
        ):
            from bioetl.composition._services import cleanup_bronze

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

    def test_calls_ensure_registrations_and_bootstrap(self) -> None:
        """Test that get_pipeline_runner_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="PipelineRunnerService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services.bootstrap_pipeline_runner_service",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition._services import get_pipeline_runner_service

            result = get_pipeline_runner_service()

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
        assert result is mock_service


# =============================================================================
# Tests for get_config_service
# =============================================================================


@pytest.mark.unit
class TestGetConfigService:
    """Tests for get_config_service function."""

    def test_calls_ensure_registrations_and_bootstrap(self) -> None:
        """Test that get_config_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="ConfigService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services.bootstrap_config_service",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition._services import get_config_service

            result = get_config_service()

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
        assert result is mock_service


# =============================================================================
# Tests for get_health_service
# =============================================================================


@pytest.mark.unit
class TestGetHealthService:
    """Tests for get_health_service function."""

    def test_calls_ensure_registrations_and_bootstrap(self) -> None:
        """Test that get_health_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="HealthService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services.bootstrap_health_service",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition._services import get_health_service

            result = get_health_service()

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
        assert result is mock_service


# =============================================================================
# Tests for get_health_server_dependencies
# =============================================================================


@pytest.mark.unit
class TestGetHealthServerDependencies:
    """Tests for get_health_server_dependencies function."""

    def test_calls_ensure_registrations_and_bootstrap(self) -> None:
        """Test that get_health_server_dependencies calls _ensure_registrations and bootstrap."""
        mock_deps = MagicMock(name="HealthServerDependencies")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services.bootstrap_health_server_dependencies",
                return_value=mock_deps,
            ) as mock_bootstrap,
        ):
            from bioetl.composition._services import get_health_server_dependencies

            result = get_health_server_dependencies()

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
        assert result is mock_deps


# =============================================================================
# Tests for get_metrics_service
# =============================================================================


@pytest.mark.unit
class TestGetMetricsService:
    """Tests for get_metrics_service function."""

    def test_calls_ensure_registrations_and_bootstrap(self) -> None:
        """Test that get_metrics_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="MetricsService")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services.bootstrap_metrics_service",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition._services import get_metrics_service

            result = get_metrics_service()

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
        assert result is mock_service


# =============================================================================
# Tests for get_adr_service
# =============================================================================


@pytest.mark.unit
class TestGetAdrService:
    """Tests for get_adr_service function."""

    def test_calls_ensure_registrations_and_bootstrap(self) -> None:
        """Test that get_adr_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock(name="AdrServicePort")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services.bootstrap_adr_service",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition._services import get_adr_service

            result = get_adr_service()

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
        assert result is mock_service


# =============================================================================
# Tests for get_quarantine_store
# =============================================================================


@pytest.mark.unit
class TestGetQuarantineStore:
    """Tests for get_quarantine_store function."""

    def test_calls_ensure_registrations_and_bootstrap_quarantine_port(self) -> None:
        """Test that get_quarantine_store calls _ensure_registrations and bootstrap_quarantine_port."""
        mock_port = MagicMock(name="QuarantinePort")

        with (
            patch("bioetl.composition._services._ensure_registrations") as mock_ensure,
            patch(
                "bioetl.composition._services.bootstrap_quarantine_port",
                return_value=mock_port,
            ) as mock_bootstrap,
        ):
            from bioetl.composition._services import get_quarantine_store

            result = get_quarantine_store("chembl_activity")

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
        assert result is mock_port

    def test_pipeline_param_is_accepted(self) -> None:
        """Test that pipeline parameter is accepted (context only)."""
        mock_port = MagicMock(name="QuarantinePort")

        with (
            patch("bioetl.composition._services._ensure_registrations"),
            patch(
                "bioetl.composition._services.bootstrap_quarantine_port",
                return_value=mock_port,
            ),
        ):
            from bioetl.composition._services import get_quarantine_store

            # Should not raise regardless of pipeline name
            result = get_quarantine_store("any_pipeline")
            assert result is mock_port
