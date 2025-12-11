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
        hash_service: Service for computing hashes.
        index_generator: Sequential index generator.
        timestamp_provider: Timestamp provider.
        business_key_fields: Fields for business key hashing.
        version_provider: Optional database version provider.

    Returns:
        Transformer chain for post-processing data.
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
