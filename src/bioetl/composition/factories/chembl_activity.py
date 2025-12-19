from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline
from bioetl.infrastructure.factories.data_sources import DataSourceFactory
from bioetl.application.registry import PipelineRegistry
from bioetl.infrastructure.schemas.silver import CHEMBL_ACTIVITY_SCHEMA
from bioetl.composition.factories.base_pipeline_factory import BasePipelineFactory
from bioetl.composition.factories.http_client_factory import HttpClientFactory

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from bioetl.domain.ports import DataSourcePort
    from bioetl.domain.filter_config import InputFilterConfig


class ChEMBLActivityPipelineFactory(BasePipelineFactory[ChEMBLActivityPipeline]):
    """Factory for creating ChEMBL Activity pipelines."""

    pipeline_name = "chembl_activity"
    pipeline_class = ChEMBLActivityPipeline
    silver_schema = CHEMBL_ACTIVITY_SCHEMA

    @classmethod
    def create_data_source(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        """Create ChEMBL data source with optional CSV filtering.

        Args:
            settings: Application settings
            pipeline_config: Pipeline configuration
            filter_config: Optional input filter configuration

        Returns:
            DataSourcePort, wrapped with FilteredDataSource if filter_config is enabled
        """
        # ChEMBL specific HTTP client setup using factory
        http_client = HttpClientFactory.create_for_provider("chembl", settings)
        base_adapter = DataSourceFactory.create("chembl", http_client=http_client)

        # Wrap with FilteredDataSource if filter is enabled
        if filter_config and filter_config.enabled:
            from bioetl.application.core.filtered_data_source import FilteredDataSource
            from bioetl.infrastructure.adapters.input.csv_filter_reader import (
                CsvFilterReader,
            )

            return FilteredDataSource(
                data_source=base_adapter,
                filter_reader=CsvFilterReader(),
                filter_config=filter_config,
            )

        return base_adapter


PipelineRegistry.register(
    "chembl_activity", ChEMBLActivityPipelineFactory, CHEMBL_ACTIVITY_SCHEMA
)
