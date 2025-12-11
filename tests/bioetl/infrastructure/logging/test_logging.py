"""Tests for logging and progress reporting components."""

from unittest.mock import patch

from bioetl.infrastructure.logging.factories import create_progress_reporter
from bioetl.infrastructure.logging.impl.progress_reporter import (
    TqdmProgressReporterImpl,
)
from bioetl.infrastructure.observability.adapters import StructuredLoggerImpl
from bioetl.infrastructure.observability.factories import create_logging_port


def test_create_logging_port():
    """Test canonical logger factory from observability layer."""
    logger = create_logging_port()
    assert isinstance(logger, StructuredLoggerImpl)


def test_create_progress_reporter():
    """Test progress reporter factory."""
    reporter = create_progress_reporter()
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
