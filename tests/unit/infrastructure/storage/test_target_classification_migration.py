"""Target migration preserves paired directories through partial failures."""

from __future__ import annotations

from pathlib import Path
from dataclasses import replace
import subprocess
import sys

import pytest
import yaml

from bioetl.domain.behavior.identity_service import EntityIdentityGenerator
from bioetl.infrastructure.storage import target_classification_migration as migration
from bioetl.infrastructure.storage.target_migration_validation import (
    compare_target_rows,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def paths(tmp_path, monkeypatch):
    names = ("silver", "gold", "assay", "candidate_silver", "candidate_gold")
    for name in names:
        folder = tmp_path / name
        (folder / "_delta_log").mkdir(parents=True)
        (folder / "_delta_log/000.json").write_text(name)
        (folder / "part.parquet").write_bytes(name.encode())
    for name in ("config", "candidate_config"):
        (tmp_path / (name + ".yaml")).write_text(
            yaml.safe_dump(
                {
                    "fixture": name,
                    "pipeline": {"target_classification": {"mode": "off"}},
                }
            )
        )
    monkeypatch.setattr(migration, "assert_no_managed_writers", lambda: None)
    # These tests isolate filesystem recovery; actual deployment policy has
    # independent loader/resolver regressions.
    monkeypatch.setattr(migration, "validate_deployment_binding", lambda *_: None)
    monkeypatch.setattr(
        migration,
        "validate_target_candidate",
        lambda *_, **__: {"synthetic_test": True},
    )
    return migration.TargetMigrationPaths(
        tmp_path,
        tmp_path / "silver",
        tmp_path / "gold",
        tmp_path / "assay",
        tmp_path / "config.yaml",
        tmp_path / "candidate_silver",
        tmp_path / "candidate_gold",
        tmp_path / "candidate_config.yaml",
        tmp_path / "backup",
    )


def test_promote_and_rollback_restore_physical_logs_data_and_config(paths):
    migration.prepare_target_migration(paths, legacy_include_fields=("target_id",))
    assert (paths.backup / "copy-silver/_delta_log/000.json").read_text() == "silver"
    migration.promote_target_migration(paths)
    assert (paths.silver / "part.parquet").read_bytes() == b"candidate_silver"
    assert yaml.safe_load(paths.config.read_bytes())["fixture"] == "candidate_config"
    migration.rollback_target_migration(paths)
    assert (paths.silver / "part.parquet").read_bytes() == b"silver"
    assert (paths.gold / "_delta_log/000.json").read_text() == "gold"
    assert yaml.safe_load(paths.config.read_bytes())["fixture"] == "config"
    assert (paths.backup / "failed-silver/part.parquet").exists()


def test_candidate_change_after_validation_refuses_mutation(paths):
    migration.prepare_target_migration(paths, legacy_include_fields=("target_id",))
    (paths.candidate_gold / "part.parquet").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="candidate bytes changed"):
        migration.promote_target_migration(paths)
    assert (paths.gold / "part.parquet").read_bytes() == b"gold"
    assert not (paths.backup / "original-silver").exists()


def test_lexical_parent_alias_cannot_hide_a_backup_inside_canonical_table(paths):
    nested = paths.workspace / "reports" / ".." / "silver" / "backup"
    with pytest.raises(ValueError, match="disjoint"):
        replace(paths, backup=nested).checked()
    assert not (paths.silver / "backup").exists()


def test_lexical_aliases_are_resolved_before_identity_comparisons(paths):
    alias = paths.workspace / "silver" / ".." / "gold"
    with pytest.raises(ValueError, match="disjoint"):
        replace(paths, candidate_silver=alias).checked()


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
    assert yaml.safe_load(paths.config.read_bytes())["fixture"] == "config"


def test_assay_cohort_change_after_prepare_blocks_promotion(paths):
    migration.prepare_target_migration(paths, legacy_include_fields=("target_id",))
    (paths.assay / "part.parquet").write_bytes(b"replacement-cohort")
    with pytest.raises(ValueError, match="assay reference cohort changed"):
        migration.promote_target_migration(paths)
    assert (paths.silver / "part.parquet").read_bytes() == b"silver"
    assert not (paths.backup / "original-silver").exists()


def test_uninstalled_v32_transition_writes_nothing(paths):
    with pytest.raises(ValueError, match="3.2.0 is not installed"):
        migration.prepare_target_migration(
            paths,
            legacy_include_fields=("target_id",),
            destination_profile="V32",
        )
    assert not paths.backup.exists()


def test_target_id_pin_uses_the_windows_safe_delta_reader(monkeypatch):
    from types import SimpleNamespace

    def scan(_table, columns=None):
        assert columns == ["target_id", "_is_current"]
        return [
            {"target_id": "CHEMBL1", "_is_current": True},
            {"target_id": None, "_is_current": True},
            {"target_id": "CHEMBL2", "_is_current": False},
        ]

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.delta.table_ops.read_delta_records",
        scan,
    )
    table = SimpleNamespace(
        schema=lambda: SimpleNamespace(
            fields=[
                SimpleNamespace(name="target_id"),
                SimpleNamespace(name="_is_current"),
            ]
        ),
        to_pyarrow_table=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("native delta scan")
        ),
    )

    assert migration._target_ids(table) == {"CHEMBL1"}


def test_schema_v1_journal_promotes_and_reports_without_v2_fields(paths):
    import orjson

    migration.prepare_target_migration(paths, legacy_include_fields=("target_id",))
    journal = orjson.loads((paths.backup / "journal.json").read_bytes())
    journal["schema_version"] = 1
    for key in (
        "source_profile",
        "destination_profile",
        "source_contract_version",
        "destination_contract_version",
        "table_versions",
        "candidate_profiles",
        "config_contract_version",
        "destination_config_contract_version",
        "dependency_schema_versions",
        "fk_restoration",
    ):
        journal.pop(key, None)
    (paths.backup / "journal.json").write_bytes(orjson.dumps(journal))
    state = migration.promote_target_migration(paths)
    assert state["phase"] == "promoted"
    assert migration.migration_status(state) == {
        "source_profile": "V30",
        "destination_profile": "V31",
        "source_contract_version": "3.0.0",
        "destination_contract_version": "3.1.0",
        "fk_restoration": "unrecorded",
    }
    migration.rollback_target_migration(paths)
    assert (paths.silver / "part.parquet").read_bytes() == b"silver"


def test_deployment_role_cannot_promote_without_rf013(paths):
    from bioetl.infrastructure.storage.target_deployment_binding import (
        TargetDeploymentBinding,
    )

    binding = TargetDeploymentBinding(
        str(paths.config),
        "a" * 64,
        "b" * 64,
        str(paths.silver),
        str(paths.gold),
        "c" * 64,
        "d" * 64,
    )
    with pytest.raises(ValueError, match="reserved for RF-013"):
        migration.promote_target_migration(paths, deployment=binding)
    assert not paths.backup.exists()


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


def test_interrupted_rollback_can_resume_after_other_pairs_were_restored(
    paths, monkeypatch
):
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
    assert yaml.safe_load(paths.config.read_bytes())["fixture"] == "config"
    assert (paths.gold / "part.parquet").read_bytes() == b"gold"
    migration.rollback_target_migration(paths)
    assert (paths.silver / "part.parquet").read_bytes() == b"silver"
    assert (
        paths.backup / "failed-silver/part.parquet"
    ).read_bytes() == b"candidate_silver"


def test_full_cohort_required_and_new_class_does_not_change_legacy_hash():
    fields = ("target_id", "pref_name")
    identity = EntityIdentityGenerator(content_hash_include_fields=set(fields))
    old = {"target_id": "CHEMBL1", "pref_name": "Fixture"}
    old["content_hash"] = identity.compute_content_hash("chembl", old)
    candidate = {**old, "iuphar_class": "Receptor", "content_hash": "new-v31-hash"}
    assert (
        compare_target_rows([old], [candidate], fields)["legacy_hashes_verified"] == 1
    )
    with pytest.raises(ValueError, match="full canonical cohort"):
        compare_target_rows([old, {**old, "target_id": "CHEMBL2"}], [candidate], fields)
    with pytest.raises(ValueError, match="legacy business field"):
        compare_target_rows([old], [{**candidate, "pref_name": "changed"}], fields)


@pytest.mark.parametrize("changed", [False, True])
def test_rollback_restores_missing_dependency_and_rejects_changed_bytes(
    paths, monkeypatch, changed
):
    dependency = paths.workspace / "old-profile.json"
    dependency.write_bytes(b"pinned dependency")
    digest = migration.sha256_file(dependency)
    monkeypatch.setattr(
        migration, "collect_target_dependencies", lambda **_: {dependency.name: digest}
    )
    migration.prepare_target_migration(paths, legacy_include_fields=("target_id",))
    migration.promote_target_migration(paths)
    dependency.unlink()
    if changed:
        dependency.write_bytes(b"another legitimate profile")
        with pytest.raises(ValueError, match="digest mismatch"):
            migration.rollback_target_migration(paths)
        assert dependency.read_bytes() == b"another legitimate profile"
        assert (paths.silver / "part.parquet").read_bytes() == b"candidate_silver"
    else:
        state = migration.rollback_target_migration(paths)
        assert dependency.read_bytes() == b"pinned dependency"
        assert state["restored_dependencies"] == [dependency.name]


def test_migration_lock_is_released_after_process_exit(paths):
    script = (
        "import os, sys\nfrom pathlib import Path\n"
        "from bioetl.infrastructure.storage import target_classification_migration as m\n"
        "m.assert_no_managed_writers = lambda: None\n"
        "with m._lock(Path(sys.argv[1])):\n    os._exit(0)\n"
    )
    subprocess.run(
        [sys.executable, "-c", script, str(paths.workspace)], check=True, timeout=30
    )
    with migration._lock(paths.workspace):
        with pytest.raises(OSError):
            with migration._lock(paths.workspace):
                pytest.fail("a concurrent migration acquired the lock")


def test_scd_history_is_preserved_and_duplicate_current_versions_are_rejected():
    fields = ("target_id", "pref_name")
    identity = EntityIdentityGenerator(content_hash_include_fields=set(fields))
    base = {"target_id": "CHEMBL1", "pref_name": "Fixture"}
    base["content_hash"] = identity.compute_content_hash("chembl", base)
    old = [
        {
            **base,
            "_version": 1,
            "_is_current": False,
            "_valid_from": "2025-01-01T00:00:00Z",
            "_valid_to": "2026-01-01T00:00:00Z",
        },
        {
            **base,
            "_version": 2,
            "_is_current": True,
            "_valid_from": "2026-01-01T00:00:00Z",
            "_valid_to": None,
        },
    ]
    new = [{**row, "iuphar_class": "Receptor", "content_hash": "v31"} for row in old]
    assert compare_target_rows(old, new, fields)["legacy_hashes_verified"] == 2
    with pytest.raises(ValueError, match="unique current"):
        compare_target_rows(old, [{**row, "_is_current": True} for row in new], fields)
    with pytest.raises(ValueError, match="full canonical cohort"):
        compare_target_rows(old, new[1:], fields)
