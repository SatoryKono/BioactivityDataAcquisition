"""Factory functions for transform services."""

from typing import Callable

from bioetl.domain.transform.contracts import (
    HasherABC,
    HashServiceABC,
    NormalizationConfigProvider,
    NormalizationServiceABC,
)
from bioetl.domain.transform.hash_service import HashServiceImpl
from bioetl.domain.transform.impl import NormalizationServiceImpl
from bioetl.domain.transform.impl.hasher import HasherImpl
from bioetl.domain.transform.transformers import (
    DatabaseVersionTransformer,
    FulldateTransformer,
    HashColumnsTransformer,
    IndexColumnTransformer,
    TransformerABC,
    TransformerChain,
)

__all__ = [
    "default_hasher",
    "default_hash_service",
    "default_normalization_service",
    "default_post_transformer",
]


def default_hasher() -> HasherABC:
    """Создает дефолтную реализацию Hasher."""

    return HasherImpl()


def default_hash_service() -> HashServiceABC:
    """Создает дефолтный HashService."""

    return HashServiceImpl()


def default_normalization_service(
    config: NormalizationConfigProvider,
) -> NormalizationServiceABC:
    """Create default normalization service implementation."""

    return NormalizationServiceImpl(config)


def default_post_transformer(
    *,
    hash_service: HashServiceABC,
    business_key_fields: list[str] | None,
    version_provider: Callable[[], str | None] | None = None,
) -> TransformerABC:
    """Create a default chain of post-transformers."""

    provider = version_provider or (lambda: "unknown")
    return TransformerChain(
        [
            HashColumnsTransformer(
                hash_service=hash_service, business_key_fields=business_key_fields
            ),
            IndexColumnTransformer(hash_service=hash_service),
            DatabaseVersionTransformer(
                hash_service=hash_service,
                database_version_provider=provider,
            ),
            FulldateTransformer(hash_service=hash_service),
        ]
    )
