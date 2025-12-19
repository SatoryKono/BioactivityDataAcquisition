"""PubMed Publications pipeline factory.

Migrated to use GenericPipelineFactory for reduced boilerplate.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from bioetl.application.pipelines.pubmed.publications import PubMedPublicationsPipeline
from bioetl.application.registry import PipelineRegistry
from bioetl.composition.factories.generic_pipeline_factory import (
    GenericPipelineFactory,
)
from bioetl.infrastructure.schemas.silver import PUBMED_PUBLICATION_SCHEMA

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


# New factory using GenericPipelineFactory
pubmed_publications_factory = GenericPipelineFactory(
    pipeline_class=PubMedPublicationsPipeline,
    pipeline_name="pubmed_publications",
    provider="pubmed",
    silver_schema=PUBMED_PUBLICATION_SCHEMA,
)


# Register with PipelineRegistry
PipelineRegistry.register(
    "pubmed_publications", pubmed_publications_factory, PUBMED_PUBLICATION_SCHEMA
)


# Deprecated class for backwards compatibility
class PubMedPublicationsPipelineFactory:
    """Фабрика для создания пайплайна PubMed Publications.

    .. deprecated:: 1.0
        Используйте ``pubmed_publications_factory`` вместо этого класса.
        Класс будет удалён в будущих версиях.
    """

    pipeline_name = "pubmed_publications"
    pipeline_class = PubMedPublicationsPipeline
    silver_schema = PUBMED_PUBLICATION_SCHEMA

    def __init__(self) -> None:
        warnings.warn(
            "PubMedPublicationsPipelineFactory is deprecated. "
            "Use pubmed_publications_factory (GenericPipelineFactory) instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    @classmethod
    def create_data_source(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
    ) -> DataSourcePort:
        """Создает источник данных PubMed.

        .. deprecated:: 1.0
            Используйте pubmed_publications_factory.create_data_source().
        """
        warnings.warn(
            "PubMedPublicationsPipelineFactory.create_data_source is deprecated. "
            "Use pubmed_publications_factory.create_data_source() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return pubmed_publications_factory.create_data_source(settings, pipeline_config)

    @classmethod
    def build_services(cls, *args, **kwargs):
        """Build services.

        .. deprecated:: 1.0
            Используйте pubmed_publications_factory.build_services().
        """
        warnings.warn(
            "PubMedPublicationsPipelineFactory.build_services is deprecated. "
            "Use pubmed_publications_factory.build_services() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return pubmed_publications_factory.build_services(*args, **kwargs)

    @classmethod
    def create_with_services(cls, *args, **kwargs):
        """Create pipeline with services.

        .. deprecated:: 1.0
            Используйте pubmed_publications_factory.create_with_services().
        """
        warnings.warn(
            "PubMedPublicationsPipelineFactory.create_with_services is deprecated. "
            "Use pubmed_publications_factory.create_with_services() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return pubmed_publications_factory.create_with_services(*args, **kwargs)
