from unittest.mock import patch
from bioetl.logging.factories import default_logger, default_progress_reporter
from bioetl.logging.impl.unified_logger import UnifiedLoggerImpl
from bioetl.logging.impl.progress_reporter import TqdmProgressReporterImpl


def test_default_logger():
    with patch("bioetl.logging.factories.structlog"):
        logger = default_logger()
        assert isinstance(logger, UnifiedLoggerImpl)


def test_default_progress_reporter():
    reporter = default_progress_reporter()
    assert isinstance(reporter, TqdmProgressReporterImpl)


def test_unified_logger():
    logger = UnifiedLoggerImpl()
    # Mock the internal structlog logger if possible, or just test api
    # UnifiedLoggerImpl usually wraps structlog.get_logger()

    # Test binding
    bound = logger.bind(key="value")
    assert isinstance(bound, UnifiedLoggerImpl)
    # Check if context is preserved (implementation detail)

    # Test methods (should not raise)
    logger.info("test info", extra="data")
    logger.error("test error", error=ValueError("x"))
    logger.warning("test warning")
    logger.debug("test debug")


def test_progress_reporter():
    reporter = TqdmProgressReporterImpl()

    # Mock tqdm
    with patch("bioetl.logging.impl.progress_reporter.tqdm") as mock_tqdm:
        # Test create_bar
        with reporter.create_bar(total=100, desc="test") as bar:
            assert bar is not None

            # Test update
            reporter.update(10)

        mock_tqdm.assert_called()
