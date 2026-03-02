"""Standardized CLI exit codes for BioETL.

Exit codes follow Unix conventions and sysexits.h standards:
- 0: Success (EX_OK)
- 1: General errors (EX_FAIL)
- 64-78: Reserved for standard exit codes

Custom BioETL codes (80-99) for specific scenarios.

References:
- BSD sysexits.h: https://man.freebsd.org/cgi/man.cgi?query=sysexits
- POSIX: https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Standardized exit codes for CLI commands.

    Follows Unix conventions with custom BioETL-specific codes.
    """

    # Success
    OK = 0  # Successful execution

    # General errors (1-63 reserved)
    FAIL = 1  # Unspecified error

    # Standard sysexits.h codes (64-78)
    EX_USAGE = 64  # Command line usage error
    EX_DATAERR = 65  # Data format error
    EX_NOINPUT = 66  # Cannot open input
    EX_NOUSER = 67  # Addressee unknown
    EX_NOHOST = 68  # Host name unknown
    EX_UNAVAILABLE = 69  # Service unavailable
    EX_SOFTWARE = 70  # Internal software error
    EX_OSERR = 71  # System error (e.g., can't fork)
    EX_OSFILE = 72  # Critical OS file missing
    EX_CANTCREAT = 73  # Can't create output file
    EX_IOERR = 74  # Input/output error
    EX_TEMPFAIL = 75  # Temporary failure; user can retry
    EX_PROTOCOL = 76  # Remote error in protocol
    EX_NOPERM = 77  # Permission denied
    EX_CONFIG = 78  # Configuration error

    # BioETL-specific codes (80-99)
    CONFIG_ERROR = 80  # Pipeline configuration error
    INIT_ERROR = 81  # Initialization failure
    PIPELINE_ERROR = 82  # Pipeline execution error
    DATA_QUALITY_ERROR = 83  # Data quality threshold exceeded
    LOCK_ERROR = 84  # Lock acquisition/validation failure
    STORAGE_ERROR = 85  # Storage operation failure
    NETWORK_ERROR = 86  # Network/API error
    CHECKPOINT_ERROR = 87  # Checkpoint save/load failure

    # Signal-related (128 + signal number)
    SIGINT = 130  # Interrupted by SIGINT (Ctrl+C) [128 + 2]
    SIGTERM = 143  # Terminated by SIGTERM [128 + 15]


# Mapping of exception types to exit codes
# Used by CLI error handlers to determine appropriate exit codes
EXCEPTION_EXIT_CODES: dict[str, ExitCode] = {
    # Critical errors
    "CriticalError": ExitCode.FAIL,
    "InfrastructureError": ExitCode.STORAGE_ERROR,
    "LockAcquisitionError": ExitCode.LOCK_ERROR,
    "LockLostError": ExitCode.LOCK_ERROR,
    "StorageError": ExitCode.STORAGE_ERROR,
    # Configuration errors
    "ValueError": ExitCode.CONFIG_ERROR,
    "FileNotFoundError": ExitCode.EX_NOINPUT,
    "ConfigValidationError": ExitCode.CONFIG_ERROR,
    # Data quality errors
    "DataQualityError": ExitCode.DATA_QUALITY_ERROR,
    "DataQualityThresholdError": ExitCode.DATA_QUALITY_ERROR,
    "SchemaViolationError": ExitCode.DATA_QUALITY_ERROR,
    # Network errors
    "NetworkError": ExitCode.NETWORK_ERROR,
    "RateLimitError": ExitCode.NETWORK_ERROR,
    "ApiError": ExitCode.NETWORK_ERROR,
    "CircuitBreakerOpenError": ExitCode.NETWORK_ERROR,
    # Recoverable errors (temporary failures)
    "RecoverableError": ExitCode.EX_TEMPFAIL,
    "RetryExhaustedError": ExitCode.EX_TEMPFAIL,
    # Shutdown
    "PipelineShutdownError": ExitCode.SIGINT,
    "KeyboardInterrupt": ExitCode.SIGINT,
}


def get_exit_code_for_exception(exc: BaseException) -> ExitCode:
    """Get the appropriate exit code for an exception.

    Args:
        exc: The exception to get exit code for.

    Returns:
        The appropriate ExitCode, defaulting to FAIL for unknown exceptions.

    """
    exc_type_name = type(exc).__name__

    # Check direct mapping first
    if exc_type_name in EXCEPTION_EXIT_CODES:
        return EXCEPTION_EXIT_CODES[exc_type_name]

    # Check MRO for parent class mappings
    for base_class in type(exc).__mro__:
        base_name = base_class.__name__
        if base_name in EXCEPTION_EXIT_CODES:
            return EXCEPTION_EXIT_CODES[base_name]

    return ExitCode.FAIL


__all__ = [
    "EXCEPTION_EXIT_CODES",
    "ExitCode",
    "get_exit_code_for_exception",
]
