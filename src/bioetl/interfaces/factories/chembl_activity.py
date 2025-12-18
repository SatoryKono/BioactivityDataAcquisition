from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.config import (
    Settings,
    get_pipeline_config,
    load_pipeline_config,
)
from bioetl.infrastructure.factories.base_services_factory import BaseServicesFactory
from bioetl.infrastructure.factories.data_sources import DataSourceFactory

if TYPE_CHECKING:
    import structlog

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class ChEMBLActivityPipelineFactory:
    """Factory for creating ChEMBL Activity pipelines."""

    @staticmethod
    def build_services(
        settings: Settings,
        logger: structlog.BoundLogger,
        config: PipelineYamlConfig | None = None,
        **_kwargs,  # Accept and ignore extra ports for now
    ) -> PipelineServices:
        """Builds PipelineServices from settings.

        Args:
            settings: Application settings
            logger: Structured logger
            config: Pre-loaded pipeline config (avoids duplicate I/O)
            **kwargs: Additional keyword arguments (ignored)

        Returns:
            Configured PipelineServices instance
        """
        # Use provided config or load from YAML
        pipeline_config = config or load_pipeline_config("chembl_activity")

        http_client = UnifiedHTTPClient(
            TokenBucket(rate=10.0, capacity=20), CircuitBreaker(provider="chembl")
        )
        data_source = DataSourceFactory.create("chembl", http_client=http_client)

        return BaseServicesFactory.create_common_services(
            settings=settings,
            logger=logger,
            data_source=data_source,
            pipeline_config=pipeline_config,
        )

    @staticmethod
    def create_with_services(
        runtime: PipelineRuntimeConfig,
        settings: Settings,
        logger: structlog.BoundLogger,
        **kwargs,
    ) -> BasePipeline:
        """Creates ChEMBL Activity pipeline with decomposed config.

        Loads config once and passes it through to avoid duplicate I/O.
        """
        # Load config once
        config_model = load_pipeline_config("chembl_activity")

        services = ChEMBLActivityPipelineFactory.build_services(
            settings=settings, logger=logger, config=config_model, **kwargs
        )
        # get_pipeline_config uses @lru_cache, so this is cheap
        config = get_pipeline_config("chembl_activity")

        return ChEMBLActivityPipeline.create(
            runtime=runtime,
            services=services,
            config=config,
        )
