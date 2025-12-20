"""DEPRECATED: This module has been moved to bioetl.composition.factories.data_sources.

This module provides backwards-compatible re-exports with deprecation warnings.
Update your imports to use bioetl.composition.factories.data_sources instead.
"""

import warnings

from bioetl.composition.factories.data_sources import DataSourceFactory

warnings.warn(
    "bioetl.infrastructure.factories.data_sources is deprecated. "
    "Import from bioetl.composition.factories.data_sources instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["DataSourceFactory"]
