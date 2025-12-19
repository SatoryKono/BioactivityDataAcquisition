from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.pipelines.uniprot.protein import UniProtProteinPipeline
from bioetl.application.registry import PipelineRegistry
from bioetl.composition.factories.base_pipeline_factory import BasePipelineFactory
from bioetl.composition.factories.http_client_factory import HttpClientFactory
from bioetl.infrastructure.factories.data_sources import DataSourceFactory
from bioetl.infrastructure.schemas.silver import UNIPROT_PROTEIN_SCHEMA

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class UniProtProteinPipelineFactory(BasePipelineFactory[UniProtProteinPipeline]):
    """Factory for creating UniProt Protein pipelines."""

    pipeline_name = "uniprot_protein"
    pipeline_class = UniProtProteinPipeline
    silver_schema = UNIPROT_PROTEIN_SCHEMA

    @classmethod
    def create_data_source(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
    ) -> DataSourcePort:
        """Create UniProt data source."""
        source_config = pipeline_config.source.get("api", {})

        # Use HttpClientFactory to create unified client
        http_client = HttpClientFactory.create_for_provider("uniprot", settings)

        return DataSourceFactory.create(
            "uniprot",
            http_client=http_client,
            base_url=source_config.get("base_url", "https://rest.uniprot.org"),
            strict_error_handling=settings.strict_error_handling,
        )


PipelineRegistry.register(
    "uniprot_protein", UniProtProteinPipelineFactory, UNIPROT_PROTEIN_SCHEMA
)
