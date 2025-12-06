from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.logging.impl.unified_logger import UnifiedLoggerImpl


@pytest.fixture
def mock_structlog():
    return MagicMock()

def test_logger_initialization_default():
    logger = UnifiedLoggerImpl()
    assert logger._logger is not None

def test_logger_initialization_with_instance(mock_structlog):
    logger = UnifiedLoggerImpl(mock_structlog)
    assert logger._logger == mock_structlog

def test_log_methods(mock_structlog):
    logger = UnifiedLoggerImpl(mock_structlog)
    
    logger.info("info msg", key="value")
    mock_structlog.info.assert_called_once_with("info msg", key="value")
    
    logger.error("error msg", error="e")
    mock_structlog.error.assert_called_once_with("error msg", error="e")
    
    logger.debug("debug msg")
    mock_structlog.debug.assert_called_once_with("debug msg")
    
    logger.warning("warn msg")
    mock_structlog.warning.assert_called_once_with("warn msg")

def test_bind(mock_structlog):
    # Arrange
    bound_mock = MagicMock()
    mock_structlog.bind.return_value = bound_mock
    logger = UnifiedLoggerImpl(mock_structlog)
    
    # Act
    new_logger = logger.bind(ctx_key="ctx_val")
    
    # Assert
    assert isinstance(new_logger, UnifiedLoggerImpl)
    assert new_logger._logger == bound_mock
    mock_structlog.bind.assert_called_once_with(ctx_key="ctx_val")
