"""Factories for structured logging adapters and progress reporters.

Naming convention:
- create_*() - creates a new instance each time
- get_*() - returns singleton/cached instance
- build_*() - uses builder pattern
"""

import warnings

import structlog

from bioetl.domain.observability import LoggingPortABC, ProgressReporterABC
from bioetl.infrastructure.logging.impl.progress_reporter import (
    TqdmProgressReporterImpl,
)
from bioetl.infrastructure.observability import factories as observability_factories
from bioetl.infrastructure.observability.adapters import StructuredLoggerImpl


def create_logger() -> LoggingPortABC:
    """Create a new configured structured logger instance."""
    observability_factories._configure_structlog()
    return StructuredLoggerImpl(logger=structlog.get_logger())


def create_progress_reporter() -> ProgressReporterABC:
    """Create a new progress reporter instance (tqdm)."""
    return TqdmProgressReporterImpl()


# ---------------------------------------------------------------------------
# Deprecated aliases for backward compatibility
# ---------------------------------------------------------------------------


def default_logger() -> LoggingPortABC:
    """DEPRECATED: Use create_logger() instead."""
    warnings.warn(
        "default_logger is deprecated, use create_logger instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_logger()


def default_progress_reporter() -> ProgressReporterABC:
    """DEPRECATED: Use create_progress_reporter() instead."""
    warnings.warn(
        "default_progress_reporter is deprecated, use create_progress_reporter instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_progress_reporter()
