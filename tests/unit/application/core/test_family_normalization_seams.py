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
from bioetl.application.core.factory_wiring_api import PipelineRunner as PipelineRunnerLegacy
from bioetl.application.core.filtered_data_source import (
    FilteredDataSource as FilteredDataSourceLegacy,
)
from bioetl.application.core.idmapping_data_source import (
    IDMappingDataSource as IDMappingDataSourceLegacy,
)
from bioetl.application.core.publication_term_data_source import (
    PublicationTermDataSource as PublicationTermDataSourceLegacy,
)
from bioetl.application.core.subcellular_fraction_data_source import (
    SubcellularFractionDataSource as SubcellularFractionDataSourceLegacy,
)
from bioetl.application.core.wiring.factory import PipelineRunner
from bioetl.application.core.wiring.registry import GenericPipeline
from bioetl.application.core.wiring.runtime import BatchExecutionRunService
from bioetl.application.core.wiring.transformer import BaseTransformer


pytestmark = pytest.mark.unit


def test_legacy_wiring_facades_point_to_new_wiring_package() -> None:
    assert PipelineRunnerLegacy is PipelineRunner
    assert BatchExecutionRunService is BatchExecutionRunService
    assert BaseTransformer is BaseTransformer
    assert GenericPipeline is GenericPipeline


def test_legacy_data_source_facades_point_to_new_data_source_package() -> None:
    assert FilteredDataSourceLegacy is FilteredDataSource
    assert FilteredDataSourcePackage is FilteredDataSource
    assert IDMappingDataSourceLegacy is IDMappingDataSource
    assert IDMappingDataSourcePackage is IDMappingDataSource
    assert PublicationTermDataSourceLegacy is PublicationTermDataSource
    assert PublicationTermDataSourcePackage is PublicationTermDataSource
    assert SubcellularFractionDataSourceLegacy is SubcellularFractionDataSource
    assert SubcellularFractionDataSourcePackage is SubcellularFractionDataSource
