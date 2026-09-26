"""Owner test for composite_assay (#11178)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.composition.factories.storage.bundle import StorageBundle

pytestmark = pytest.mark.unit

_CONFIG = (
    Path(__file__).resolve().parents[4]
    / "configs"
    / "entities"
    / "composite"
    / "assay.yaml"
)


def test_entity_config_names_composite_assay_pipeline() -> None:
    document = yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))
    assert document["pipeline"]["pipeline_name"] == "composite_assay"
    assert document["pipeline"]["entity_type"] == "assay"


def test_storage_bundle_resolves_composite_assay_schema() -> None:
    schema = StorageBundle._COMPOSITE_GOLD_SCHEMAS["composite_assay"]
    assert schema.__name__ == "CompositeAssayGoldSchema"
