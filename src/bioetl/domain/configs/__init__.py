"""Backward-compatibility shim — use ``bioetl.domain.config`` instead.

All classes have been moved to ``bioetl.domain.config.base_provider``.
This re-export ensures existing ``from bioetl.domain.configs import ...``
statements keep working.
"""

from bioetl.domain.config.base_provider import (
    BaseClientConfig,
    BaseProviderConfig,
    RateLimitConfig,
)

__all__ = [
    "BaseClientConfig",
    "BaseProviderConfig",
    "RateLimitConfig",
]
