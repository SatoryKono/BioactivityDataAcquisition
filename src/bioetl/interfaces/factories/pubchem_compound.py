from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.pipelines.pubchem_compound import PubChemCompoundPipeline
from bioetl.infrastructure.adapters.pubchem.client import PubChemClient
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


class PubChemCompoundPipelineFactory:
    """Factory for creating PubChem Compound pipelines."""

    @staticmethod
    def build_services(
        settings: Settings,
        logger: structlog.BoundLogger,
        config: PipelineYamlConfig | None = None,
        **_kwargs,
    ) -> PipelineServices:
        """Builds PipelineServices from settings."""
        # Use provided config or load from YAML
        pipeline_config = config or load_pipeline_config("pubchem_compound")

        # Configure data source
        data_source = PubChemClient(
            rate=pipeline_config.source.get("api", {}).get("rate_limit", 5.0)
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
        """Creates PubChem Compound pipeline."""
        config_model = load_pipeline_config("pubchem_compound")
        services = PubChemCompoundPipelineFactory.build_services(
            settings=settings, logger=logger, config=config_model, **kwargs
        )
        config = get_pipeline_config("pubchem_compound")

        return PubChemCompoundPipeline.create(
            runtime=runtime,
            services=services,
            config=config,
        )
