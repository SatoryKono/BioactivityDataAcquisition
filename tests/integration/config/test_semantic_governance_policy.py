"""Contract checks for semantic governance policy over residual ETL audit debt."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.engineering.qa.check_semantic_governance_policy import (
    DEFAULT_REVIEW_REGISTRY,
    validate_semantic_governance_policy,
)


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
    assert len(decisions) >= 12
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
    }


def test_promoted_publication_candidates_are_no_longer_reviewed_as_weak_inventory() -> None:
    payload = yaml.safe_load(DEFAULT_REVIEW_REGISTRY.read_text(encoding="utf-8"))

    decisions = {entry["cluster_id"] for entry in payload["weak_cluster_decisions"]}

    assert {
        "shared_abstract",
        "shared_authors",
        "shared_issue",
        "shared_publication_class",
        "shared_publication_date",
        "shared_publication_subclass",
        "shared_publication_type_unified",
        "shared_volume",
    }.isdisjoint(decisions)


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
