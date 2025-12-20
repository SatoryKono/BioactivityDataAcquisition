from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline
from bioetl.application.registry import PipelineRegistry
from bioetl.composition.factories.base_pipeline_factory import BasePipelineFactory
from bioetl.composition.factories.data_source_registry import _wrap_with_filter
from bioetl.composition.factories.http_client_factory import HttpClientFactory
from bioetl.infrastructure.factories.data_sources import DataSourceFactory
from bioetl.infrastructure.schemas.silver import CHEMBL_ACTIVITY_SCHEMA

if TYPE_CHECKING:
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


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

        return _wrap_with_filter(base_adapter, filter_config)


PipelineRegistry.register(
    "chembl_activity", ChEMBLActivityPipelineFactory, CHEMBL_ACTIVITY_SCHEMA
)
