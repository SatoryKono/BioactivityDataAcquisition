"""Regressions from immutable limit-1000 ChEMBL acquisition evidence."""

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from bioetl.application.core.base_transformer_runtime import serialize_json_fields
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
from bioetl.domain.config.validation_config import ValidationConfig

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "weight,valid",
    [
        (46.07, True),
        (92.09, True),
        (1500, True),
        (10, True),
        (10000, True),
        (9, False),
        (10001, False),
    ],
)
def test_molecule_range_matches_canonical_domain_contract(weight, valid):
    root = Path(__file__).resolve().parents[3]
    payload = yaml.safe_load(
        (root / "configs/entities/chembl/molecule.yaml").read_text(encoding="utf-8")
    )
    rule = next(
        rule
        for rule in payload["quality"]["entity_field_validations"]
        if rule["field"] == "molecular_weight"
    )
    canonical = ValidationConfig()
    assert (rule["min"], rule["max"]) == (
        canonical.min_molecular_weight,
        canonical.max_molecular_weight,
    )
    assert (rule["min"] <= weight <= rule["max"]) is valid


@pytest.mark.parametrize("codes", [[], ["J01DB03"], ["N02AA59", "R05DA04"]])
def test_molecule_atc_list_survives_full_normalization(codes):
    host = SimpleNamespace(
        validate_value_object=lambda cls, value: value,
        serialize_json_fields=lambda record, fields: serialize_json_fields(
            record=record, field_names=fields
        ),
    )
    extracted = MoleculeTransformer._extract_business_data(
        host, {"atc_classifications": codes}, "CHEMBL617"
    )
    processor = RecordNormalizationProcessor(provider="chembl", entity_type="molecule")
    normalized = processor.normalize_business_data(extracted)
    assert (
        normalized["atc_classifications"] is None
        if not codes
        else json.loads(normalized["atc_classifications"]) == codes
    )
    assert not processor.normalization_findings


@pytest.mark.parametrize("entity", ["tissue", "cell_line"])
@pytest.mark.parametrize("raw", ["EFO;0000992", "EFO:0000992", "EFO_0000992"])
def test_efo_provider_separator_preserves_ontology_bundle(raw, entity):
    processor = RecordNormalizationProcessor(provider="chembl", entity_type=entity)
    normalized = processor.normalize_business_data(
        {"efo_id": raw, "efo_iri": None, "efo_mapping_status": None}
    )
    assert normalized["efo_id"] == "EFO_0000992"
    assert normalized["efo_iri"].endswith("/EFO_0000992")
    assert normalized["efo_mapping_status"] == "mapped"


@pytest.mark.parametrize("entity", ["tissue", "cell_line"])
@pytest.mark.parametrize("raw", ["EFO;garbage", "EFO;0000992;other", "OTHER;0000992"])
def test_efo_unknown_identifiers_still_fail_canonical_pattern(raw, entity):
    processor = RecordNormalizationProcessor(provider="chembl", entity_type=entity)
    normalized = processor.normalize_business_data({"efo_id": raw})
    assert re.fullmatch(r"EFO_\d+", normalized["efo_id"]) is None
