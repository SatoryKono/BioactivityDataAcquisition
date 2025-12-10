"""Transform infrastructure layer."""

from bioetl.infrastructure.transform.factories import (
    # New naming convention
    create_hash_service,
    create_hasher,
    create_index_generator,
    create_normalization_service,
    create_timestamp_provider,
    # Deprecated aliases for backward compatibility
    default_hash_service,
    default_hasher,
    default_index_generator,
    default_normalization_service,
    default_timestamp_provider,
)

__all__ = [
    # New naming convention
    "create_hasher",
    "create_hash_service",
    "create_timestamp_provider",
    "create_index_generator",
    "create_normalization_service",
    # Deprecated aliases
    "default_hasher",
    "default_hash_service",
    "default_timestamp_provider",
    "default_index_generator",
    "default_normalization_service",
]
