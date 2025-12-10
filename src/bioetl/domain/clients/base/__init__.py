"""Base contracts for data source clients.

Note:
    ``ResponseParserABC`` is deprecated. Use ``ResponseParserPortABC``
    from ``bioetl.domain.ports.parsing`` instead.
"""

import warnings

from bioetl.domain.clients.base.contracts import (
    CacheABC,
    PaginatorABC,
    RateLimiterABC,
    RequestBuilderABC,
    RetryPolicyABC,
    SecretProviderABC,
)

__all__ = [
    "CacheABC",
    "PaginatorABC",
    "RateLimiterABC",
    "RequestBuilderABC",
    "ResponseParserABC",  # Deprecated: re-exported for backward compatibility
    "RetryPolicyABC",
    "SecretProviderABC",
]


def __getattr__(name: str) -> type:
    """Lazy import with deprecation warning for ResponseParserABC."""
    if name == "ResponseParserABC":
        from bioetl.domain.ports.parsing import ResponseParserPortABC

        warnings.warn(
            "ResponseParserABC is deprecated. "
            "Use ResponseParserPortABC from bioetl.domain.ports.parsing instead. "
            "See migration guide in bioetl.domain.ports.parsing module docstring.",
            DeprecationWarning,
            stacklevel=2,
        )
        return ResponseParserPortABC
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
