from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.filtered_data_source import FilteredDataSource
from bioetl.application.pipelines.uniprot.protein import UniProtProteinPipeline
from bioetl.application.registry import PipelineRegistry
from bioetl.composition.factories.base_pipeline_factory import BasePipelineFactory
from bioetl.composition.factories.data_sources import DataSourceFactory
from bioetl.composition.factories.http_client_factory import HttpClientFactory
from bioetl.infrastructure.adapters.input.csv_filter_reader import CsvFilterReader
from bioetl.infrastructure.schemas.silver import UNIPROT_PROTEIN_SCHEMA

if TYPE_CHECKING:
    from bioetl.domain.filter_config import InputFilterConfig
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
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        """Create UniProt data source."""
        # Use HttpClientFactory to create unified client
        http_client = HttpClientFactory.create_for_provider("uniprot", settings)

        data_source = DataSourceFactory.create(
            "uniprot",
            http_client=http_client,
            base_url=pipeline_config.source.api.base_url or "https://rest.uniprot.org",
            strict_error_handling=settings.strict_error_handling,
        )

        if filter_config and filter_config.enabled:
            return FilteredDataSource(
                data_source=data_source,
                filter_reader=CsvFilterReader(),
                filter_config=filter_config,
            )

        return data_source


PipelineRegistry.register(
    "uniprot_protein", UniProtProteinPipelineFactory, UNIPROT_PROTEIN_SCHEMA
)
