from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.pipelines.uniprot_protein import UniProtProteinPipeline
from bioetl.infrastructure.config import (
    Settings,
    load_pipeline_config,
    yaml_config_to_domain,
)
from bioetl.infrastructure.factories.base_services_factory import BaseServicesFactory
from bioetl.infrastructure.factories.data_sources import DataSourceFactory

if TYPE_CHECKING:
    import structlog

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class UniProtProteinPipelineFactory:
    """Factory for creating UniProt Protein pipelines."""

    @staticmethod
    def build_services(
        settings: Settings,
        logger: structlog.BoundLogger,
        config: PipelineYamlConfig | None = None,
        **_kwargs,
    ) -> PipelineServices:
        """Builds PipelineServices from settings."""
        pipeline_config = config or load_pipeline_config("uniprot_protein")

        # Configure data source
        source_config = pipeline_config.source.get("api", {})
        data_source = DataSourceFactory.create(
            "uniprot",
            http_client=None,
            rate=source_config.get("rate_limit", 10.0),
            base_url=source_config.get("base_url", "https://rest.uniprot.org"),
            strict_error_handling=settings.strict_error_handling,
        )

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
        """Creates UniProt Protein pipeline.

        Loads config once and reuses it for both services and pipeline.
        """
        # Load YAML config once (cached)
        yaml_config = load_pipeline_config("uniprot_protein")

        # Build services with YAML config
        services = UniProtProteinPipelineFactory.build_services(
            settings=settings, logger=logger, config=yaml_config, **kwargs
        )

        # Map to domain config for pipeline
        domain_config = yaml_config_to_domain(yaml_config)

        return UniProtProteinPipeline.create(
            runtime=runtime,
            services=services,
            config=domain_config,
        )
