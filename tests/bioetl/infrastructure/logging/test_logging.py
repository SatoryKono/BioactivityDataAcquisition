"""
Tests for logging and progress reporting components.
"""

import warnings
from unittest.mock import patch

from bioetl.infrastructure.logging.factories import (
    create_logger,
    default_logger,
    default_progress_reporter,
)
from bioetl.infrastructure.logging.impl.progress_reporter import (
    TqdmProgressReporterImpl,
)
from bioetl.infrastructure.observability.adapters import StructuredLoggerImpl
from bioetl.infrastructure.observability.factories import create_logging_port


def test_create_logging_port():
    """Test canonical logger factory from observability layer."""
    logger = create_logging_port()
    assert isinstance(logger, StructuredLoggerImpl)


def test_create_logger_deprecated():
    """Test that create_logger emits deprecation warning and delegates."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        logger = create_logger()
        assert isinstance(logger, StructuredLoggerImpl)
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "v1.6" in str(w[0].message)
        assert "create_logging_port" in str(w[0].message)


def test_default_logger_deprecated():
    """Test that default_logger emits deprecation warning and delegates."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        logger = default_logger()
        assert isinstance(logger, StructuredLoggerImpl)
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "v1.6" in str(w[0].message)
        assert "create_logging_port" in str(w[0].message)


def test_default_progress_reporter():
    """Test default progress reporter factory."""
    reporter = default_progress_reporter()
    assert isinstance(reporter, TqdmProgressReporterImpl)


def test_structured_logger():
    """Test StructuredLoggerImpl basic functionality."""
    logger = StructuredLoggerImpl()
    # Mock the internal structlog logger if possible, or just test api
    # StructuredLoggerImpl usually wraps structlog.get_logger()

    # Test binding
    bound = logger.apply_bind(key="value")
    assert isinstance(bound, StructuredLoggerImpl)
    # Check if context is preserved (implementation detail)

    # Test methods (should not raise)
    logger.info("test info", extra="data")
    logger.error("test error", error=ValueError("x"))
    logger.warning("test warning")
    logger.debug("test debug")


def test_progress_reporter():
    """Test TqdmProgressReporterImpl functionality."""
    reporter = TqdmProgressReporterImpl()

    # Mock tqdm
    with patch(
        "bioetl.infrastructure.logging.impl.progress_reporter.tqdm"
    ) as mock_tqdm:
        # Test create_bar
        with reporter.create_bar(total=100, desc="test") as progress_bar:
            assert progress_bar is not None

            # Test update
            reporter.apply_update(10)

        mock_tqdm.assert_called()
