"""Factory functions for transform services."""

from bioetl.domain.transform.contracts import (
    NormalizationConfigProvider,
    NormalizationServiceABC,
)
from bioetl.domain.transform.impl import NormalizationServiceImpl

__all__ = ["default_normalization_service"]


def default_normalization_service(
    config: NormalizationConfigProvider,
) -> NormalizationServiceABC:
    """Create default normalization service implementation."""

    return NormalizationServiceImpl(config)
