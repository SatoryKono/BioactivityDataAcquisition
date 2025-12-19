"""PubChem Compound pipeline factory.

Migrated to use GenericPipelineFactory for reduced boilerplate.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from bioetl.application.pipelines.pubchem.compound import PubChemCompoundPipeline
from bioetl.application.registry import PipelineRegistry
from bioetl.composition.factories.generic_pipeline_factory import (
    GenericPipelineFactory,
)
from bioetl.infrastructure.schemas.silver import PUBCHEM_COMPOUND_SCHEMA

if TYPE_CHECKING:
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


# New factory using GenericPipelineFactory
pubchem_compound_factory = GenericPipelineFactory(
    pipeline_class=PubChemCompoundPipeline,
    pipeline_name="pubchem_compound",
    provider="pubchem",
    silver_schema=PUBCHEM_COMPOUND_SCHEMA,
)


# Register with PipelineRegistry
PipelineRegistry.register(
    "pubchem_compound", pubchem_compound_factory, PUBCHEM_COMPOUND_SCHEMA
)


# Deprecated class for backwards compatibility
class PubChemCompoundPipelineFactory:
    """Factory for creating PubChem Compound pipelines.

    .. deprecated:: 1.0
        Use ``pubchem_compound_factory`` instead. This class will be removed
        in a future version.
    """

    pipeline_name = "pubchem_compound"
    pipeline_class = PubChemCompoundPipeline
    silver_schema = PUBCHEM_COMPOUND_SCHEMA

    def __init__(self) -> None:
        warnings.warn(
            "PubChemCompoundPipelineFactory is deprecated. "
            "Use pubchem_compound_factory (GenericPipelineFactory) instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    @classmethod
    def create_data_source(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        """Create PubChem data source.

        .. deprecated:: 1.0
            Use pubchem_compound_factory.create_data_source() instead.
        """
        warnings.warn(
            "PubChemCompoundPipelineFactory.create_data_source is deprecated. "
            "Use pubchem_compound_factory.create_data_source() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return pubchem_compound_factory.create_data_source(
            settings, pipeline_config, filter_config
        )

    @classmethod
    def build_services(cls, *args, **kwargs):
        """Build services.

        .. deprecated:: 1.0
            Use pubchem_compound_factory.build_services() instead.
        """
        warnings.warn(
            "PubChemCompoundPipelineFactory.build_services is deprecated. "
            "Use pubchem_compound_factory.build_services() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return pubchem_compound_factory.build_services(*args, **kwargs)

    @classmethod
    def create_with_services(cls, *args, **kwargs):
        """Create pipeline with services.

        .. deprecated:: 1.0
            Use pubchem_compound_factory.create_with_services() instead.
        """
        warnings.warn(
            "PubChemCompoundPipelineFactory.create_with_services is deprecated. "
            "Use pubchem_compound_factory.create_with_services() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return pubchem_compound_factory.create_with_services(*args, **kwargs)
