"""Stub factories for pipeline abstractions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.pipelines.contracts import PipelineContainerABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC

if TYPE_CHECKING:
    from bioetl.application.container import SimplePipelineContainer
    from bioetl.application.pipelines.base import PipelineBase
    from bioetl.domain.configs import PipelineConfig
    from bioetl.domain.ports.extraction import ExtractionServiceABC


def default_pipeline_container() -> PipelineContainerABC:
    """Provide a placeholder pipeline container until DI container is configured."""

    raise NotImplementedError("PipelineContainerABC default factory is not configured")


def default_pipeline_hook() -> PipelineHookABC:
    """Provide a placeholder pipeline hook."""

    raise NotImplementedError("PipelineHookABC default factory is not configured")


def default_error_policy() -> ErrorPolicyABC:
    """Provide a placeholder error policy."""

    raise NotImplementedError("ErrorPolicyABC default factory is not configured")


def create_extraction_service(
    provider_config: Any,
    *,
    parser: Any | None = None,
) -> ExtractionServiceABC:
    """Create extraction service for the configured provider.

    Args:
        provider_config: Provider-specific configuration.
        parser: Optional response parser to use. If not provided,
            a default parser will be created.

    Returns:
        Configured extraction service instance.

    Note:
        This is a factory function that creates provider-specific
        extraction services. The actual implementation depends on
        the provider configuration type.
    """
    from bioetl.application.factories.services import ProviderServiceFactory
    from bioetl.domain.configs import PipelineConfig
    from bioetl.domain.providers import ProviderDefinition, ProviderId

    # This is a simplified factory - in practice you would resolve
    # the provider definition from a registry based on config
    raise NotImplementedError(
        "create_extraction_service requires provider registry integration. "
        "Use container.get_extraction_service() instead."
    )


def create_chembl_pipeline(
    config: PipelineConfig,
    container: SimplePipelineContainer,
) -> PipelineBase:
    """Create ChEMBL pipeline with all dependencies.

    This factory function creates a fully configured ChEMBL pipeline
    using the simplified container. It handles bootstrapping and
    dependency injection.

    Args:
        config: Pipeline configuration including provider settings.
        container: SimplePipelineContainer for dependency resolution.

    Returns:
        Configured ChemblPipelineBase ready to run.

    Example:
        >>> from bioetl.application.container import SimplePipelineContainer
        >>> from bioetl.domain.configs import PipelineConfig
        >>>
        >>> config = PipelineConfig(...)
        >>> container = SimplePipelineContainer()
        >>> pipeline = create_chembl_pipeline(config, container)
        >>> result = pipeline.run()

    Note:
        This function automatically bootstraps the container if it
        hasn't been bootstrapped yet.
    """
    from bioetl.application.pipelines.chembl.common import ChemblCommonPipeline
    from bioetl.application.pipelines.stages.extract import ExtractStage

    # Ensure container is bootstrapped
    container.bootstrap()

    # Get components from container
    record_mapper = container.record_mapper
    response_parser = container.response_parser

    # The actual pipeline creation depends on additional services
    # that would be provided by the full container or external configuration
    # This is a simplified version for demonstration

    return _create_chembl_pipeline_impl(
        config=config,
        record_mapper=record_mapper,
        response_parser=response_parser,
    )


def _create_chembl_pipeline_impl(
    config: PipelineConfig,
    record_mapper: Any,
    response_parser: Any,
) -> PipelineBase:
    """Internal implementation for ChEMBL pipeline creation.

    This is a stub that should be extended with full pipeline
    assembly logic including extraction service, validation,
    transformation, and loading components.
    """
    # This would typically:
    # 1. Create extraction service with the response parser
    # 2. Create extraction stage with record mapper
    # 3. Assemble full pipeline with all stages
    raise NotImplementedError(
        "Full pipeline creation requires additional services. "
        "Use ChemblPipelineFactory.create() with a full PipelineContainer, "
        "or extend this function with the required dependencies."
    )


__all__ = [
    "default_pipeline_container",
    "default_pipeline_hook",
    "default_error_policy",
    "create_extraction_service",
    "create_chembl_pipeline",
]
