from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.pipelines.uniprot_protein import UniProtProteinPipeline
from bioetl.infrastructure.adapters.uniprot.client import UniProtClient
from bioetl.infrastructure.config import (
    Settings,
    get_pipeline_config,
    load_pipeline_config,
)
from bioetl.infrastructure.factories.base_services_factory import BaseServicesFactory

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
        data_source = UniProtClient(
            rate=source_config.get("rate_limit", 10.0),
            base_url=source_config.get("base_url", "https://rest.uniprot.org")
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
        """Creates UniProt Protein pipeline."""
        config_model = load_pipeline_config("uniprot_protein")
        services = UniProtProteinPipelineFactory.build_services(
            settings=settings, logger=logger, config=config_model, **kwargs
        )
        config = get_pipeline_config("uniprot_protein")

        return UniProtProteinPipeline.create(
            runtime=runtime,
            services=services,
            config=config,
        )
