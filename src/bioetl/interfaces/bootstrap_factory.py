"""Factory for creating ApplicationBootstrap with infrastructure integration.

This module provides factory functions for creating ApplicationBootstrap
instances configured with infrastructure-layer components (config loaders,
provider injection).

The separation between application-layer bootstrap logic and infrastructure
integration maintains clean architecture boundaries while providing a
convenient entry point for CLI and other interfaces.

Example:
    >>> from bioetl.interfaces.bootstrap_factory import create_default_bootstrap
    >>> bootstrap = create_default_bootstrap()
    >>> context = bootstrap.start()
    >>> config = context.config_loader.get_by_id("chembl.activity")
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from bioetl.application.bootstrap import (
    ApplicationBootstrap,
    ConfigLoaderFactory,
    ProviderClearer,
    ProviderInjector,
)
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
from bioetl.domain.ports.schema import SchemaContractProviderABC


def _create_config_loader_factory() -> ConfigLoaderFactory:
    """Create a config loader factory using infrastructure components.

    Returns:
        Factory function that creates a config loader given a contract provider.
    """
    from bioetl.infrastructure.config.loader import (
        get_pipeline_config,
        get_pipeline_config_from_path,
    )

    def factory(
        contract_provider: SchemaContractProviderABC,
    ) -> PipelineConfigLoaderProtocol:
        """Build a config loader bound to the provided schema contracts."""
        def get_by_id(
            pipeline_id: str,
            *,
            profile: str | None = None,
            cli_overrides: dict[str, Any] | None = None,
            env_overrides: dict[str, Any] | None = None,
            base_dir: str | Path | None = None,
        ) -> PipelineConfig:
            """Load pipeline config by id with optional overrides."""
            return get_pipeline_config(
                pipeline_id,
                schema_contract_provider=contract_provider,
                profile=profile,
                cli_overrides=cli_overrides,
                env_overrides=env_overrides,
                base_dir=base_dir,
            )

        def get_from_path(
            config_path: str | Path,
            *,
            profile: str | None = None,
            profiles_root: str | Path | None = None,
            cli_overrides: dict[str, Any] | None = None,
            env_overrides: dict[str, Any] | None = None,
        ) -> PipelineConfig:
            """Load pipeline config from an explicit file path."""
            return get_pipeline_config_from_path(
                config_path,
                schema_contract_provider=contract_provider,
                profile=profile,
                profiles_root=profiles_root,
                cli_overrides=cli_overrides,
                env_overrides=env_overrides,
            )

        return cast(
            PipelineConfigLoaderProtocol,
            SimpleNamespace(
                get_by_id=get_by_id,
                get_from_path=get_from_path,
            ),
        )

    return factory


def _create_provider_injector() -> ProviderInjector:
    """Create a provider injector for backward compatibility.

    Returns:
        Callback function that injects the provider into infrastructure.
    """
    from bioetl.infrastructure.config.loader import _set_provider_internal

    def injector(provider: SchemaContractProviderABC) -> None:
        """Inject provider instance into infrastructure config loader."""
        _set_provider_internal(provider)

    return injector


def _create_provider_clearer() -> ProviderClearer:
    """Create a provider clearer for cleanup.

    Returns:
        Callback function that clears the provider from infrastructure.
    """
    from bioetl.infrastructure.config.loader import _clear_provider_internal

    def clearer() -> None:
        """Clear injected provider from infrastructure config loader."""
        _clear_provider_internal()

    return clearer


def create_default_bootstrap() -> ApplicationBootstrap:
    """Create an ApplicationBootstrap with default infrastructure integration.

    This factory creates a fully configured ApplicationBootstrap instance
    with config loader support and provider injection for backward compatibility.

    Returns:
        ApplicationBootstrap configured with infrastructure components.

    Example:
        >>> bootstrap = create_default_bootstrap()
        >>> context = bootstrap.start()
        >>> config = context.config_loader.get_by_id("chembl.activity")
    """
    from bioetl.infrastructure.validation.bootstrap import register_schemas

    return ApplicationBootstrap(
        config_loader_factory=_create_config_loader_factory(),
        provider_injector=_create_provider_injector(),
        provider_clearer=_create_provider_clearer(),
        schema_register_fn=register_schemas,
    )


__all__ = [
    "create_default_bootstrap",
]
