"""Factories for transform infrastructure components."""

from __future__ import annotations

from datetime import datetime
import warnings

from bioetl.domain.transform.contracts import (
    HasherABC,
    HashServiceABC,
    IndexGeneratorABC,
    NormalizationConfigProviderProtocol,
    NormalizationServiceABC,
    TimestampProviderABC,
)
from bioetl.infrastructure.transform.impl.default_normalization_transformer_impl import (  # noqa: E501
    DefaultNormalizationTransformerImpl,
)
from bioetl.infrastructure.transform.impl.hash_service import Blake2bHashService
from bioetl.infrastructure.transform.impl.hasher import HasherImpl
from bioetl.infrastructure.transform.impl.index_generator import (
    SequentialIndexGenerator,
)
from bioetl.infrastructure.transform.impl.timestamp_provider import (
    DeterministicTimestampProvider,
)


def default_hasher() -> HasherABC:
    """Create default Hasher implementation."""
    return HasherImpl()


def default_hash_service(hasher: HasherABC | None = None) -> HashServiceABC:
    """Create default HashService (Blake2b-based).

    Args:
        hasher: Optional custom hasher. Uses default if not provided.

    Returns:
        Stateless hash service for computing row and business key hashes.
    """
    return Blake2bHashService(hasher=hasher or default_hasher())


def default_timestamp_provider(
    fixed_time: datetime | None = None,
) -> TimestampProviderABC:
    """Create default timestamp provider.

    Args:
        fixed_time: Optional fixed timestamp. Uses current time if not provided.

    Returns:
        Deterministic timestamp provider for extraction timestamps.
    """
    return DeterministicTimestampProvider(fixed_time=fixed_time)


def default_index_generator(start: int = 0) -> IndexGeneratorABC:
    """Create default index generator.

    Args:
        start: Starting index value (default 0).

    Returns:
        Sequential index generator for row indexing.
    """
    return SequentialIndexGenerator(start=start)


def default_normalization_service(
    config: NormalizationConfigProviderProtocol,
) -> NormalizationServiceABC:
    """Create default normalization service."""
    return DefaultNormalizationTransformerImpl(config)


def default_chembl_normalization_service(
    config: NormalizationConfigProviderProtocol,
) -> NormalizationServiceABC:
    """Create ChEMBL normalization service.

    DEPRECATED: Use default_normalization_service with appropriate parameters.
    """
    warnings.warn(
        "default_chembl_normalization_service is deprecated. "
        "Use default_normalization_service or DefaultNormalizationTransformerImpl "
        "with empty_value=None, serialize_array_in_series=False instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return DefaultNormalizationTransformerImpl(
        config,
        empty_value=None,
        support_base_model=True,
        serialize_array_in_series=False,
    )


__all__ = [
    "default_hasher",
    "default_hash_service",
    "default_timestamp_provider",
    "default_index_generator",
    "default_normalization_service",
    "default_chembl_normalization_service",
]
