"""Base Pipeline Factory (Legacy).

This module provides the legacy class-based factory pattern.
For new pipelines, prefer using GenericPipelineFactory from generic_factory.py.

.. deprecated:: 0.2.0
    Use :class:`GenericPipelineFactory` instead for new pipelines.
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from bioetl.infrastructure.config import load_pipeline_config, yaml_config_to_domain
from bioetl.composition.factories.base_services_factory import BaseServicesFactory

if TYPE_CHECKING:
    import structlog
    import pyarrow as pa
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from bioetl.infrastructure.config import Settings
    from bioetl.domain.ports import DataSourcePort
    from bioetl.domain.filter_config import InputFilterConfig

TPipeline = TypeVar("TPipeline", bound="BasePipeline")


class BasePipelineFactory(Generic[TPipeline], ABC):
    """Base factory for creating pipelines.

    .. deprecated:: 0.2.0
        This class-based pattern is deprecated. Use :class:`GenericPipelineFactory`
        from :mod:`bioetl.composition.factories.generic_factory` instead.

        Migration example::

            # Old pattern (deprecated):
            class MyPipelineFactory(BasePipelineFactory[MyPipeline]):
                pipeline_name = "my_pipeline"
                pipeline_class = MyPipeline
                silver_schema = MY_SCHEMA

                @classmethod
                def create_data_source(cls, settings, config, filter_config=None):
                    return MyDataSource()

            # New pattern (recommended):
            from bioetl.composition.factories import GenericPipelineFactory

            factory = GenericPipelineFactory(
                pipeline_name="my_pipeline",
                pipeline_class=MyPipeline,
                provider="my_provider",
                silver_schema=MY_SCHEMA,
            )
            PipelineRegistry.register_factory(factory)
    """

    pipeline_name: str
    pipeline_class: type[TPipeline]
    silver_schema: pa.Schema | None = None

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Emit deprecation warning when subclassing."""
        super().__init_subclass__(**kwargs)
        warnings.warn(
            f"Subclassing BasePipelineFactory is deprecated. "
            f"Use GenericPipelineFactory instead for '{cls.__name__}'. "
            f"See bioetl.composition.factories.generic_factory for the new pattern.",
            DeprecationWarning,
            stacklevel=2,
        )

    @classmethod
    @abstractmethod
    def create_data_source(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        """Create the data source for the pipeline.

        Args:
            settings: Application settings
            pipeline_config: Pipeline configuration
            filter_config: Optional input filter configuration for CSV filtering

        Returns:
            Configured DataSourcePort (possibly wrapped with FilteredDataSource)
        """
        ...

    @classmethod
    def build_services(
        cls,
        settings: Settings,
        logger: structlog.BoundLogger,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        **_kwargs,
    ) -> PipelineServices:
        """Builds PipelineServices from settings.

        Args:
            settings: Application settings
            logger: Structured logger
            config: Pre-loaded pipeline config (avoids duplicate I/O)
            filter_config: Optional input filter configuration
            **_kwargs: Additional keyword arguments (ignored)

        Returns:
            Configured PipelineServices instance
        """
        # Use provided config or load from YAML
        pipeline_config = config or load_pipeline_config(cls.pipeline_name)

        data_source = cls.create_data_source(
            settings, pipeline_config, filter_config=filter_config
        )

        return BaseServicesFactory.create_common_services(
            settings=settings,
            logger=logger,
            data_source=data_source,
            pipeline_config=pipeline_config,
        )

    @classmethod
    def create_with_services(
        cls,
        runtime: PipelineRuntimeConfig,
        settings: Settings,
        logger: structlog.BoundLogger,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        **kwargs,
    ) -> TPipeline:
        """Creates pipeline instance.

        Loads config once and reuses it for both services and pipeline.

        Args:
            runtime: Pipeline runtime configuration
            settings: Application settings
            logger: Structured logger
            config: Pre-loaded pipeline config (avoids duplicate I/O)
            filter_config: Optional input filter configuration for CSV filtering
            **kwargs: Additional keyword arguments
        """
        # Use provided config or load YAML config (cached)
        yaml_config = config or load_pipeline_config(cls.pipeline_name)

        # Build services with YAML config and filter config
        services = cls.build_services(
            settings=settings,
            logger=logger,
            config=yaml_config,
            filter_config=filter_config,
            **kwargs,
        )

        # Map to domain config for pipeline
        domain_config = yaml_config_to_domain(yaml_config)

        # Note: We assume TPipeline has a create method compatible with this signature.
        # Since BasePipeline is the bound, and it usually has a create method, this should work.
        # However, BasePipeline.create might need to be called on the concrete class.
        return cls.pipeline_class.create(
            runtime=runtime,
            services=services,
            config=domain_config,
        )
