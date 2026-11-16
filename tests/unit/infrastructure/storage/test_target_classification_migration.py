"""Target migration preserves paired directories through partial failures."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.domain.behavior.identity_service import EntityIdentityGenerator
from bioetl.infrastructure.storage import target_classification_migration as migration
from bioetl.infrastructure.storage.target_migration_validation import compare_target_rows


@pytest.fixture
def paths(tmp_path, monkeypatch):
    names = ("silver", "gold", "assay", "candidate_silver", "candidate_gold")
    for name in names:
        folder = tmp_path / name
        (folder / "_delta_log").mkdir(parents=True)
        (folder / "_delta_log/000.json").write_text(name)
        (folder / "part.parquet").write_bytes(name.encode())
    for name in ("config", "candidate_config"):
        (tmp_path / (name + ".yaml")).write_text(name)
    monkeypatch.setattr(migration, "assert_no_managed_writers", lambda: None)
    monkeypatch.setattr(migration, "validate_target_candidate", lambda *_: {"synthetic_test": True})
    return migration.TargetMigrationPaths(
        tmp_path, tmp_path / "silver", tmp_path / "gold", tmp_path / "assay",
        tmp_path / "config.yaml", tmp_path / "candidate_silver",
        tmp_path / "candidate_gold", tmp_path / "candidate_config.yaml", tmp_path / "backup",
    )


def test_promote_and_rollback_restore_physical_logs_data_and_config(paths):
    migration.prepare_target_migration(paths, legacy_include_fields=("target_id",))
    assert (paths.backup / "copy-silver/_delta_log/000.json").read_text() == "silver"
    migration.promote_target_migration(paths)
    assert (paths.silver / "part.parquet").read_bytes() == b"candidate_silver"
    assert paths.config.read_text() == "candidate_config"
    migration.rollback_target_migration(paths)
    assert (paths.silver / "part.parquet").read_bytes() == b"silver"
    assert (paths.gold / "_delta_log/000.json").read_text() == "gold"
    assert paths.config.read_text() == "config"
    assert (paths.backup / "failed-silver/part.parquet").exists()


def test_candidate_change_after_validation_refuses_mutation(paths):
    migration.prepare_target_migration(paths, legacy_include_fields=("target_id",))
    (paths.candidate_gold / "part.parquet").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="candidate bytes changed"):
        migration.promote_target_migration(paths)
    assert (paths.gold / "part.parquet").read_bytes() == b"gold"
    assert not (paths.backup / "original-silver").exists()


def test_second_table_activation_failure_restores_first_table(paths, monkeypatch):
    migration.prepare_target_migration(paths, legacy_include_fields=("target_id",))
    rename = Path.rename

    def interrupted(source, destination):
        if source == paths.candidate_gold:
            raise PermissionError("simulated Windows sharing violation")
        return rename(source, destination)

    monkeypatch.setattr(Path, "rename", interrupted)
    with pytest.raises(PermissionError):
        migration.promote_target_migration(paths)
    assert (paths.silver / "part.parquet").read_bytes() == b"silver"
    assert (paths.gold / "part.parquet").read_bytes() == b"gold"
    assert paths.config.read_text() == "config"


def test_canonical_change_after_backup_is_not_overwritten(paths):
    migration.prepare_target_migration(paths, legacy_include_fields=("target_id",))
    (paths.gold / "part.parquet").write_bytes(b"new legitimate writer")
    with pytest.raises(ValueError, match="canonical bytes changed"):
        migration.promote_target_migration(paths)
    assert (paths.gold / "part.parquet").read_bytes() == b"new legitimate writer"


def test_live_writer_blocks_even_preparation(paths, monkeypatch):
    def busy():
        raise RuntimeError("managed writer active")

    monkeypatch.setattr(migration, "assert_no_managed_writers", busy)
    with pytest.raises(RuntimeError, match="managed writer"):
        migration.prepare_target_migration(paths, legacy_include_fields=("target_id",))
    assert not paths.backup.exists()


def test_interrupted_rollback_can_resume_after_other_pairs_were_restored(paths, monkeypatch):
    migration.prepare_target_migration(paths, legacy_include_fields=("target_id",))
    migration.promote_target_migration(paths)
    rename = Path.rename

    def interrupted(source, destination):
        if source == paths.backup / "original-silver":
            raise PermissionError("simulated interrupted rollback")
        return rename(source, destination)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "rename", interrupted)
        with pytest.raises(PermissionError, match="interrupted rollback"):
            migration.rollback_target_migration(paths)
    assert paths.config.read_text() == "config"
    assert (paths.gold / "part.parquet").read_bytes() == b"gold"
    migration.rollback_target_migration(paths)
    assert (paths.silver / "part.parquet").read_bytes() == b"silver"
    assert (paths.backup / "failed-silver/part.parquet").read_bytes() == b"candidate_silver"


def test_full_cohort_required_and_new_class_does_not_change_legacy_hash():
    fields = ("target_id", "pref_name")
    identity = EntityIdentityGenerator(content_hash_include_fields=set(fields))
    old = {"target_id": "CHEMBL1", "pref_name": "Fixture"}
    old["content_hash"] = identity.compute_content_hash("chembl", old)
    candidate = {**old, "iuphar_class": "Receptor", "content_hash": "new-v31-hash"}
    assert compare_target_rows([old], [candidate], fields)["legacy_hashes_verified"] == 1
    with pytest.raises(ValueError, match="full canonical cohort"):
        compare_target_rows([old, {**old, "target_id": "CHEMBL2"}], [candidate], fields)
    with pytest.raises(ValueError, match="legacy business field"):
        compare_target_rows([old], [{**candidate, "pref_name": "changed"}], fields)
