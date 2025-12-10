"""Factories for transform infrastructure components."""

import warnings

from bioetl.domain.transform.contracts import (
    HasherABC,
    HashServiceABC,
    NormalizationConfigProviderProtocol,
    NormalizationServiceABC,
)
from bioetl.domain.transform.hash_service import HashService
from bioetl.infrastructure.transform.impl.default_normalization_transformer_impl import (
    DefaultNormalizationTransformerImpl,
)
from bioetl.infrastructure.transform.impl.hasher import HasherImpl


def default_hasher() -> HasherABC:
    """Create default Hasher implementation."""
    return HasherImpl()


def default_hash_service() -> HashServiceABC:
    """Create default HashService."""
    return HashService(hasher=default_hasher())


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
    "default_normalization_service",
    "default_chembl_normalization_service",
]
