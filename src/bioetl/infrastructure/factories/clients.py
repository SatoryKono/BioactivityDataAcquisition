"""DEPRECATED: This module has been moved to bioetl.composition.factories.clients.

This module provides backwards-compatible re-exports with deprecation warnings.
Update your imports to use bioetl.composition.factories.clients instead.
"""

import warnings

from bioetl.composition.factories.clients import (
    create_redis_client,
    get_aws_credentials,
)

warnings.warn(
    "bioetl.infrastructure.factories.clients is deprecated. "
    "Import from bioetl.composition.factories.clients instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["create_redis_client", "get_aws_credentials"]
