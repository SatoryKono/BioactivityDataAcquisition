"""Factory functions for transform services."""

from typing import Callable

from bioetl.domain.transform.contracts import (
    HashServiceABC,
    IndexGeneratorABC,
    TimestampProviderABC,
)
from bioetl.domain.transform.transformers import (
    DatabaseVersionTransformerImpl,
    FulldateTransformerImpl,
    HashColumnsTransformerImpl,
    IndexColumnTransformerImpl,
    TransformerABC,
    TransformerChainImpl,
)

__all__ = ["default_post_transformer"]


def default_post_transformer(
    *,
    hash_service: HashServiceABC,
    index_generator: IndexGeneratorABC,
    timestamp_provider: TimestampProviderABC,
    business_key_fields: list[str] | None,
    version_provider: Callable[[], str | None] | None = None,
) -> TransformerABC:
    """Create a default chain of post-transformers.

    Args:
        hash_service: Сервис для вычисления хешей.
        index_generator: Генератор последовательных индексов.
        timestamp_provider: Провайдер временных меток.
        business_key_fields: Поля для хеширования бизнес-ключа.
        version_provider: Опциональный провайдер версии БД.

    Returns:
        Цепочка трансформеров для пост-обработки данных.
    """
    provider = version_provider or (lambda: "unknown")
    return TransformerChainImpl(
        [
            HashColumnsTransformerImpl(
                hash_service=hash_service, business_key_fields=business_key_fields
            ),
            IndexColumnTransformerImpl(index_generator=index_generator),
            DatabaseVersionTransformerImpl(database_version_provider=provider),
            FulldateTransformerImpl(timestamp_provider=timestamp_provider),
        ]
    )
