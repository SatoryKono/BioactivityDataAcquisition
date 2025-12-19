"""UniProt Protein pipeline factory.

Migrated to use GenericPipelineFactory for reduced boilerplate.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from bioetl.application.pipelines.uniprot.protein import UniProtProteinPipeline
from bioetl.application.registry import PipelineRegistry
from bioetl.composition.factories.generic_pipeline_factory import (
    GenericPipelineFactory,
)
from bioetl.infrastructure.schemas.silver import UNIPROT_PROTEIN_SCHEMA

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


# New factory using GenericPipelineFactory
uniprot_protein_factory = GenericPipelineFactory(
    pipeline_class=UniProtProteinPipeline,
    pipeline_name="uniprot_protein",
    provider="uniprot",
    silver_schema=UNIPROT_PROTEIN_SCHEMA,
)


# Register with PipelineRegistry
PipelineRegistry.register(
    "uniprot_protein", uniprot_protein_factory, UNIPROT_PROTEIN_SCHEMA
)


# Deprecated class for backwards compatibility
class UniProtProteinPipelineFactory:
    """Factory for creating UniProt Protein pipelines.

    .. deprecated:: 1.0
        Use ``uniprot_protein_factory`` instead. This class will be removed
        in a future version.
    """

    pipeline_name = "uniprot_protein"
    pipeline_class = UniProtProteinPipeline
    silver_schema = UNIPROT_PROTEIN_SCHEMA

    def __init__(self) -> None:
        warnings.warn(
            "UniProtProteinPipelineFactory is deprecated. "
            "Use uniprot_protein_factory (GenericPipelineFactory) instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    @classmethod
    def create_data_source(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
    ) -> DataSourcePort:
        """Create UniProt data source.

        .. deprecated:: 1.0
            Use uniprot_protein_factory.create_data_source() instead.
        """
        warnings.warn(
            "UniProtProteinPipelineFactory.create_data_source is deprecated. "
            "Use uniprot_protein_factory.create_data_source() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return uniprot_protein_factory.create_data_source(settings, pipeline_config)

    @classmethod
    def build_services(cls, *args, **kwargs):
        """Build services.

        .. deprecated:: 1.0
            Use uniprot_protein_factory.build_services() instead.
        """
        warnings.warn(
            "UniProtProteinPipelineFactory.build_services is deprecated. "
            "Use uniprot_protein_factory.build_services() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return uniprot_protein_factory.build_services(*args, **kwargs)

    @classmethod
    def create_with_services(cls, *args, **kwargs):
        """Create pipeline with services.

        .. deprecated:: 1.0
            Use uniprot_protein_factory.create_with_services() instead.
        """
        warnings.warn(
            "UniProtProteinPipelineFactory.create_with_services is deprecated. "
            "Use uniprot_protein_factory.create_with_services() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return uniprot_protein_factory.create_with_services(*args, **kwargs)
