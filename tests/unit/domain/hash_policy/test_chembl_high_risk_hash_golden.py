"""Golden hash tests for high-risk ChEMBL JSON canonicalization seams."""

from __future__ import annotations

import json

from bioetl.domain.normalization.json import serialize_json_canonical
from bioetl.domain.normalization.profiles import resolve_normalization_profile
from bioetl.domain.transformations.hashing import generate_content_hash

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
            "target_component_xrefs": (
                '[{"xref_id":"P1","xref_src_db":"PDBe","xref_name":"A"},'
                '{"xref_id":"P2","xref_src_db":"InterPro","xref_name":"B"}]'
            ),
        },
    ),
    "target_component_list_order_b": (
        "target_component",
        {
            "component_id": 1,
            "target_component_xrefs": (
                '[{"xref_id":"P2","xref_src_db":"InterPro","xref_name":"B"},'
                '{"xref_id":"P1","xref_src_db":"PDBe","xref_name":"A"}]'
            ),
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

_CHEMBL_HIGH_RISK_HASHES = """{
  "publication_authors_a": "f6e3e81ef0bcffad9ad1f976127099145fdb699507721414dd04869bb0192964",
  "publication_authors_b": "a798eea917b342e247efcd2e5cf77fe385933b3e1d3e06781702f4cd7602b0aa",
  "publication_orcids_a": "2843117562cb5c5b7cdde0dab2b9ea5184550e23c29a8f3cb79674564852d716",
  "publication_orcids_b": "2843117562cb5c5b7cdde0dab2b9ea5184550e23c29a8f3cb79674564852d716",
  "target_component_key_order_a": "eac4f0df898cd286e91b5dd6ac3c68d7fdf27532eb76ce53612830037c66d622",
  "target_component_key_order_b": "eac4f0df898cd286e91b5dd6ac3c68d7fdf27532eb76ce53612830037c66d622",
  "target_component_list_order_a": "20594d592dc2b2939493d8e6bc6dd22058bfdb48d49a132fc87295b50be05ee2",
  "target_component_list_order_b": "752faa86143f5bf5182d0e639ba182ecbddc1a67da6365fb9eecaede2ac11b63",
  "target_component_types_a": "883e1849878c1136b454bdfc83caeca97b184c621fcffda86ed97f029e133ace",
  "target_component_types_b": "883e1849878c1136b454bdfc83caeca97b184c621fcffda86ed97f029e133ace"
}"""


def _normalize_business_data(
    *,
    entity_type: str,
    payload: dict[str, object],
) -> tuple[dict[str, object], object]:
    profile = resolve_normalization_profile("chembl", entity_type)
    assert profile is not None
    normalized: dict[str, object] = {}
    for field_name, value in payload.items():
        rule = profile.rule_for(field_name)
        normalized_value = value if rule is None else rule.apply(value, record=payload)
        if isinstance(normalized_value, dict | list):
            normalized_value = serialize_json_canonical(normalized_value)
        normalized[field_name] = normalized_value
    return normalized, profile


def _compute_snapshot() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for case_name, (entity_type, payload) in _CASE_PAYLOADS.items():
        normalized, profile = _normalize_business_data(
            entity_type=entity_type,
            payload=payload,
        )
        hashes[case_name] = str(
            generate_content_hash(
                normalized,
                "chembl",
                exclude_none=True,
                include_fields=set(profile.hash_included_fields) or None,
                exclude_fields=set(profile.hash_excluded_fields),
                set_like_fields=set(profile.set_like_fields),
            )
        )
    return hashes


def test_chembl_high_risk_hashes_match_golden_snapshot() -> None:
    expected = json.loads(_CHEMBL_HIGH_RISK_HASHES)

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
