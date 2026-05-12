"""Golden normalization/hash tests for high-risk ChEMBL profiles."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)

GOLDEN_DIR = Path("tests/golden/normalization/chembl")

RAW_CASES: dict[str, tuple[str, dict[str, object]]] = {
    "activity": (
        "activity",
        {
            "activity_id": " ACT-001 ",
            "standard_relation": " ≤ ",
            "standard_type": "IC50",
            "standard_units": " uM ",
            "activity_properties": '["beta","alpha"]',
        },
    ),
    "publication": (
        "publication",
        {
            "publication_id": "CHEMBL123",
            "title": " Example dataset ",
            "publication_type_raw": " dataset ",
            "publication_type": "DATASET",
            "publication_doi": " HTTPS://doi.org/10.1000/XYZ ",
            "publication_pmid": " 00012345 ",
            "issn_list": ["ISSN:1234567X", "2049-3630"],
            "oa_status": " GREEN ",
        },
    ),
    "target": (
        "target",
        {
            "pref_name": " Example Target ",
            "target_type": " single protein ",
            "component_types": '["DNA","PROTEIN"]',
            "component_relationships": '["RNA","PROTEIN SUBUNIT"]',
        },
    ),
    "target_component": (
        "target_component",
        {
            "component_id": 77,
            "component_type": " protein ",
            "accession": " p12345 ",
            "target_component_xrefs": '[{"xref_id":"P12345","xref_src_db":"UniProt"},{"xref_id":"GO:0003677","xref_src_db":"GoFunction"}]',
        },
    ),
    "molecule": (
        "molecule",
        {
            "pref_name": " Example Molecule ",
            "molecule_type": " small molecule ",
            "structure_type": " mol ",
            "max_phase": "0.5",
            "molecule_synonyms": '[{"molecule_synonym":"Example"},{"molecule_synonym":"Alt"}]',
        },
    ),
}


def _load_golden(name: str) -> dict[str, object]:
    return json.loads((GOLDEN_DIR / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(RAW_CASES))
def test_chembl_normalization_payload_and_hash_match_golden(name: str) -> None:
    entity_type, raw = RAW_CASES[name]
    processor = RecordNormalizationProcessor(provider="chembl", entity_type=entity_type)
    golden = _load_golden(name)

    normalized = processor.normalize_business_data(dict(raw))

    assert normalized == golden["normalized"]
    assert processor.compute_content_hash(normalized) == golden["content_hash"]


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(RAW_CASES))
def test_chembl_hash_excludes_runtime_meta_fields(name: str) -> None:
    entity_type, raw = RAW_CASES[name]
    processor = RecordNormalizationProcessor(provider="chembl", entity_type=entity_type)
    normalized = processor.normalize_business_data(dict(raw))

    baseline_hash = processor.compute_content_hash(normalized)
    with_runtime_meta = {
        **normalized,
        "_run_id": "run-a",
        "_ingestion_ts": "2026-05-11T00:00:00Z",
        "_index": 7,
        "_source_batch_id": "batch-a",
    }
    with_other_runtime_meta = {
        **normalized,
        "_run_id": "run-b",
        "_ingestion_ts": "2026-05-12T00:00:00Z",
        "_index": 99,
        "_source_batch_id": "batch-b",
    }

    assert processor.compute_content_hash(with_runtime_meta) == baseline_hash
    assert processor.compute_content_hash(with_other_runtime_meta) == baseline_hash


@pytest.mark.unit
def test_chembl_set_like_and_order_sensitive_hash_contracts_hold() -> None:
    activity_processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )
    activity_left = activity_processor.normalize_business_data(
        {"activity_properties": '["beta","alpha"]'}
    )
    activity_right = activity_processor.normalize_business_data(
        {"activity_properties": '["alpha","beta"]'}
    )
    assert activity_processor.compute_content_hash(
        activity_left
    ) == activity_processor.compute_content_hash(activity_right)

    target_processor = RecordNormalizationProcessor(
        provider="chembl", entity_type="target"
    )
    target_left = target_processor.normalize_business_data(
        {"component_types": '["DNA","PROTEIN"]'}
    )
    target_right = target_processor.normalize_business_data(
        {"component_types": '["PROTEIN","DNA"]'}
    )
    assert target_processor.compute_content_hash(
        target_left
    ) == target_processor.compute_content_hash(target_right)

    target_component_processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="target_component",
    )
    ordered_left = target_component_processor.normalize_business_data(
        {
            "target_component_xrefs": '[{"xref_id":"P12345","xref_src_db":"UniProt"},{"xref_id":"GO:0003677","xref_src_db":"GoFunction"}]'
        }
    )
    ordered_right = target_component_processor.normalize_business_data(
        {
            "target_component_xrefs": '[{"xref_id":"GO:0003677","xref_src_db":"GoFunction"},{"xref_id":"P12345","xref_src_db":"UniProt"}]'
        }
    )
    assert target_component_processor.compute_content_hash(
        ordered_left
    ) != target_component_processor.compute_content_hash(ordered_right)
