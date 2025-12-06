"""Factories for transform infrastructure components."""

from bioetl.domain.transform.contracts import (
    NormalizationConfigProvider,
    NormalizationServiceABC,
)
from bioetl.infrastructure.transform.impl.normalization_service_impl import (
    NormalizationServiceImpl,
)


def default_normalization_service(
    config: NormalizationConfigProvider,
) -> NormalizationServiceABC:
    """Создает сервис нормализации по умолчанию."""

    return NormalizationServiceImpl(config)


__all__ = ["default_normalization_service"]
