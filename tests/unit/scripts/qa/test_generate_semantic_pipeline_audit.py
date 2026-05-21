from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa import generate_semantic_pipeline_audit as audit


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


def test_build_current_member_facts_exposes_composite_inherited_field_types() -> None:
    seed_registry = json.loads(
        Path(
            "reports/semantic_pipeline_audit/semantic_cluster_registry_2026-05-16.json"
        ).read_text(encoding="utf-8")
    )

    facts = audit._build_current_member_facts(seed_registry)

    assert facts[("composite_activity", "assay_id")]["field_type"] == "string"
    assert facts[("composite_activity", "molecule_id")]["field_type"] == "string"
    assert facts[("composite_molecule", "hba_count")]["field_type"] == "int64"
    assert facts[("composite_molecule", "logp")]["field_type"] == "double"
    assert facts[("composite_publication", "year")]["field_type"] == "int64"
    assert facts[("composite_target", "downgraded")]["field_type"] == "bool"


def test_build_current_member_facts_exposes_composite_authority_shim_types() -> None:
    seed_registry = json.loads(
        Path(
            "reports/semantic_pipeline_audit/semantic_cluster_registry_2026-05-21.json"
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
            "reports/semantic_pipeline_audit/semantic_cluster_registry_2026-05-21.json"
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
