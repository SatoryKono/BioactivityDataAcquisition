"""File operation utilities (infrastructure layer).

This module provides file-related infrastructure components including:
- Atomic file operations
- Checksum calculation
- Path resolution
"""

from bioetl.infrastructure.files.atomic import AtomicFileOperation
from bioetl.infrastructure.files.checksum import (
    compute_file_sha256,
    compute_files_sha256,
)
from bioetl.infrastructure.files.path_resolver import (
    CONFIGS_ROOT_ENV,
    DEFAULT_CONFIGS_ROOT,
    PathResolver,
    create_config_resolver,
    create_output_resolver,
)

__all__ = [
    # Atomic operations
    "AtomicFileOperation",
    # Checksum
    "compute_file_sha256",
    "compute_files_sha256",
    # Path resolution
    "PathResolver",
    "CONFIGS_ROOT_ENV",
    "DEFAULT_CONFIGS_ROOT",
    "create_config_resolver",
    "create_output_resolver",
]
