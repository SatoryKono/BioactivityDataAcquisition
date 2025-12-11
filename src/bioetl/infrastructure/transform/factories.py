"""Factories for transform infrastructure components.

Naming convention:
- create_*() - creates a new instance each time
- get_*() - returns singleton/cached instance
- build_*() - uses builder pattern
"""

from __future__ import annotations

from datetime import datetime

from bioetl.domain.transform.contracts import (
    HasherABC,
    HashServiceABC,
    IndexGeneratorABC,
    NormalizationConfigProviderProtocol,
    NormalizationServiceABC,
    TimestampProviderABC,
)
from bioetl.infrastructure.transform.impl import (
    default_normalization_transformer_impl as norm_impl,
)
from bioetl.infrastructure.transform.impl.hash_service import Blake2bHashService
from bioetl.infrastructure.transform.impl.hasher import HasherImpl
from bioetl.infrastructure.transform.impl.index_generator import (
    SequentialIndexGenerator,
)
from bioetl.infrastructure.transform.impl.timestamp_provider import (
    DeterministicTimestampProvider,
)


def create_hasher() -> HasherABC:
    """Create a new Hasher instance."""
    return HasherImpl()


def create_hash_service(hasher: HasherABC | None = None) -> HashServiceABC:
    """Create a new HashService (Blake2b-based).

    Args:
        hasher: Optional custom hasher. Uses default if not provided.

    Returns:
        Stateless hash service for computing row and business key hashes.
    """
    return Blake2bHashService(hasher=hasher or create_hasher())


def create_timestamp_provider(
    fixed_time: datetime | None = None,
) -> TimestampProviderABC:
    """Create a new timestamp provider.

    Args:
        fixed_time: Optional fixed timestamp. Uses current time if not provided.

    Returns:
        Deterministic timestamp provider for extraction timestamps.
    """
    return DeterministicTimestampProvider(fixed_time=fixed_time)


def create_index_generator(start: int = 0) -> IndexGeneratorABC:
    """Create a new index generator.

    Args:
        start: Starting index value (default 0).

    Returns:
        Sequential index generator for row indexing.
    """
    return SequentialIndexGenerator(start=start)


def create_normalization_service(
    config: NormalizationConfigProviderProtocol,
) -> NormalizationServiceABC:
    """Create a new normalization service."""
    return norm_impl.NormalizationServiceImpl(config)


__all__ = [
    "create_hasher",
    "create_hash_service",
    "create_timestamp_provider",
    "create_index_generator",
    "create_normalization_service",
]
