"""DEPRECATED: This module has been moved to bioetl.composition.factories.storage_factory.

This module provides backwards-compatible re-exports with deprecation warnings.
Update your imports to use bioetl.composition.factories.storage_factory instead.
"""

import warnings

from bioetl.composition.factories.storage_factory import (
    StorageAdapter,
    StorageContext,
    StorageFactory,
)

warnings.warn(
    "bioetl.infrastructure.factories.storage_factory is deprecated. "
    "Import from bioetl.composition.factories.storage_factory instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["StorageAdapter", "StorageContext", "StorageFactory"]
