"""Governance checks for expanded UniProt semantic payload registry."""

from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.domain.normalization.structured_payload_policies import (
    structured_payload_policy,
)
from scripts.engineering.qa.extract_uniprot_semantic_payload_vocab import (
    extract_uniprot_semantic_payload_vocab,
)

_REGISTRY = yaml.safe_load(
    Path("configs/vocab/uniprot_semantic_payloads.yaml").read_text(encoding="utf-8")
)["protein"]
_PIPELINE_CONFIG = yaml.safe_load(
    Path("configs/entities/uniprot/protein.yaml").read_text(encoding="utf-8")
)
_BUSINESS_FIELDS = set(_PIPELINE_CONFIG["schema"]["column_groups"][1]["fields"])


def test_uniprot_semantic_payload_registry_covers_observed_fixture_vocab() -> None:
    payload = extract_uniprot_semantic_payload_vocab(
        [
            Path("tests/fixtures/bronze/uniprot/protein/sample_ci_2026-04-24.jsonl"),
            Path(
                "tests/fixtures/bronze/uniprot/protein/sample_edge_semantic_payloads_2026-05-12.jsonl"
            ),
        ]
    )

    assert set(payload["feature_types"]) <= set(_REGISTRY["feature_types"])
    assert set(payload["comment_types"]) <= set(_REGISTRY["comment_types"])
    assert set(payload["keyword_categories"]) <= set(_REGISTRY["keyword_categories"])


def test_uniprot_semantic_payload_registry_declares_profile_backed_field_groups() -> (
    None
):
    for key in (
        "structured_payload_fields",
        "comment_projection_fields",
        "feature_projection_fields",
        "reference_payload_fields",
    ):
        assert set(_REGISTRY[key]) <= _BUSINESS_FIELDS


def test_uniprot_features_policy_points_to_expanded_semantic_registry() -> None:
    policy = structured_payload_policy("uniprot.protein", "features_json")

    assert policy is not None
    assert policy.controlled_vocabulary_source == (
        "configs/vocab/uniprot_semantic_payloads.yaml"
    )
