"""DEPRECATED: Factory modules have been moved to bioetl.composition.factories.

This module provides backwards-compatible re-exports with deprecation warnings.
Update your imports to use bioetl.composition.factories instead.

Migration guide:
    OLD: from bioetl.infrastructure.factories.storage import StorageAdapter
    NEW: from bioetl.composition.factories.storage_factory import StorageAdapter

    OLD: from bioetl.infrastructure.factories.storage_factory import StorageFactory, StorageContext
    NEW: from bioetl.composition.factories.storage_factory import StorageFactory, StorageContext

    OLD: from bioetl.infrastructure.factories.clients import create_redis_client, get_aws_credentials
    NEW: from bioetl.composition.factories.clients import create_redis_client, get_aws_credentials

    OLD: from bioetl.infrastructure.factories.data_sources import DataSourceFactory
    NEW: from bioetl.composition.factories.data_sources import DataSourceFactory
"""

import warnings

warnings.warn(
    "bioetl.infrastructure.factories is deprecated. "
    "Import from bioetl.composition.factories instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backwards compatibility
from bioetl.composition.factories.clients import (  # noqa: E402
    create_redis_client,
    get_aws_credentials,
)
from bioetl.composition.factories.data_sources import (  # noqa: E402
    DataSourceFactory,
)
from bioetl.composition.factories.storage_factory import (  # noqa: E402
    StorageAdapter,
    StorageContext,
    StorageFactory,
)

__all__ = [
    "DataSourceFactory",
    "StorageAdapter",
    "StorageContext",
    "StorageFactory",
    "create_redis_client",
    "get_aws_credentials",
]
