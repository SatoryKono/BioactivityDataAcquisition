"""Factory functions for transform services."""

from typing import Callable

from bioetl.domain.transform.contracts import HashServiceABC
from bioetl.domain.transform.transformers import (
    DatabaseVersionTransformer,
    FulldateTransformer,
    HashColumnsTransformer,
    IndexColumnTransformer,
    TransformerABC,
    TransformerChain,
)

__all__ = ["default_post_transformer"]


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
