"""Factories for transform infrastructure components."""

from bioetl.domain.transform.contracts import (
    HasherABC,
    HashServiceABC,
    NormalizationConfigProvider,
    NormalizationServiceABC,
)
from bioetl.domain.transform.hash_service import HashServiceImpl
from bioetl.infrastructure.transform.impl.hasher import HasherImpl
from bioetl.infrastructure.transform.impl.normalization_service_impl import (
    NormalizationServiceImpl,
)


def default_hasher() -> HasherABC:
    """Создает дефолтную реализацию Hasher."""

    return HasherImpl()


def default_hash_service() -> HashServiceABC:
    """Создает дефолтный HashService."""

    return HashServiceImpl(hasher=default_hasher())


def default_normalization_service(
    config: NormalizationConfigProvider,
) -> NormalizationServiceABC:
    """Создает сервис нормализации по умолчанию."""

    return NormalizationServiceImpl(config)


__all__ = ["default_hasher", "default_hash_service", "default_normalization_service"]
