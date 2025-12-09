"""Interface-layer wiring for application ports to infrastructure implementations."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable

from bioetl.domain.configs import PipelineConfig
from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
from bioetl.infrastructure.config.loader import (
    get_pipeline_config,
    get_pipeline_config_from_path,
)
from bioetl.interfaces.container_factory import (
    build_default_container as application_build_default_container,
    create_default_container_factory,
)


def create_config_loader() -> PipelineConfigLoaderProtocol:
    """Return config loader port backed by infrastructure loader."""

    return SimpleNamespace(
        get_by_id=get_pipeline_config,
        get_from_path=get_pipeline_config_from_path,
    )


def build_default_container(
    config: PipelineConfig,
    *,
    provider_registry: Any | None = None,
    provider_registry_provider: Callable[[], Any] | None = None,
) -> Any:
    """Proxy to application-level default container factory."""

    return application_build_default_container(
        config,
        provider_registry=provider_registry,
        provider_registry_provider=provider_registry_provider,
    )


def create_container_factory() -> Callable[..., Any]:
    """Expose default container factory."""

    return create_default_container_factory()


__all__ = [
    "create_config_loader",
    "create_container_factory",
    "build_default_container",
]
