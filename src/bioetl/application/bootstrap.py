"""Application bootstrap for initializing the application layer.

This module provides the central entry point for bootstrapping the application.
It ensures all application-level services are initialized in the correct order
and provides an ApplicationContext with ready-to-use dependencies.

Note:
    This module contains only application-layer code and does not depend on
    infrastructure. Infrastructure-specific initialization (config loaders,
    provider injection) should be provided via dependency injection from
    the interfaces layer.

Example:
    >>> # Basic usage (application layer only)
    >>> bootstrap = ApplicationBootstrap()
    >>> context = bootstrap.start()
    >>> schema = context.schema_provider.get_schema("activity")
    >>>
    >>> # With infrastructure integration
    >>> from bioetl.interfaces.bootstrap_factory import create_default_bootstrap
    >>> bootstrap = create_default_bootstrap()
    >>> context = bootstrap.start()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from bioetl.application.services.config_migration_service import (
    ConfigMigrationService,
    ConfigMigrationServiceProtocol,
    create_config_migration_service,
)
from bioetl.application.services.schema_bootstrap import (
    SchemaBootstrapService,
    create_schema_bootstrap_service,
)
from bioetl.application.services.schema_contract_provider import (
    SchemaContractProviderImpl,
)
from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.validation import SchemaProviderABC

if TYPE_CHECKING:
    pass

# Type aliases for callbacks
ConfigLoaderFactory = Callable[
    [SchemaContractProviderABC], PipelineConfigLoaderProtocol
]
ProviderInjector = Callable[[SchemaContractProviderABC], None]
ProviderClearer = Callable[[], None]
MigrationServiceFactory = Callable[[], ConfigMigrationServiceProtocol]


@dataclass(frozen=True)
class ApplicationServicesContext:
    """Context of an initialized application.

    Provides access to all bootstrapped services needed by the application.
    This is an immutable data class that holds references to the initialized
    services.

    Attributes:
        schema_provider: Provider for accessing registered schemas.
        contract_provider: Provider for schema contracts used by pipelines.
        config_loader: Loader for pipeline configurations (may be None if
            no config loader factory was provided).
        migration_service: Service for migrating and validating raw configs.
            Provides application-layer interface for config migration without
            going through full loader flow.
    """

    schema_provider: SchemaProviderABC
    contract_provider: SchemaContractProviderABC
    config_loader: PipelineConfigLoaderProtocol | None = None
    migration_service: ConfigMigrationServiceProtocol | None = None


class ApplicationBootstrap:
    """Central entry point for application initialization.

    Ensures all application-level services are initialized in the correct
    order and ready for use. Provides idempotent initialization - multiple
    calls to start() return the same context.

    This class eliminates the need for global state by encapsulating
    all bootstrap logic in a single, testable object.

    Infrastructure-specific functionality (config loaders, provider injection)
    can be provided via dependency injection through constructor parameters.

    Args:
        config_loader_factory: Optional factory for creating config loaders.
            If provided, will be called with the contract provider to create
            a config loader.
        provider_injector: Optional callback to inject the contract provider
            into infrastructure for backward compatibility.
        provider_clearer: Optional callback to clear the injected provider
            during shutdown.
        migration_service_factory: Optional factory for creating migration service.
            If provided, will be used to create the config migration service.

    Example:
        >>> # Basic usage without infrastructure
        >>> bootstrap = ApplicationBootstrap()
        >>> context = bootstrap.start()
        >>> schema = context.schema_provider.get_schema("activity")
        >>>
        >>> # With config loader factory
        >>> def make_loader(provider):
        ...     return MyConfigLoader(provider)
        >>> bootstrap = ApplicationBootstrap(config_loader_factory=make_loader)
        >>> context = bootstrap.start()
        >>> config = context.config_loader.get_by_id("chembl.activity")
    """

    def __init__(
        self,
        *,
        config_loader_factory: ConfigLoaderFactory | None = None,
        provider_injector: ProviderInjector | None = None,
        provider_clearer: ProviderClearer | None = None,
        migration_service_factory: MigrationServiceFactory | None = None,
        schema_register_fn: Callable[[SchemaProviderABC], Any] | None = None,
    ) -> None:
        """Initialize the bootstrap instance with optional infrastructure hooks."""
        self._context: ApplicationServicesContext | None = None
        self._started: bool = False
        self._schema_bootstrap_service: SchemaBootstrapService | None = None

        # Infrastructure hooks (dependency injection)
        self._config_loader_factory = config_loader_factory
        self._provider_injector = provider_injector
        self._provider_clearer = provider_clearer
        self._migration_service_factory = migration_service_factory
        self._schema_register_fn = schema_register_fn

    def start(self) -> ApplicationServicesContext:
        """Initialize the application and return the context.

        Idempotent: subsequent calls return the same context.

        Returns:
            ApplicationServicesContext with all initialized services.
        """
        if self._started:
            return self._get_context()

        schema_provider = self._init_schema_provider()
        contract_provider = self._init_contract_provider(schema_provider)

        # Inject provider if callback provided (for backward compatibility)
        if self._provider_injector is not None:
            self._provider_injector(contract_provider)

        # Create config loader if factory provided
        config_loader: PipelineConfigLoaderProtocol | None = None
        if self._config_loader_factory is not None:
            config_loader = self._config_loader_factory(contract_provider)

        # Create migration service if factory provided
        migration_service: ConfigMigrationServiceProtocol | None = None
        if self._migration_service_factory is not None:
            migration_service = self._migration_service_factory()

        self._context = ApplicationServicesContext(
            schema_provider=schema_provider,
            contract_provider=contract_provider,
            config_loader=config_loader,
            migration_service=migration_service,
        )
        self._started = True
        return self._context

    def shutdown(self) -> None:
        """Release resources and reset state (for graceful shutdown).

        Clears the cached context and resets initialization state.
        This is primarily useful for testing scenarios where you need
        to re-initialize the application.
        """
        # Clear provider if callback provided
        if self._provider_clearer is not None:
            self._provider_clearer()

        self._context = None
        self._started = False
        self._schema_bootstrap_service = None

    @property
    def is_started(self) -> bool:
        """Check if the application has been started."""
        return self._started

    @property
    def context(self) -> ApplicationServicesContext | None:
        """Get the current context (may be None if not started)."""
        return self._context

    def _get_context(self) -> ApplicationServicesContext:
        """Get context or raise if not started.

        Returns:
            The initialized ApplicationServicesContext.

        Raises:
            RuntimeError: If application has not been started.
        """
        if self._context is None:
            raise RuntimeError("Application not started. Call start() first.")
        return self._context

    def _init_schema_provider(self) -> SchemaProviderABC:
        """Initialize and return the schema provider.

        Creates a SchemaBootstrapService and ensures all schemas are registered.

        Returns:
            Fully initialized schema provider with all schemas registered.
        """
        self._schema_bootstrap_service = create_schema_bootstrap_service(
            register_fn=self._schema_register_fn
        )
        return self._schema_bootstrap_service.ensure_registered()

    def _init_contract_provider(
        self, schema_provider: SchemaProviderABC
    ) -> SchemaContractProviderABC:
        """Initialize and return the schema contract provider.

        Args:
            schema_provider: The initialized schema provider.

        Returns:
            SchemaContractProviderImpl wrapping the schema provider.
        """
        return SchemaContractProviderImpl(schema_provider)


def create_application_bootstrap(
    *,
    config_loader_factory: ConfigLoaderFactory | None = None,
    provider_injector: ProviderInjector | None = None,
    provider_clearer: ProviderClearer | None = None,
    migration_service_factory: MigrationServiceFactory | None = None,
    schema_register_fn: Callable[[SchemaProviderABC], Any] | None = None,
) -> ApplicationBootstrap:
    """Create an ApplicationBootstrap instance.

    Factory function for creating ApplicationBootstrap instances.
    Provides a clean way to create bootstrap objects with optional
    infrastructure hooks.

    Args:
        config_loader_factory: Optional factory for creating config loaders.
        provider_injector: Optional callback to inject the contract provider.
        provider_clearer: Optional callback to clear the injected provider.
        migration_service_factory: Optional factory for creating migration service.
        schema_register_fn: Optional callback to register schemas.

    Returns:
        New ApplicationBootstrap instance.

    Example:
        >>> # Basic usage
        >>> bootstrap = create_application_bootstrap()
        >>> context = bootstrap.start()
        >>>
        >>> # With infrastructure hooks
        >>> bootstrap = create_application_bootstrap(
        ...     config_loader_factory=my_loader_factory,
        ...     provider_injector=inject_provider,
        ... )
    """
    return ApplicationBootstrap(
        config_loader_factory=config_loader_factory,
        provider_injector=provider_injector,
        provider_clearer=provider_clearer,
        migration_service_factory=migration_service_factory,
        schema_register_fn=schema_register_fn,
    )


__all__ = [
    "ApplicationBootstrap",
    "ApplicationServicesContext",
    "ConfigLoaderFactory",
    "ConfigMigrationService",
    "ConfigMigrationServiceProtocol",
    "MigrationServiceFactory",
    "ProviderClearer",
    "ProviderInjector",
    "create_application_bootstrap",
    "create_config_migration_service",
]

# Backward compatibility alias
ApplicationContext = ApplicationServicesContext
