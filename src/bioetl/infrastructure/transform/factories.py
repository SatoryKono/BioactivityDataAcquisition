"""Factories for transform infrastructure components."""

from bioetl.domain.transform.contracts import (
    BaseNormalizationServiceABC,
    HasherABC,
    HashServiceABC,
    NormalizationConfigProviderProtocol,
    NormalizationServiceABC,
)
from bioetl.domain.transform.hash_service import HashService
from bioetl.infrastructure.transform.impl.base_normalizer import (
    BaseNormalizationServiceImpl,
)
from bioetl.infrastructure.transform.impl.chembl_normalization_service_impl import (
    ChemblNormalizationServiceImpl,
)
from bioetl.infrastructure.transform.impl.hasher import HasherImpl
from bioetl.infrastructure.transform.impl.default_normalization_transformer_impl import (
    DefaultNormalizationTransformerImpl,
)


def default_hasher() -> HasherABC:
    """Создает дефолтную реализацию Hasher."""

    return HasherImpl()


def default_hash_service() -> HashServiceABC:
    """Создает дефолтный HashService."""

    return HashService(hasher=default_hasher())


def default_base_normalization_service(
    config: NormalizationConfigProviderProtocol,
) -> BaseNormalizationServiceABC:
    """Создает базовый сервис нормализации."""

    return BaseNormalizationServiceImpl(config)


def default_normalization_service(
    config: NormalizationConfigProviderProtocol,
) -> NormalizationServiceABC:
    """Создает сервис нормализации по умолчанию."""

    return DefaultNormalizationTransformerImpl(config)


def default_chembl_normalization_service(
    config: NormalizationConfigProviderProtocol,
) -> NormalizationServiceABC:
    """Создает сервис нормализации ChEMBL."""

    return ChemblNormalizationServiceImpl(config)


__all__ = [
    "default_hasher",
    "default_hash_service",
    "default_base_normalization_service",
    "default_normalization_service",
    "default_chembl_normalization_service",
]
