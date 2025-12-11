"""DEPRECATED: Import from bioetl.application.files.csv_record_source instead.

This module is a backward compatibility shim and will be removed in v2.0.
CSV record sources have been moved to the application layer.

Migration guide: docs/migration/v2.0-import-changes.md
"""

import warnings

warnings.warn(
    "Importing from bioetl.infrastructure.files.csv_record_source is deprecated. "
    "Use bioetl.application.files.csv_record_source instead. "
    "This module will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export CSV record source implementations for backward compatibility
from bioetl.application.files.csv_record_source import (  # noqa: E402, F401
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)

__all__ = [
    "CsvRecordSourceImpl",
    "IdListRecordSourceImpl",
]
