"""
Factory for creating pipeline runtime components.

Provides hooks, error policies, and metrics ports for pipeline execution.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from bioetl.application.factories.hooks import PipelineHookFactory
from bioetl.application.factories.hooks_impl import FailFastErrorPolicyImpl
from bioetl.application.factories.noop import create_noop_metrics_port
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC


class PipelineRuntimeFactoryABC(ABC):
    """Abstract factory for creating pipeline runtime components.

    Defines the contract for factories that provide hooks, error policies,
    and metrics ports used during pipeline execution.
    """

    @abstractmethod
    def get_hooks(self, logger: LoggingPortABC) -> list[PipelineHookABC]:
        """Get pipeline execution hooks.

        Args:
            logger: Logger to use for logging hooks.

        Returns:
            List of pipeline hooks.
        """

    @abstractmethod
    def get_error_policy(self) -> ErrorPolicyABC:
        """Get the error handling policy.

        Returns:
            Error policy for pipeline execution.
        """

    @abstractmethod
    def get_metrics_port(self) -> MetricsPortABC:
        """Get the metrics port.

        Returns:
            Metrics port for observability.
        """


class PipelineRuntimeFactory(PipelineRuntimeFactoryABC):
    """Factory for creating pipeline runtime components.

    Encapsulates creation of hooks, error policies, and metrics ports
    that are used during pipeline execution.
    """

    def __init__(
        self,
        config: PipelineConfig,
        metrics_port: MetricsPortABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
    ) -> None:
        """Initialize the runtime factory.

        Args:
            config: Pipeline configuration.
            metrics_port: Optional metrics port (noop if not provided).
            hooks: Optional pre-configured hooks list.
            error_policy: Optional error handling policy.
        """
        self._config = config
        self._metrics_port = metrics_port
        self._hooks: list[PipelineHookABC] | None = list(hooks) if hooks else None
        self._error_policy = error_policy
        self._hook_factory: PipelineHookFactory | None = None

    def _get_hook_factory(self) -> PipelineHookFactory:
        """Get or create the hook factory."""
        if self._hook_factory is None:
            self._hook_factory = PipelineHookFactory(
                self._config,
                self.get_metrics_port(),
            )
        return self._hook_factory

    def get_hooks(self, logger: LoggingPortABC) -> list[PipelineHookABC]:
        """Get pipeline execution hooks.

        Creates default logging and metrics hooks if none were provided.

        Args:
            logger: Logger to use for logging hooks.

        Returns:
            List of pipeline hooks.
        """
        if self._hooks is None:
            self._hooks = self._get_hook_factory().create_hooks(logger)
        return list(self._hooks)

    def get_error_policy(self) -> ErrorPolicyABC:
        """Get the error handling policy.

        Returns fail-fast policy if none was provided.

        Returns:
            Error policy for pipeline execution.
        """
        if self._error_policy is None:
            self._error_policy = FailFastErrorPolicyImpl()
        return self._error_policy

    def get_metrics_port(self) -> MetricsPortABC:
        """Get the metrics port.

        Returns noop metrics if none was provided.

        Returns:
            Metrics port for observability.
        """
        if self._metrics_port is None:
            self._metrics_port = create_noop_metrics_port()
        return self._metrics_port


__all__ = ["PipelineRuntimeFactory", "PipelineRuntimeFactoryABC"]
