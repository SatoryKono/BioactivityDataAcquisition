"""Unit tests for PostrunMetadataVersionResolver.

Tests Delta table version resolution via injected StorageMaintenancePort:
successful resolution, error handling with strict/warning mode, and
allowlisted exception filtering.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.core.postrun.metadata_version_resolver import (
    PostrunMetadataVersionResolver,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def mock_runtime() -> MagicMock:
    """Create a mock runtime with strict_validation=False."""
    runtime = MagicMock()
    runtime.strict_validation = False
    return runtime


@pytest.fixture
def strict_runtime() -> MagicMock:
    """Create a mock runtime with strict_validation=True."""
    runtime = MagicMock()
    runtime.strict_validation = True
    return runtime


@pytest.fixture
def mock_storage() -> MagicMock:
    """Create a mock StorageMaintenancePort."""
    return MagicMock()


@pytest.fixture
def resolver(
    mock_logger: MagicMock, mock_runtime: MagicMock, mock_storage: MagicMock
) -> PostrunMetadataVersionResolver:
    """Create PostrunMetadataVersionResolver in warning mode."""
    return PostrunMetadataVersionResolver(
        logger=mock_logger,
        runtime=mock_runtime,
        storage=mock_storage,
        warning_allowlist=(RuntimeError, OSError),
    )


@pytest.fixture
def strict_resolver(
    mock_logger: MagicMock, strict_runtime: MagicMock, mock_storage: MagicMock
) -> PostrunMetadataVersionResolver:
    """Create PostrunMetadataVersionResolver in strict mode."""
    return PostrunMetadataVersionResolver(
        logger=mock_logger,
        runtime=strict_runtime,
        storage=mock_storage,
        warning_allowlist=(RuntimeError, OSError),
    )


# ---------------------------------------------------------------------------
# Tests: Successful Resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPostrunMetadataVersionResolverSuccess:
    """Tests for successful Delta version resolution."""

    def test_resolve_returns_version_integer(
        self,
        resolver: PostrunMetadataVersionResolver,
        mock_storage: MagicMock,
    ) -> None:
        """Test that resolve_delta_version returns an integer on success."""
        mock_storage.get_table_version.return_value = 42

        result = resolver.resolve_delta_version("/path/to/table", layer="silver")

        assert result == 42
        mock_storage.get_table_version.assert_called_once_with(
            "/path/to/table", layer="silver"
        )

    def test_resolve_returns_version_zero(
        self,
        resolver: PostrunMetadataVersionResolver,
        mock_storage: MagicMock,
    ) -> None:
        """Test that version 0 (first commit) is returned correctly."""
        mock_storage.get_table_version.return_value = 0

        result = resolver.resolve_delta_version("/path/to/table", layer="gold")

        assert result == 0

    def test_resolve_returns_none_when_table_missing(
        self,
        resolver: PostrunMetadataVersionResolver,
        mock_storage: MagicMock,
    ) -> None:
        """Test that None from port is passed through."""
        mock_storage.get_table_version.return_value = None

        result = resolver.resolve_delta_version("/missing/table", layer="silver")

        assert result is None


# ---------------------------------------------------------------------------
# Tests: Allowlisted Errors (warning vs strict mode)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPostrunMetadataVersionResolverAllowlistedErrors:
    """Tests for warning_allowlist-based error handling."""

    def test_core_postrun_metadata_version_resolver_141__a3cb225a(
        self,
        mock_logger: MagicMock,
        mock_runtime: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """Test that allowlisted OSError returns None in warning mode."""
        mock_storage.get_table_version.side_effect = OSError("permission denied")

        resolver = PostrunMetadataVersionResolver(
            logger=mock_logger,
            runtime=mock_runtime,
            storage=mock_storage,
            warning_allowlist=(OSError, RuntimeError),
        )

        result = resolver.resolve_delta_version("/path", layer="silver")

        assert result is None
        mock_logger.warning.assert_called_once()

    def test_allowlisted_error_warning_reason_code(
        self,
        mock_logger: MagicMock,
        mock_runtime: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """Test that allowlisted error uses correct reason_code."""
        mock_storage.get_table_version.side_effect = OSError("io error")

        resolver = PostrunMetadataVersionResolver(
            logger=mock_logger,
            runtime=mock_runtime,
            storage=mock_storage,
            warning_allowlist=(OSError,),
        )

        resolver.resolve_delta_version("/path", layer="gold")

        call_kwargs = mock_logger.warning.call_args[1]
        assert (
            call_kwargs["reason_code"]
            == "POSTRUN_DELTA_VERSION_RESOLUTION_FAILED_WARNING"
        )

    def test_allowlisted_error_warning_includes_layer(
        self,
        mock_logger: MagicMock,
        mock_runtime: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """Test that warning log includes layer and table_path."""
        mock_storage.get_table_version.side_effect = RuntimeError("fail")

        resolver = PostrunMetadataVersionResolver(
            logger=mock_logger,
            runtime=mock_runtime,
            storage=mock_storage,
            warning_allowlist=(RuntimeError,),
        )

        resolver.resolve_delta_version("/silver/path", layer="silver")

        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs.get("layer") == "silver"
        assert call_kwargs.get("table_path") == "/silver/path"

    def test_core_postrun_metadata_version_resolver_208__5f1f6127(
        self,
        strict_resolver: PostrunMetadataVersionResolver,
        mock_storage: MagicMock,
    ) -> None:
        """Test that allowlisted error raises in strict mode."""
        mock_storage.get_table_version.side_effect = OSError("strict fail")

        with pytest.raises(OSError, match="strict fail"):
            strict_resolver.resolve_delta_version("/path/table", layer="silver")

    def test_allowlisted_error_strict_mode_logs_error(
        self,
        mock_logger: MagicMock,
        strict_resolver: PostrunMetadataVersionResolver,
        mock_storage: MagicMock,
    ) -> None:
        """Test that strict mode logs error with strict_mode=True before raising."""
        mock_storage.get_table_version.side_effect = OSError("fail")

        with pytest.raises(OSError):
            strict_resolver.resolve_delta_version("/path/table", layer="gold")

        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs.get("strict_mode") is True
        assert (
            call_kwargs["reason_code"]
            == "POSTRUN_DELTA_VERSION_RESOLUTION_FAILED_STRICT"
        )

    def test_non_allowlisted_error_propagates(
        self,
        resolver: PostrunMetadataVersionResolver,
        mock_storage: MagicMock,
    ) -> None:
        """Test that errors NOT in allowlist propagate regardless of mode."""
        mock_storage.get_table_version.side_effect = ValueError("unexpected")

        with pytest.raises(ValueError, match="unexpected"):
            resolver.resolve_delta_version("/path", layer="silver")


# ---------------------------------------------------------------------------
# Tests: _is_strict_validation_enabled
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsStrictValidationEnabled:
    """Tests for _is_strict_validation_enabled private helper."""

    def test_returns_false_when_strict_false(
        self, mock_logger: MagicMock, mock_storage: MagicMock
    ) -> None:
        """Test returns False when runtime.strict_validation is False."""
        runtime = MagicMock()
        runtime.strict_validation = False
        resolver = PostrunMetadataVersionResolver(
            logger=mock_logger,
            runtime=runtime,
            storage=mock_storage,
            warning_allowlist=(),
        )
        assert resolver._is_strict_validation_enabled() is False

    def test_returns_true_when_strict_true(
        self, mock_logger: MagicMock, mock_storage: MagicMock
    ) -> None:
        """Test returns True when runtime.strict_validation is True."""
        runtime = MagicMock()
        runtime.strict_validation = True
        resolver = PostrunMetadataVersionResolver(
            logger=mock_logger,
            runtime=runtime,
            storage=mock_storage,
            warning_allowlist=(),
        )
        assert resolver._is_strict_validation_enabled() is True

    def test_validation_enabled__attribute_missing__12bed4a9(
        self, mock_logger: MagicMock, mock_storage: MagicMock
    ) -> None:
        """Test returns False when runtime lacks strict_validation attr."""
        runtime = object()
        resolver = PostrunMetadataVersionResolver(
            logger=mock_logger,
            runtime=runtime,
            storage=mock_storage,
            warning_allowlist=(),
        )
        assert resolver._is_strict_validation_enabled() is False
