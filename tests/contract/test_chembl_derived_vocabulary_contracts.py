"""Contract tests for ChEMBL raw/canonical derived-vocabulary surfaces."""

from __future__ import annotations

import pytest

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


def test_chembl_assay_parameter_type_raw_and_canonical_fields_stay_distinct() -> None:
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="assay_parameters",
    )

    normalized = processor.normalize_business_data(
        {
            "type_raw": " custom window ",
            "type": " custom window ",
            "standard_type": "TEMP",
        }
    )

    assert normalized["type_raw"] == "custom window"
    assert normalized["type"] == "CUSTOM WINDOW"
    assert normalized["standard_type"] == "TEMP"


def test_chembl_subcellular_fraction_raw_and_canonical_fields_stay_distinct() -> None:
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="subcellular_fraction",
    )

    normalized = processor.normalize_business_data(
        {
            "subcellular_fraction_raw": " outer leaflet ",
            "subcellular_fraction": " outer leaflet ",
        }
    )

    assert normalized["subcellular_fraction_raw"] == "outer leaflet"
    assert normalized["subcellular_fraction"] == "outer leaflet"


def test_chembl_publication_raw_and_canonical_type_sidecars_remain_independent() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="publication",
    )

    normalized = processor.normalize_business_data(
        {
            "publication_id": "CHEMBL9000001",
            "title": "Edge dataset publication",
            "publication_type_raw": " dataset ",
            "publication_type": "DATASET",
        }
    )

    assert normalized["publication_type_raw"] == "DATASET"
    assert normalized["publication_type"] == "dataset"
