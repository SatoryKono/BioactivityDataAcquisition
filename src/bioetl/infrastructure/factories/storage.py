"""DEPRECATED: This module has been moved to bioetl.composition.factories.storage_factory.

This module provides backwards-compatible re-exports with deprecation warnings.
Update your imports to use bioetl.composition.factories.storage_factory instead.
"""

import warnings

from bioetl.composition.factories.storage_factory import (
    StorageAdapter as _StorageAdapter,
)

warnings.warn(
    "bioetl.infrastructure.factories.storage is deprecated. "
    "Import from bioetl.composition.factories.storage_factory instead.",
    DeprecationWarning,
    stacklevel=2,
)


class StorageAdapter(_StorageAdapter):
    """DEPRECATED: Use bioetl.composition.factories.storage_factory.StorageAdapter."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "StorageAdapter from bioetl.infrastructure.factories.storage is deprecated. "
            "Import from bioetl.composition.factories.storage_factory instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


__all__ = ["StorageAdapter"]
