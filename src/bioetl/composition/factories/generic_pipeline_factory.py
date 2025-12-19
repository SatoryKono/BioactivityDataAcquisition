"""Generic pipeline factory for declarative pipeline creation.

Eliminates boilerplate by providing a configurable factory class
that uses DataSourceRegistry for data source creation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from bioetl.composition.factories.base_services_factory import BaseServicesFactory
from bioetl.composition.factories.data_source_registry import (
    DataSourceCreator,
    DataSourceRegistry,
)
from bioetl.infrastructure.config import load_pipeline_config, yaml_config_to_domain

if TYPE_CHECKING:
    import pyarrow as pa
    import structlog

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


TPipeline = TypeVar("TPipeline", bound="BasePipeline")


class GenericPipelineFactory(Generic[TPipeline]):
    """Generic factory for creating pipelines with minimal configuration.

    Replaces the need for per-pipeline factory subclasses by using:
    - DataSourceRegistry for provider-specific data source creation
    - Declarative configuration of pipeline class, name, and schema

    Example:
        >>> from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline
        >>> from bioetl.infrastructure.schemas.silver import CHEMBL_ACTIVITY_SCHEMA
        >>>
        >>> factory = GenericPipelineFactory(
        ...     pipeline_class=ChEMBLActivityPipeline,
        ...     pipeline_name="chembl_activity",
        ...     provider="chembl",
        ...     silver_schema=CHEMBL_ACTIVITY_SCHEMA,
        ... )
        >>>
        >>> # Register with PipelineRegistry
        >>> PipelineRegistry.register("chembl_activity", factory, CHEMBL_ACTIVITY_SCHEMA)
    """

    def __init__(
        self,
        pipeline_class: type[TPipeline],
        pipeline_name: str,
        provider: str,
        silver_schema: pa.Schema | None = None,
        data_source_creator: DataSourceCreator | None = None,
    ) -> None:
        """Initialize the generic factory.

        Args:
            pipeline_class: The pipeline class to instantiate.
            pipeline_name: Name used for config loading and registration.
            provider: Provider name for DataSourceRegistry lookup.
            silver_schema: PyArrow schema for Silver layer validation.
            data_source_creator: Optional custom creator. If None, uses
                DataSourceRegistry.get(provider).
        """
        self.pipeline_class = pipeline_class
        self.pipeline_name = pipeline_name
        self.provider = provider
        self.silver_schema = silver_schema
        self._data_source_creator = data_source_creator

    def _get_data_source_creator(self) -> DataSourceCreator:
        """Get the data source creator for this factory.

        Returns:
            DataSourceCreator from custom override or DataSourceRegistry.
        """
        if self._data_source_creator is not None:
            return self._data_source_creator
        return DataSourceRegistry.get(self.provider)

    def create_data_source(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        """Create the data source for the pipeline.

        Args:
            settings: Application settings.
            pipeline_config: Pipeline configuration.
            filter_config: Optional input filter configuration.

        Returns:
            Configured DataSourcePort.
        """
        creator = self._get_data_source_creator()
        return creator(settings, pipeline_config, filter_config)

    def build_services(
        self,
        settings: Settings,
        logger: structlog.BoundLogger,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        **_kwargs,
    ) -> PipelineServices:
        """Build PipelineServices from settings.

        Args:
            settings: Application settings.
            logger: Structured logger.
            config: Pre-loaded pipeline config (avoids duplicate I/O).
            filter_config: Optional input filter configuration.
            **_kwargs: Additional keyword arguments (ignored).

        Returns:
            Configured PipelineServices instance.
        """
        pipeline_config = config or load_pipeline_config(self.pipeline_name)

        data_source = self.create_data_source(
            settings, pipeline_config, filter_config=filter_config
        )

        return BaseServicesFactory.create_common_services(
            settings=settings,
            logger=logger,
            data_source=data_source,
            pipeline_config=pipeline_config,
        )

    def create_with_services(
        self,
        runtime: PipelineRuntimeConfig,
        settings: Settings,
        logger: structlog.BoundLogger,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        **kwargs,
    ) -> TPipeline:
        """Create pipeline instance with services.

        Loads config once and reuses it for both services and pipeline.

        Args:
            runtime: Pipeline runtime configuration.
            settings: Application settings.
            logger: Structured logger.
            config: Pre-loaded pipeline config (avoids duplicate I/O).
            filter_config: Optional input filter configuration.
            **kwargs: Additional keyword arguments.

        Returns:
            Configured pipeline instance.
        """
        yaml_config = config or load_pipeline_config(self.pipeline_name)

        services = self.build_services(
            settings=settings,
            logger=logger,
            config=yaml_config,
            filter_config=filter_config,
            **kwargs,
        )

        domain_config = yaml_config_to_domain(yaml_config)

        return self.pipeline_class.create(
            runtime=runtime,
            services=services,
            config=domain_config,
        )


def create_pipeline_factory(
    pipeline_class: type[TPipeline],
    pipeline_name: str,
    provider: str,
    silver_schema: pa.Schema | None = None,
) -> GenericPipelineFactory[TPipeline]:
    """Convenience function to create a GenericPipelineFactory.

    Args:
        pipeline_class: The pipeline class to instantiate.
        pipeline_name: Name used for config loading and registration.
        provider: Provider name for DataSourceRegistry lookup.
        silver_schema: PyArrow schema for Silver layer validation.

    Returns:
        Configured GenericPipelineFactory instance.

    Example:
        >>> factory = create_pipeline_factory(
        ...     ChEMBLActivityPipeline,
        ...     "chembl_activity",
        ...     "chembl",
        ...     CHEMBL_ACTIVITY_SCHEMA,
        ... )
    """
    return GenericPipelineFactory(
        pipeline_class=pipeline_class,
        pipeline_name=pipeline_name,
        provider=provider,
        silver_schema=silver_schema,
    )
