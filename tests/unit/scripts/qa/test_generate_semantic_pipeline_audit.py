from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa import generate_semantic_pipeline_audit as audit


pytestmark = pytest.mark.unit


def test_resolve_seed_artifact_prefers_existing_dated_candidate(tmp_path: Path) -> None:
    dated = tmp_path / "semantic_pair_matrix_2026-05-16.csv"
    dated.write_text("header\n", encoding="utf-8")
    older = tmp_path / "semantic_pair_matrix_2026-05-15.csv"
    older.write_text("header\n", encoding="utf-8")

    resolved = audit._resolve_seed_artifact(
        None,
        out_dir=tmp_path,
        prefix=audit.PAIR_MATRIX_PREFIX,
        source_date="2026-05-16",
        suffix=".csv",
    )

    assert resolved == dated


def test_resolve_seed_artifact_falls_back_to_latest_existing_snapshot(
    tmp_path: Path,
) -> None:
    older = tmp_path / "semantic_pair_matrix_2026-05-14.csv"
    older.write_text("header\n", encoding="utf-8")
    latest = tmp_path / "semantic_pair_matrix_2026-05-15.csv"
    latest.write_text("header\n", encoding="utf-8")

    resolved = audit._resolve_seed_artifact(
        None,
        out_dir=tmp_path,
        prefix=audit.PAIR_MATRIX_PREFIX,
        source_date="2026-05-16",
        suffix=".csv",
    )

    assert resolved == latest


def test_resolve_seed_artifact_honors_explicit_override(tmp_path: Path) -> None:
    explicit = tmp_path / "custom.csv"
    explicit.write_text("header\n", encoding="utf-8")
    dated = tmp_path / "semantic_pair_matrix_2026-05-16.csv"
    dated.write_text("header\n", encoding="utf-8")

    resolved = audit._resolve_seed_artifact(
        explicit,
        out_dir=tmp_path,
        prefix=audit.PAIR_MATRIX_PREFIX,
        source_date="2026-05-16",
        suffix=".csv",
    )

    assert resolved == explicit


def test_resolve_seed_artifact_raises_when_no_seed_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    empty_canonical_out_dir = tmp_path / "canonical-empty"
    empty_canonical_out_dir.mkdir()
    monkeypatch.setattr(audit, "DEFAULT_OUT_DIR", empty_canonical_out_dir)

    with pytest.raises(FileNotFoundError, match="Unable to resolve seed artifact"):
        audit._resolve_seed_artifact(
            None,
            out_dir=tmp_path,
            prefix=audit.CLUSTER_REGISTRY_PREFIX,
            source_date="2026-05-16",
            suffix=".json",
        )


def test_resolve_seed_artifact_falls_back_to_canonical_out_dir_for_custom_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical_out_dir = tmp_path / "canonical"
    canonical_out_dir.mkdir()
    latest = canonical_out_dir / "semantic_pair_matrix_2026-05-15.csv"
    latest.write_text("header\n", encoding="utf-8")
    custom_out_dir = tmp_path / "custom"
    custom_out_dir.mkdir()
    monkeypatch.setattr(audit, "DEFAULT_OUT_DIR", canonical_out_dir)

    resolved = audit._resolve_seed_artifact(
        None,
        out_dir=custom_out_dir,
        prefix=audit.PAIR_MATRIX_PREFIX,
        source_date="2026-05-19",
        suffix=".csv",
    )

    assert resolved == latest


def test_resolve_latest_gold_contract_path_prefers_highest_version_over_v1_default(
    tmp_path: Path,
) -> None:
    (tmp_path / "chembl_target_v1.0.json").write_text("{}", encoding="utf-8")
    latest = tmp_path / "chembl_target_v3.0.json"
    latest.write_text("{}", encoding="utf-8")
    (tmp_path / "chembl_target_v2.1.json").write_text("{}", encoding="utf-8")

    resolved = audit.resolve_latest_gold_contract_path(
        "chembl_target",
        contracts_dir=tmp_path,
    )

    assert resolved == latest


def test_resolve_latest_gold_contract_path_returns_default_when_pipeline_missing(
    tmp_path: Path,
) -> None:
    resolved = audit.resolve_latest_gold_contract_path(
        "missing_pipeline",
        contracts_dir=tmp_path,
    )

    assert resolved == tmp_path / "missing_pipeline_v1.0.json"


def test_build_current_member_facts_exposes_composite_inherited_field_types() -> None:
    seed_registry = json.loads(
        Path(
            "tests/fixtures/semantic_pipeline_audit/semantic_cluster_registry_2026-05-16.json"
        ).read_text(encoding="utf-8")
    )

    facts = audit._build_current_member_facts(seed_registry)

    assert facts[("composite_activity", "assay_id")]["field_type"] == "string"
    assert facts[("composite_activity", "molecule_id")]["field_type"] == "string"
    assert facts[("composite_molecule", "hba_count")]["field_type"] == "int64"
    assert facts[("composite_molecule", "logp")]["field_type"] == "double"
    assert facts[("composite_publication", "year")]["field_type"] == "int64"
    assert facts[("composite_target", "target_description")]["field_type"] == "string"


def test_build_current_member_facts_exposes_composite_authority_shim_types() -> None:
    seed_registry = json.loads(
        Path(
            "tests/fixtures/semantic_pipeline_audit/semantic_cluster_registry_2026-05-21.json"
        ).read_text(encoding="utf-8")
    )

    facts = audit._build_current_member_facts(seed_registry)

    assert facts[("composite_activity", "taxonomy_id")]["field_type"] == "int64"
    assert facts[("composite_activity", "_source")]["field_type"] == "string"
    assert facts[("composite_activity", "_lookup_method")]["field_type"] == "string"
    assert facts[("composite_activity", "_original_id")]["field_type"] == "string"
    assert facts[("composite_assay", "_source")]["field_type"] == "string"
    assert facts[("composite_assay", "_lookup_method")]["field_type"] == "string"
    assert facts[("composite_assay", "_original_id")]["field_type"] == "string"
    assert facts[("composite_molecule", "_source")]["field_type"] == "string"
    assert facts[("composite_target", "_source")]["field_type"] == "string"
    assert facts[("composite_target", "_lookup_method")]["field_type"] == "string"
    assert facts[("composite_target", "_original_id")]["field_type"] == "string"


def test_refresh_clusters_rebuilds_canonical_registry_membership_from_current_registry() -> (
    None
):
    seed_registry = json.loads(
        Path(
            "tests/fixtures/semantic_pipeline_audit/semantic_cluster_registry_2026-05-21.json"
        ).read_text(encoding="utf-8")
    )

    facts = audit._build_current_member_facts(seed_registry)
    refreshed = audit._refresh_clusters(
        seed_registry,
        facts,
        review_registry={},
        source_date="2026-05-21",
    )
    cluster_lookup = {
        cluster["cluster_id"]: cluster
        for cluster in refreshed["clusters"]
        if isinstance(cluster, dict)
    }

    chembl_cluster = cluster_lookup["chembl_molecule_identifier"]
    chembl_members = {
        str(member["pipeline"])
        for member in chembl_cluster["members"]
        if isinstance(member, dict)
    }
    assert chembl_members == {
        "chembl_activity",
        "chembl_compound_record",
        "chembl_molecule",
        "composite_activity",
        "composite_molecule",
    }

    pubchem_cluster = cluster_lookup["pubchem_cid_identifier"]
    pubchem_members = {
        str(member["pipeline"])
        for member in pubchem_cluster["members"]
        if isinstance(member, dict)
    }
    assert pubchem_members == {"pubchem_compound"}


def test_refresh_clusters_attaches_tracked_weak_decision_metadata() -> None:
    seed_registry = json.loads(
        Path(
            "tests/fixtures/semantic_pipeline_audit/semantic_cluster_registry_2026-05-21.json"
        ).read_text(encoding="utf-8")
    )
    review_registry_payload = audit._load_yaml(
        Path("configs/field_registry/semantic_audit_review_registry.yaml")
    )

    facts = audit._build_current_member_facts(seed_registry)
    refreshed = audit._refresh_clusters(
        seed_registry,
        facts,
        review_registry=review_registry_payload,
        source_date="2026-05-21",
    )
    cluster_lookup = {
        cluster["cluster_id"]: cluster
        for cluster in refreshed["clusters"]
        if isinstance(cluster, dict)
    }

    bao_format = cluster_lookup["shared_bao_format"]["weak_decision"]
    assert bao_format["decision"] == "source_owned_same_name"
    assert bao_format["semantic_scope"] == "role_governed_ontology_reference_identifier"
    assert "ontology_unit_semantic_roles.yaml" in bao_format["authority_scope"]

    assay_type = cluster_lookup["shared_assay_type"]["weak_decision"]
    assert assay_type["semantic_scope"] == "explicit_source_owned_assay_contract"
    assert (
        assay_type["promotion_policy"]
        == "require_canonical_assay_metadata_registry_before_exact"
    )


def test_dedicated_authority_registries_override_review_projections(
    tmp_path: Path,
) -> None:
    review_path = tmp_path / "review.yaml"
    review_path.write_text(
        "partial_cluster_policies:\n"
        "  - cluster_id: identifier\n"
        "    owner: stale\n"
        "weak_cluster_decisions:\n"
        "  - cluster_id: assay\n"
        "    decision: source_owned_same_name\n"
        "    owner: stale\n",
        encoding="utf-8",
    )
    assay_path = tmp_path / "assay.yaml"
    assay_path.write_text(
        "fields:\n  - cluster_id: assay\n    owner: canonical-assay-owner\n",
        encoding="utf-8",
    )
    partial_path = tmp_path / "partial.yaml"
    partial_path.write_text(
        "clusters:\n  - cluster_id: identifier\n    owner: canonical-id-owner\n",
        encoding="utf-8",
    )

    payload = audit._load_governance_review_payload(
        review_path,
        assay_metadata_registry=assay_path,
        partial_identifier_registry=partial_path,
    )

    assert payload["partial_cluster_policies"][0]["owner"] == "canonical-id-owner"
    assay = payload["weak_cluster_decisions"][0]
    assert assay["owner"] == "canonical-assay-owner"
    assert assay["decision"] == "source_owned_same_name"


def test_chembl_target_organism_keeps_custom_validator_evidence() -> None:
    seed_registry = json.loads(
        Path(
            "reports/semantic_pipeline_audit/semantic_cluster_registry_2026-07-01.json"
        ).read_text(encoding="utf-8")
    )

    facts = audit._build_current_member_facts(seed_registry)

    organism = facts[("chembl_target", "organism")]
    assert organism["dq_coverage"] == "custom:error"
