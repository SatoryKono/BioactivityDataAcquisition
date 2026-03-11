"""Unit tests for PostrunMetadataVersionResolver.

Tests Delta table version resolution: ImportError (missing deltalake),
DeltaError, TableNotFoundError, allowlisted errors, strict vs warning mode,
and successful resolution paths.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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
def resolver(
    mock_logger: MagicMock, mock_runtime: MagicMock
) -> PostrunMetadataVersionResolver:
    """Create PostrunMetadataVersionResolver in warning mode."""
    return PostrunMetadataVersionResolver(
        logger=mock_logger,
        runtime=mock_runtime,
        warning_allowlist=(RuntimeError, OSError),
    )


@pytest.fixture
def strict_resolver(
    mock_logger: MagicMock, strict_runtime: MagicMock
) -> PostrunMetadataVersionResolver:
    """Create PostrunMetadataVersionResolver in strict mode."""
    return PostrunMetadataVersionResolver(
        logger=mock_logger,
        runtime=strict_runtime,
        warning_allowlist=(RuntimeError, OSError),
    )


# ---------------------------------------------------------------------------
# Tests: Successful Resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPostrunMetadataVersionResolverSuccess:
    """Tests for successful Delta version resolution."""

    def test_resolve_returns_version_integer(
        self, resolver: PostrunMetadataVersionResolver
    ) -> None:
        """Test that resolve_delta_version returns an integer on success."""
        mock_delta_table = MagicMock()
        mock_delta_table.version.return_value = 42

        with patch.dict(
            "sys.modules",
            {
                "deltalake": MagicMock(
                    DeltaTable=MagicMock(return_value=mock_delta_table)
                ),
                "deltalake.exceptions": MagicMock(
                    DeltaError=Exception, TableNotFoundError=Exception
                ),
            },
        ):
            result = resolver.resolve_delta_version("/path/to/table", layer="silver")

        assert result == 42

    def test_resolve_returns_version_zero(
        self, resolver: PostrunMetadataVersionResolver
    ) -> None:
        """Test that version 0 (first commit) is returned correctly."""
        mock_delta_table = MagicMock()
        mock_delta_table.version.return_value = 0

        with patch.dict(
            "sys.modules",
            {
                "deltalake": MagicMock(
                    DeltaTable=MagicMock(return_value=mock_delta_table)
                ),
                "deltalake.exceptions": MagicMock(
                    DeltaError=Exception, TableNotFoundError=Exception
                ),
            },
        ):
            result = resolver.resolve_delta_version("/path/to/table", layer="gold")

        assert result == 0


# ---------------------------------------------------------------------------
# Tests: ImportError (missing deltalake dependency)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPostrunMetadataVersionResolverImportError:
    """Tests for handling missing deltalake dependency."""

    def test_import_error_returns_none_in_warning_mode(
        self,
        resolver: PostrunMetadataVersionResolver,
        mock_logger: MagicMock,
    ) -> None:
        """Test that missing deltalake returns None in warning mode."""
        with patch.dict("sys.modules", {"deltalake": None}):
            result = resolver.resolve_delta_version("/path/table", layer="silver")

        assert result is None

    def test_import_error_logs_warning_in_warning_mode(
        self,
        resolver: PostrunMetadataVersionResolver,
        mock_logger: MagicMock,
    ) -> None:
        """Test that ImportError emits a warning in warning mode."""
        with patch.dict("sys.modules", {"deltalake": None}):
            resolver.resolve_delta_version("/path/table", layer="silver")

        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["reason_code"] == "POSTRUN_DELTA_DEPENDENCY_MISSING_WARNING"
        assert call_kwargs.get("strict_mode") is False

    def test_import_error_includes_layer_in_log(
        self,
        resolver: PostrunMetadataVersionResolver,
        mock_logger: MagicMock,
    ) -> None:
        """Test that warning log includes layer and table_path."""
        with patch.dict("sys.modules", {"deltalake": None}):
            resolver.resolve_delta_version("/silver/path", layer="silver")

        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs.get("layer") == "silver"
        assert call_kwargs.get("table_path") == "/silver/path"

    def test_import_error_raises_in_strict_mode(
        self,
        strict_resolver: PostrunMetadataVersionResolver,
        mock_logger: MagicMock,
    ) -> None:
        """Test that missing deltalake raises in strict mode."""
        with patch.dict("sys.modules", {"deltalake": None}):
            with pytest.raises((ImportError, ModuleNotFoundError)):
                strict_resolver.resolve_delta_version("/path/table", layer="silver")

    def test_import_error_strict_mode_logs_error_with_strict_flag(
        self,
        strict_resolver: PostrunMetadataVersionResolver,
        mock_logger: MagicMock,
    ) -> None:
        """Test that strict mode logs error with strict_mode=True before raising."""
        with patch.dict("sys.modules", {"deltalake": None}):
            with pytest.raises((ImportError, ModuleNotFoundError)):
                strict_resolver.resolve_delta_version("/path/table", layer="gold")

        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs.get("strict_mode") is True
        assert call_kwargs["reason_code"] == "POSTRUN_DELTA_DEPENDENCY_MISSING_STRICT"


# ---------------------------------------------------------------------------
# Tests: DeltaError / TableNotFoundError
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPostrunMetadataVersionResolverDeltaErrors:
    """Tests for DeltaError and TableNotFoundError handling."""

    def _make_delta_module(
        self, *, raises: type[Exception]
    ) -> tuple[MagicMock, MagicMock]:
        """Create mock deltalake module that raises on DeltaTable construction."""
        mock_exceptions = MagicMock()
        # Make both DeltaError and TableNotFoundError real exception classes
        mock_exceptions.DeltaError = type("DeltaError", (Exception,), {})
        mock_exceptions.TableNotFoundError = type(
            "TableNotFoundError", (mock_exceptions.DeltaError,), {}
        )
        mock_delta = MagicMock()
        mock_delta.DeltaTable.side_effect = raises(
            mock_exceptions.DeltaError
            if raises is mock_exceptions.DeltaError
            else mock_exceptions.TableNotFoundError
        )
        mock_delta.exceptions = mock_exceptions
        return mock_delta, mock_exceptions

    def test_table_not_found_returns_none_in_warning_mode(
        self,
        resolver: PostrunMetadataVersionResolver,
        mock_logger: MagicMock,
    ) -> None:
        """Test that TableNotFoundError returns None in warning mode."""
        DeltaError = type("DeltaError", (Exception,), {})
        TableNotFoundError = type("TableNotFoundError", (DeltaError,), {})

        mock_delta = MagicMock()
        mock_delta.DeltaTable.side_effect = TableNotFoundError("not found")
        mock_delta.exceptions.DeltaError = DeltaError
        mock_delta.exceptions.TableNotFoundError = TableNotFoundError

        with patch.dict(
            "sys.modules",
            {
                "deltalake": mock_delta,
                "deltalake.exceptions": mock_delta.exceptions,
            },
        ):
            result = resolver.resolve_delta_version("/missing/table", layer="silver")

        assert result is None
        mock_logger.warning.assert_called_once()

    def test_delta_error_returns_none_in_warning_mode(
        self,
        resolver: PostrunMetadataVersionResolver,
        mock_logger: MagicMock,
    ) -> None:
        """Test that DeltaError returns None in warning mode."""
        DeltaError = type("DeltaError", (Exception,), {})
        TableNotFoundError = type("TableNotFoundError", (DeltaError,), {})

        mock_delta = MagicMock()
        mock_delta.DeltaTable.side_effect = DeltaError("delta failed")
        mock_delta.exceptions.DeltaError = DeltaError
        mock_delta.exceptions.TableNotFoundError = TableNotFoundError

        with patch.dict(
            "sys.modules",
            {
                "deltalake": mock_delta,
                "deltalake.exceptions": mock_delta.exceptions,
            },
        ):
            result = resolver.resolve_delta_version("/broken/table", layer="gold")

        assert result is None

    def test_table_not_found_warning_includes_reason_code(
        self,
        resolver: PostrunMetadataVersionResolver,
        mock_logger: MagicMock,
    ) -> None:
        """Test that TableNotFoundError warning log has correct reason_code."""
        DeltaError = type("DeltaError", (Exception,), {})
        TableNotFoundError = type("TableNotFoundError", (DeltaError,), {})

        mock_delta = MagicMock()
        mock_delta.DeltaTable.side_effect = TableNotFoundError("missing")
        mock_delta.exceptions.DeltaError = DeltaError
        mock_delta.exceptions.TableNotFoundError = TableNotFoundError

        with patch.dict(
            "sys.modules",
            {
                "deltalake": mock_delta,
                "deltalake.exceptions": mock_delta.exceptions,
            },
        ):
            resolver.resolve_delta_version("/path/table", layer="silver")

        call_kwargs = mock_logger.warning.call_args[1]
        assert (
            call_kwargs["reason_code"]
            == "POSTRUN_DELTA_TABLE_RESOLUTION_FAILED_WARNING"
        )


# ---------------------------------------------------------------------------
# Tests: Allowlisted Error (warning_allowlist catch)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPostrunMetadataVersionResolverAllowlistedErrors:
    """Tests for warning_allowlist-based error handling."""

    def test_allowlisted_error_returns_none_in_warning_mode(
        self,
        mock_logger: MagicMock,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that allowlisted OSError returns None in warning mode."""
        DeltaError = type("DeltaError", (Exception,), {})
        TableNotFoundError = type("TableNotFoundError", (DeltaError,), {})

        mock_delta = MagicMock()
        mock_delta.DeltaTable.side_effect = OSError("permission denied")
        mock_delta.exceptions.DeltaError = DeltaError
        mock_delta.exceptions.TableNotFoundError = TableNotFoundError

        resolver = PostrunMetadataVersionResolver(
            logger=mock_logger,
            runtime=mock_runtime,
            warning_allowlist=(OSError, RuntimeError),
        )

        with patch.dict(
            "sys.modules",
            {
                "deltalake": mock_delta,
                "deltalake.exceptions": mock_delta.exceptions,
            },
        ):
            result = resolver.resolve_delta_version("/path", layer="silver")

        assert result is None
        mock_logger.warning.assert_called_once()

    def test_allowlisted_error_warning_reason_code(
        self,
        mock_logger: MagicMock,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that allowlisted error uses POSTRUN_DELTA_VERSION_RESOLUTION_FAILED_WARNING."""
        DeltaError = type("DeltaError", (Exception,), {})
        TableNotFoundError = type("TableNotFoundError", (DeltaError,), {})

        mock_delta = MagicMock()
        mock_delta.DeltaTable.side_effect = OSError("io error")
        mock_delta.exceptions.DeltaError = DeltaError
        mock_delta.exceptions.TableNotFoundError = TableNotFoundError

        resolver = PostrunMetadataVersionResolver(
            logger=mock_logger,
            runtime=mock_runtime,
            warning_allowlist=(OSError,),
        )

        with patch.dict(
            "sys.modules",
            {
                "deltalake": mock_delta,
                "deltalake.exceptions": mock_delta.exceptions,
            },
        ):
            resolver.resolve_delta_version("/path", layer="gold")

        call_kwargs = mock_logger.warning.call_args[1]
        assert (
            call_kwargs["reason_code"]
            == "POSTRUN_DELTA_VERSION_RESOLUTION_FAILED_WARNING"
        )


# ---------------------------------------------------------------------------
# Tests: _is_strict_validation_enabled
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsStrictValidationEnabled:
    """Tests for _is_strict_validation_enabled private helper."""

    def test_returns_false_when_strict_false(self, mock_logger: MagicMock) -> None:
        """Test returns False when runtime.strict_validation is False."""
        runtime = MagicMock()
        runtime.strict_validation = False
        resolver = PostrunMetadataVersionResolver(
            logger=mock_logger,
            runtime=runtime,
            warning_allowlist=(),
        )
        assert resolver._is_strict_validation_enabled() is False

    def test_returns_true_when_strict_true(self, mock_logger: MagicMock) -> None:
        """Test returns True when runtime.strict_validation is True."""
        runtime = MagicMock()
        runtime.strict_validation = True
        resolver = PostrunMetadataVersionResolver(
            logger=mock_logger,
            runtime=runtime,
            warning_allowlist=(),
        )
        assert resolver._is_strict_validation_enabled() is True

    def test_returns_false_when_attribute_missing(self, mock_logger: MagicMock) -> None:
        """Test returns False when runtime lacks strict_validation attr."""
        runtime = object()
        resolver = PostrunMetadataVersionResolver(
            logger=mock_logger,
            runtime=runtime,
            warning_allowlist=(),
        )
        assert resolver._is_strict_validation_enabled() is False
