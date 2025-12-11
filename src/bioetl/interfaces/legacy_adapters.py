"""Legacy adapters for backward compatibility.

This module provides adapter functions that maintain backward compatibility
with deprecated API patterns while emitting deprecation warnings.

These adapters will be removed in a future release. Users should migrate
to the new factory-based API.

Migration guide:
    Old (deprecated):
        >>> root = CompositionRoot(logger=my_logger, metrics=my_metrics)

    New (recommended):
        >>> from bioetl.interfaces.factories import CustomObservabilityFactory
        >>> class MyObservabilityFactory(ObservabilityFactoryABC):
        ...     def create_logger(self) -> LoggingPortABC:
        ...         return my_logger
        ...     def create_metrics(self) -> MetricsPortABC:
        ...         return my_metrics
        >>> root = CompositionRoot(observability_factory=MyObservabilityFactory())
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import warnings

from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.interfaces.composition_root import CompositionRoot
from bioetl.interfaces.factories import (
    InfrastructureFactoryABC,
    ObservabilityFactoryABC,
)

if TYPE_CHECKING:
    pass


class _LegacyObservabilityFactory(ObservabilityFactoryABC):
    """Observability factory wrapping explicit logger/metrics instances.

    This factory is used internally for backward compatibility when
    legacy parameters (logger, metrics) are passed to CompositionRoot.
    """

    def __init__(
        self,
        logger: LoggingPortABC | None = None,
        metrics: MetricsPortABC | None = None,
        fallback_factory: ObservabilityFactoryABC | None = None,
    ) -> None:
        self._logger = logger
        self._metrics = metrics
        self._fallback = fallback_factory

    def create_logger(self) -> LoggingPortABC:
        """Return explicit logger or fallback to factory."""
        if self._logger is not None:
            return self._logger
        if self._fallback is not None:
            return self._fallback.create_logger()
        from bioetl.interfaces.factories import DefaultObservabilityFactory

        return DefaultObservabilityFactory().create_logger()

    def create_metrics(self) -> MetricsPortABC:
        """Return explicit metrics or fallback to factory."""
        if self._metrics is not None:
            return self._metrics
        if self._fallback is not None:
            return self._fallback.create_metrics()
        from bioetl.interfaces.factories import DefaultObservabilityFactory

        return DefaultObservabilityFactory().create_metrics()


def create_composition_root_with_legacy(
    *,
    logger: LoggingPortABC | None = None,
    metrics: MetricsPortABC | None = None,
    observability_factory: ObservabilityFactoryABC | None = None,
    infrastructure_factory: InfrastructureFactoryABC | None = None,
    http_session_factory: type | None = None,
    schema_contract_provider: SchemaContractProviderABC | None = None,
) -> CompositionRoot:
    """Create CompositionRoot with legacy parameter support.

    .. deprecated::
        The `logger` and `metrics` parameters are deprecated.
        Use `observability_factory` instead.

    This function provides backward compatibility for code that passes
    explicit logger/metrics instances. It wraps them in a factory and
    emits deprecation warnings.

    Args:
        logger: Deprecated. Use observability_factory instead.
        metrics: Deprecated. Use observability_factory instead.
        observability_factory: Factory for observability components.
        infrastructure_factory: Factory for infrastructure components.
        http_session_factory: HTTP session factory class.
        schema_contract_provider: Custom schema contract provider.

    Returns:
        Configured CompositionRoot instance.

    Example:
        Old (deprecated):
            >>> root = create_composition_root_with_legacy(
            ...     logger=mock_logger,
            ...     metrics=mock_metrics,
            ... )

        New (recommended):
            >>> root = CompositionRoot(
            ...     observability_factory=MyObservabilityFactory(),
            ... )
    """
    if logger is not None or metrics is not None:
        warnings.warn(
            "logger/metrics parameters are deprecated. "
            "Use observability_factory instead. "
            "These parameters will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Create a factory that wraps the explicit instances
        effective_factory = _LegacyObservabilityFactory(
            logger=logger,
            metrics=metrics,
            fallback_factory=observability_factory,
        )
    else:
        effective_factory = observability_factory

    return CompositionRoot(
        observability_factory=effective_factory,
        infrastructure_factory=infrastructure_factory,
        http_session_factory=http_session_factory,
        schema_contract_provider=schema_contract_provider,
    )


__all__ = [
    "create_composition_root_with_legacy",
]
