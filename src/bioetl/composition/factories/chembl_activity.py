"""ChEMBL Activity pipeline factory.

Migrated to use GenericPipelineFactory for reduced boilerplate.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline
from bioetl.application.registry import PipelineRegistry
from bioetl.composition.factories.generic_pipeline_factory import (
    GenericPipelineFactory,
)
from bioetl.infrastructure.schemas.silver import CHEMBL_ACTIVITY_SCHEMA

if TYPE_CHECKING:
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


# New factory using GenericPipelineFactory
chembl_activity_factory = GenericPipelineFactory(
    pipeline_class=ChEMBLActivityPipeline,
    pipeline_name="chembl_activity",
    provider="chembl",
    silver_schema=CHEMBL_ACTIVITY_SCHEMA,
)


# Register with PipelineRegistry
PipelineRegistry.register(
    "chembl_activity", chembl_activity_factory, CHEMBL_ACTIVITY_SCHEMA
)


# Deprecated class for backwards compatibility
class ChEMBLActivityPipelineFactory:
    """Factory for creating ChEMBL Activity pipelines.

    .. deprecated:: 1.0
        Use ``chembl_activity_factory`` instead. This class will be removed
        in a future version.
    """

    pipeline_name = "chembl_activity"
    pipeline_class = ChEMBLActivityPipeline
    silver_schema = CHEMBL_ACTIVITY_SCHEMA

    def __init__(self) -> None:
        warnings.warn(
            "ChEMBLActivityPipelineFactory is deprecated. "
            "Use chembl_activity_factory (GenericPipelineFactory) instead.",
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
        """Create ChEMBL data source.

        .. deprecated:: 1.0
            Use chembl_activity_factory.create_data_source() instead.
        """
        warnings.warn(
            "ChEMBLActivityPipelineFactory.create_data_source is deprecated. "
            "Use chembl_activity_factory.create_data_source() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return chembl_activity_factory.create_data_source(
            settings, pipeline_config, filter_config
        )

    @classmethod
    def build_services(cls, *args, **kwargs):
        """Build services.

        .. deprecated:: 1.0
            Use chembl_activity_factory.build_services() instead.
        """
        warnings.warn(
            "ChEMBLActivityPipelineFactory.build_services is deprecated. "
            "Use chembl_activity_factory.build_services() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return chembl_activity_factory.build_services(*args, **kwargs)

    @classmethod
    def create_with_services(cls, *args, **kwargs):
        """Create pipeline with services.

        .. deprecated:: 1.0
            Use chembl_activity_factory.create_with_services() instead.
        """
        warnings.warn(
            "ChEMBLActivityPipelineFactory.create_with_services is deprecated. "
            "Use chembl_activity_factory.create_with_services() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return chembl_activity_factory.create_with_services(*args, **kwargs)
