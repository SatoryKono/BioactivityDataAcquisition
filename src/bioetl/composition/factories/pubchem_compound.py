from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.pipelines.pubchem_compound import PubChemCompoundPipeline
from bioetl.infrastructure.factories.data_sources import DataSourceFactory
from bioetl.application.registry import PipelineRegistry
from bioetl.infrastructure.schemas.silver import PUBCHEM_COMPOUND_SCHEMA
from bioetl.composition.factories.base_pipeline_factory import BasePipelineFactory

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from bioetl.domain.ports import DataSourcePort


class PubChemCompoundPipelineFactory(BasePipelineFactory[PubChemCompoundPipeline]):
    """Factory for creating PubChem Compound pipelines."""

    pipeline_name = "pubchem_compound"
    pipeline_class = PubChemCompoundPipeline
    silver_schema = PUBCHEM_COMPOUND_SCHEMA

    @classmethod
    def create_data_source(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
    ) -> DataSourcePort:
        """Create PubChem data source."""
        return DataSourceFactory.create(
            "pubchem",
            http_client=None,
            rate=pipeline_config.source.get("api", {}).get("rate_limit", 5.0),
            strict_error_handling=settings.strict_error_handling,
        )


PipelineRegistry.register(
    "pubchem_compound", PubChemCompoundPipelineFactory, PUBCHEM_COMPOUND_SCHEMA
)
