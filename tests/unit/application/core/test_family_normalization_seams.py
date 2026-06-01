from __future__ import annotations

import pytest

from bioetl.application.core.data_sources import (
    FilteredDataSource as FilteredDataSourcePackage,
)
from bioetl.application.core.data_sources import (
    IDMappingDataSource as IDMappingDataSourcePackage,
)
from bioetl.application.core.data_sources import (
    PublicationTermDataSource as PublicationTermDataSourcePackage,
)
from bioetl.application.core.data_sources import (
    SubcellularFractionDataSource as SubcellularFractionDataSourcePackage,
)
from bioetl.application.core.data_sources.filtered import FilteredDataSource
from bioetl.application.core.data_sources.idmapping import IDMappingDataSource
from bioetl.application.core.data_sources.publication_term import (
    PublicationTermDataSource,
)
from bioetl.application.core.data_sources.subcellular_fraction import (
    SubcellularFractionDataSource,
)
from bioetl.application.core.factory_wiring_api import PipelineRunner
from bioetl.application.core.filtered_data_source import (
    FilteredDataSource as FilteredDataSourceLegacy,
)
from bioetl.application.core.idmapping_data_source import (
    IDMappingDataSource as IDMappingDataSourceLegacy,
)
from bioetl.application.core.pipeline_registry_wiring_api import GenericPipeline
from bioetl.application.core.publication_term_data_source import (
    PublicationTermDataSource as PublicationTermDataSourceLegacy,
)
from bioetl.application.core.runtime_wiring_api import BatchExecutionRunService
from bioetl.application.core.subcellular_fraction_data_source import (
    SubcellularFractionDataSource as SubcellularFractionDataSourceLegacy,
)
from bioetl.application.core.transformer_wiring_api import BaseTransformer
from bioetl.application.core.wiring import BatchExecutionRunService as RuntimePackage
from bioetl.application.core.wiring import BaseTransformer as TransformerPackage
from bioetl.application.core.wiring import GenericPipeline as RegistryPackage
from bioetl.application.core.wiring import PipelineRunner as FactoryPackage


pytestmark = pytest.mark.unit

def test_legacy_wiring_facades_point_to_new_wiring_package() -> None:
    assert PipelineRunner is FactoryPackage
    assert BatchExecutionRunService is RuntimePackage
    assert BaseTransformer is TransformerPackage
    assert GenericPipeline is RegistryPackage


def test_legacy_data_source_facades_point_to_new_data_source_package() -> None:
    assert FilteredDataSourceLegacy is FilteredDataSource
    assert FilteredDataSourcePackage is FilteredDataSource
    assert IDMappingDataSourceLegacy is IDMappingDataSource
    assert IDMappingDataSourcePackage is IDMappingDataSource
    assert PublicationTermDataSourceLegacy is PublicationTermDataSource
    assert PublicationTermDataSourcePackage is PublicationTermDataSource
    assert SubcellularFractionDataSourceLegacy is SubcellularFractionDataSource
    assert SubcellularFractionDataSourcePackage is SubcellularFractionDataSource
