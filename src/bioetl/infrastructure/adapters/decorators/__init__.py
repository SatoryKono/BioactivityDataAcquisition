"""Data Source Decorators.

Implements the Decorator Pattern for DataSourcePort to add cross-cutting concerns.
These decorators decouple resilience logic (retry, circuit breaker) from adapter
implementations, improving testability and flexibility.

Usage:
    from bioetl.infrastructure.adapters.decorators import (
        RetryingDataSourceDecorator,
        CircuitBreakerDataSourceDecorator,
    )

    # Compose decorators for full resilience
    base_adapter = ChemblAdapter(...)
    with_retry = RetryingDataSourceDecorator(
        data_source=base_adapter,
        retry_config=retry_config,
    )
    fully_protected = CircuitBreakerDataSourceDecorator(
        data_source=with_retry,
        circuit_breaker=circuit_breaker,
    )

    # Or use the helper function
    protected = wrap_with_resilience(
        data_source=base_adapter,
        retry_config=retry_config,
        circuit_breaker=circuit_breaker,
    )

Decorator Order:
    The recommended order is:
    1. CircuitBreakerDataSourceDecorator (outermost)
    2. RetryingDataSourceDecorator
    3. Base adapter (innermost)

    This ensures:
    - Circuit breaker fails fast before retry attempts
    - Retries happen within circuit breaker protection
    - Multiple retries count as one operation for circuit breaker
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.decorators.circuit_breaker import (
    CircuitBreakerDataSourceDecorator,
)
from bioetl.infrastructure.adapters.decorators.retry import (
    RetryingDataSourceDecorator,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        CircuitBreakerPort,
        DataSourcePort,
        LoggerPort,
        MetricsPort,
    )
    from bioetl.domain.resilience import RetryConfig

__all__ = [
    "CircuitBreakerDataSourceDecorator",
    "RetryingDataSourceDecorator",
    "wrap_with_resilience",
]


def wrap_with_resilience(
    data_source: DataSourcePort,
    retry_config: RetryConfig | None = None,
    circuit_breaker: CircuitBreakerPort | None = None,
    logger: LoggerPort | None = None,
    metrics: MetricsPort | None = None,
) -> DataSourcePort:
    """Wrap a data source with retry and circuit breaker decorators.

    Helper function to compose decorators in the correct order.

    The decorators are applied in this order (innermost to outermost):
    1. Base data source
    2. RetryingDataSourceDecorator (if retry_config provided)
    3. CircuitBreakerDataSourceDecorator (if circuit_breaker provided)

    Args:
        data_source: The base DataSourcePort to wrap.
        retry_config: Optional RetryConfig for retry behavior.
        circuit_breaker: Optional CircuitBreakerPort for circuit breaker protection.
        logger: Optional logger for decorator events.
        metrics: Optional metrics for decorator tracking.

    Returns:
        Wrapped DataSourcePort with resilience decorators.

    Example:
        >>> from bioetl.domain.resilience import RetryConfig
        >>> from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
        >>>
        >>> adapter = ChemblAdapter(...)
        >>> protected = wrap_with_resilience(
        ...     data_source=adapter,
        ...     retry_config=RetryConfig(max_attempts=3),
        ...     circuit_breaker=CircuitBreakerGuard(provider="chembl"),
        ...     logger=logger,
        ... )
    """
    result = data_source

    # Apply retry decorator first (innermost after base)
    if retry_config is not None:
        result = RetryingDataSourceDecorator(
            data_source=result,
            retry_config=retry_config,
            logger=logger,
            metrics=metrics,
        )

    # Apply circuit breaker decorator (outermost)
    if circuit_breaker is not None:
        result = CircuitBreakerDataSourceDecorator(
            data_source=result,
            circuit_breaker=circuit_breaker,
            logger=logger,
            metrics=metrics,
        )

    return result
