from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.factories.data_sources import DataSourceFactory
from bioetl.application.registry import PipelineRegistry
from bioetl.infrastructure.schemas.silver import CHEMBL_ACTIVITY_SCHEMA
from bioetl.composition.factories.base_pipeline_factory import BasePipelineFactory

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from bioetl.domain.ports import DataSourcePort


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
    ) -> DataSourcePort:
        """Create ChEMBL data source."""
        # ChEMBL specific HTTP client setup
        http_client = UnifiedHTTPClient(
            TokenBucket(rate=10.0, capacity=20), CircuitBreaker(provider="chembl")
        )
        return DataSourceFactory.create("chembl", http_client=http_client)


PipelineRegistry.register(
    "chembl_activity", ChEMBLActivityPipelineFactory, CHEMBL_ACTIVITY_SCHEMA
)
