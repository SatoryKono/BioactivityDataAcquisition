"""Factories for structured logging adapters and progress reporters.

Naming convention:
- create_*() - creates a new instance each time
- get_*() - returns singleton/cached instance
- build_*() - uses builder pattern

NOTE: Logging factories are consolidated in observability layer.
Use `bioetl.infrastructure.observability.factories.create_logging_port` as the
canonical factory. Functions here delegate to observability for backward compatibility.
"""

import warnings

from bioetl.domain.observability import LoggingPortABC, ProgressReporterABC
from bioetl.infrastructure.logging.impl.progress_reporter import (
    TqdmProgressReporterImpl,
)


def create_logger() -> LoggingPortABC:
    """Create structured logger. Delegates to observability layer.

    .. deprecated:: 1.6
        Use :func:`bioetl.infrastructure.observability.factories.create_logging_port`
        instead. Will be removed in v2.0.
    """
    warnings.warn(
        "create_logger is deprecated since v1.6, use "
        "bioetl.infrastructure.observability.factories.create_logging_port instead. "
        "Will be removed in v2.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    from bioetl.infrastructure.observability.factories import create_logging_port

    return create_logging_port()


def create_progress_reporter() -> ProgressReporterABC:
    """Create a new progress reporter instance (tqdm)."""
    return TqdmProgressReporterImpl()


# ---------------------------------------------------------------------------
# Deprecated aliases for backward compatibility
# ---------------------------------------------------------------------------


def default_logger() -> LoggingPortABC:
    """DEPRECATED: Use create_logging_port() from observability.factories instead.

    .. deprecated:: 1.6
        Use :func:`bioetl.infrastructure.observability.factories.create_logging_port`
        instead. Will be removed in v2.0.
    """
    warnings.warn(
        "default_logger is deprecated since v1.6, use "
        "bioetl.infrastructure.observability.factories.create_logging_port instead. "
        "Will be removed in v2.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    from bioetl.infrastructure.observability.factories import create_logging_port

    return create_logging_port()


def default_progress_reporter() -> ProgressReporterABC:
    """DEPRECATED: Use create_progress_reporter() instead."""
    warnings.warn(
        "default_progress_reporter is deprecated, use create_progress_reporter instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_progress_reporter()
