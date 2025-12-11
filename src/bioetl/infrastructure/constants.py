"""Constants for infrastructure layer.

DEPRECATED: This module is deprecated. Use infrastructure.settings instead.

All constants have been moved to:
    - infrastructure.settings.files for file operation constants
    - infrastructure.settings.http for HTTP-related constants
    - infrastructure.settings.metrics for Prometheus metric names

This module re-exports legacy constants for backward compatibility.
This module will be removed in v2.0.

Migration guide: docs/migration/v2.0-import-changes.md
"""

import warnings

warnings.warn(
    "Importing from bioetl.infrastructure.constants is deprecated. "
    "Use bioetl.infrastructure.settings.files instead. "
    "This module will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2,
)

from bioetl.infrastructure.settings.files import (  # noqa: E402
    CHECKSUM_CHUNK_SIZE,
    MAX_FILE_RETRIES,
    RETRY_DELAY_SEC,
)

__all__ = [
    "MAX_FILE_RETRIES",
    "RETRY_DELAY_SEC",
    "CHECKSUM_CHUNK_SIZE",
]
