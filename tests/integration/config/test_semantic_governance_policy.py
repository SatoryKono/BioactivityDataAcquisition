"""Contract checks for semantic governance policy over residual ETL audit debt."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from bioetl.domain.contracts.gold.composite import CompositeActivityGoldSchema
from bioetl.infrastructure.schemas.silver_common_field_blocks import (
    build_silver_dq_suffix_fields,
    build_silver_lookup_prefix_fields,
    build_silver_system_prefix_fields,
)
from scripts.engineering.qa.check_semantic_governance_policy import (
    DEFAULT_REVIEW_REGISTRY,
    validate_semantic_governance_policy,
)

COMPOSITE_AUTHORITY_REGISTRY = Path(
    "configs/field_registry/composite_schema_authority_registry.yaml"
)


def _matrix_type_from_pyarrow(field_type: object) -> str:
    return {
        "string": "string",
        "int64": "int64",
        "bool": "bool",
    }[str(field_type).strip().lower()]


def test_semantic_governance_policy_gate_passes_current_repo() -> None:
    findings = validate_semantic_governance_policy()

    assert not findings, "\n".join(finding.message for finding in findings)


def test_partial_cluster_policies_cover_current_reviewed_identity_clusters() -> None:
    payload = yaml.safe_load(DEFAULT_REVIEW_REGISTRY.read_text(encoding="utf-8"))

    policies = payload["partial_cluster_policies"]
    assert {entry["cluster_id"] for entry in policies} == {
        "canonical_smiles_identifier",
        "chembl_target_identifier",
        "inchi_key_identifier",
        "pmc_identifier",
        "uniprot_accession_identifier",
    }
    for entry in policies:
        assert entry["promotion_policy"] == "require_explicit_owner_split_before_exact"
        assert entry["business_owner_role"]
        assert entry["composite_role"]
        assert entry["lineage_role"]


def test_weak_cluster_decisions_cover_current_high_frequency_inventory() -> None:
    payload = yaml.safe_load(DEFAULT_REVIEW_REGISTRY.read_text(encoding="utf-8"))

    policy = payload["weak_cluster_policy"]
    decisions = payload["weak_cluster_decisions"]

    assert policy["weak_decision_min_rows"] == 6
    assert len(decisions) >= 20
    assert {
        entry["cluster_id"]
        for entry in decisions
    } >= {
        "shared_pref_name",
        "shared_author_keys",
        "shared_author_orcids",
        "shared_is_oa",
        "shared_language",
        "shared_assay_type",
        "shared_bao_format",
        "shared_bao_label",
        "shared_issn",
        "shared_oa_status",
        "shared_annotation_score",
        "shared_cross_references",
        "shared_abstract",
        "shared_authors",
        "shared_issue",
        "shared_publication_class",
        "shared_publication_date",
        "shared_publication_subclass",
        "shared_publication_type_unified",
        "shared_volume",
    }


def test_publication_weak_clusters_are_explicit_promotable_candidates() -> None:
    payload = yaml.safe_load(DEFAULT_REVIEW_REGISTRY.read_text(encoding="utf-8"))

    decisions = {
        entry["cluster_id"]: entry["decision"]
        for entry in payload["weak_cluster_decisions"]
    }

    assert {
        "shared_abstract",
        "shared_authors",
        "shared_issue",
        "shared_publication_class",
        "shared_publication_date",
        "shared_publication_subclass",
        "shared_publication_type_unified",
        "shared_volume",
    } <= set(decisions)
    for cluster_id in (
        "shared_abstract",
        "shared_authors",
        "shared_issue",
        "shared_publication_class",
        "shared_publication_date",
        "shared_publication_subclass",
        "shared_publication_type_unified",
        "shared_volume",
    ):
        assert decisions[cluster_id] == "promotable_candidate"


def test_promotion_requirements_define_machine_enforced_evidence_contracts() -> None:
    payload = yaml.safe_load(DEFAULT_REVIEW_REGISTRY.read_text(encoding="utf-8"))

    requirements = payload["promotion_requirements"]
    assert {
        "business_owner_identity",
        "composite_role",
        "join_semantics",
        "lineage_role",
        "normalization_parity",
        "dq_parity",
        "gold_contract_compatibility",
    } <= set(requirements["PARTIAL"]["required_evidence"])
    assert {
        "canonical_owner",
        "ontology_meaning",
        "join_usage_proof",
        "lineage_role",
        "normalization_parity",
        "dq_parity",
        "gold_contract_compatibility",
    } <= set(requirements["WEAK"]["required_evidence"])
    assert {
        "explicit_owner_registry",
        "non_aliasability_rationale",
    } <= set(requirements["CONFLICTING"]["required_evidence"])


def test_semantic_governance_workflow_runs_policy_gate() -> None:
    workflow = Path(".github/workflows/semantic-governance.yml").read_text(
        encoding="utf-8"
    )

    assert "check-semantic-governance-policy --check --json" in workflow
    assert "tests/integration/config/test_semantic_governance_policy.py" in workflow


def test_composite_unknown_typing_reviews_retire_after_contract_shim() -> None:
    payload = yaml.safe_load(DEFAULT_REVIEW_REGISTRY.read_text(encoding="utf-8"))

    assert payload["composite_unknown_typing_reviews"] == []


def test_composite_schema_authority_registry_matches_shared_system_field_blocks() -> None:
    payload = yaml.safe_load(COMPOSITE_AUTHORITY_REGISTRY.read_text(encoding="utf-8"))
    authorities = {entry["id"]: entry for entry in payload["authorities"]}
    system_authority = authorities["medallion_system_metadata_contract"]

    actual_types = {
        field.name: _matrix_type_from_pyarrow(field.type)
        for field in (
            [
                *build_silver_system_prefix_fields(include_source=True),
                *build_silver_lookup_prefix_fields(),
                *build_silver_dq_suffix_fields(),
            ]
        )
    }

    assert system_authority["field_types"] == {
        field_name: actual_types[field_name]
        for field_name in system_authority["field_types"]
    }


def test_composite_schema_authority_registry_matches_activity_taxonomy_contract() -> None:
    payload = yaml.safe_load(COMPOSITE_AUTHORITY_REGISTRY.read_text(encoding="utf-8"))
    authorities = {entry["id"]: entry for entry in payload["authorities"]}
    activity_authority = authorities["seed_and_provider_gold_contracts"]

    schema = CompositeActivityGoldSchema.to_schema()
    assert (
        activity_authority["field_types"]["taxonomy_id"]
        == _matrix_type_from_pyarrow(schema.columns["taxonomy_id"].dtype)
    )

    contract = json.loads(
        Path("docs/04-reference/contracts/gold/composite_activity_v1.0.json").read_text(
            encoding="utf-8"
        )
    )
    assert contract["properties"]["taxonomy_id"]["type"] == ["integer", "null"]
