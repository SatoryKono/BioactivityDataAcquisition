"""Golden hash tests for high-risk ChEMBL JSON canonicalization seams."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)

SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "chembl_high_risk_hashes.json"

_CASE_PAYLOADS: dict[str, tuple[str, dict[str, object]]] = {
    "target_component_key_order_a": (
        "target_component",
        {
            "component_id": 1,
            "target_component_xrefs": '[{"xref_id":"P1","xref_src_db":"PDBe","xref_name":"A"}]',
        },
    ),
    "target_component_key_order_b": (
        "target_component",
        {
            "component_id": 1,
            "target_component_xrefs": '[{"xref_name":"A","xref_src_db":"PDBe","xref_id":"P1"}]',
        },
    ),
    "target_component_list_order_a": (
        "target_component",
        {
            "component_id": 1,
            "target_component_xrefs": '[{"xref_id":"P1","xref_src_db":"PDBe","xref_name":"A"},{"xref_id":"P2","xref_src_db":"InterPro","xref_name":"B"}]',
        },
    ),
    "target_component_list_order_b": (
        "target_component",
        {
            "component_id": 1,
            "target_component_xrefs": '[{"xref_id":"P2","xref_src_db":"InterPro","xref_name":"B"},{"xref_id":"P1","xref_src_db":"PDBe","xref_name":"A"}]',
        },
    ),
    "target_component_types_a": (
        "target",
        {"target_id": "CHEMBL1", "component_types": '["PROTEIN","DNA"]'},
    ),
    "target_component_types_b": (
        "target",
        {"target_id": "CHEMBL1", "component_types": '["DNA","PROTEIN"]'},
    ),
    "publication_orcids_a": (
        "publication",
        {
            "publication_id": "CHEMBL1",
            "author_orcids": '["0000-0002-1825-0097","0000-0001-5109-3700"]',
        },
    ),
    "publication_orcids_b": (
        "publication",
        {
            "publication_id": "CHEMBL1",
            "author_orcids": '["0000-0001-5109-3700","0000-0002-1825-0097"]',
        },
    ),
    "publication_authors_a": (
        "publication",
        {"publication_id": "CHEMBL1", "authors": '["Alice","Bob"]'},
    ),
    "publication_authors_b": (
        "publication",
        {"publication_id": "CHEMBL1", "authors": '["Bob","Alice"]'},
    ),
}


def _compute_snapshot() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for case_name, (entity_type, payload) in _CASE_PAYLOADS.items():
        processor = RecordNormalizationProcessor(
            provider="chembl", entity_type=entity_type
        )
        normalized = processor.normalize_business_data(payload)
        hashes[case_name] = processor.compute_content_hash(normalized)
    return hashes


def test_chembl_high_risk_hashes_match_golden_snapshot() -> None:
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert _compute_snapshot() == expected


def test_chembl_high_risk_hash_contracts_encode_intended_ordering_rules() -> None:
    snapshot = _compute_snapshot()

    assert (
        snapshot["target_component_key_order_a"]
        == snapshot["target_component_key_order_b"]
    )
    assert (
        snapshot["target_component_list_order_a"]
        != snapshot["target_component_list_order_b"]
    )
    assert snapshot["target_component_types_a"] == snapshot["target_component_types_b"]
    assert snapshot["publication_orcids_a"] == snapshot["publication_orcids_b"]
    assert snapshot["publication_authors_a"] != snapshot["publication_authors_b"]
