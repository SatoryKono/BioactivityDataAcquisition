"""Actual loader, admitted synthetic V2 bytes and physical Delta rehearsal."""

from dataclasses import replace
from pathlib import Path
from shutil import copytree, ignore_patterns

import pyarrow as pa
import pytest
import yaml
from deltalake import DeltaTable, write_deltalake

from bioetl.composition.bootstrap.cli.config import (
    bind_target_deployment,
    bind_target_rehearsal,
)
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.schemas.silver_chembl_core import CHEMBL_TARGET_SCHEMA
from bioetl.infrastructure.storage.delta.schema_ops import coerce_null_types_for_delta
from bioetl.infrastructure.storage.target_candidates import (
    TargetCandidateBuildRequest,
    build_target_candidates,
    freeze_target_inputs,
)
from bioetl.infrastructure.storage.target_classification_migration import (
    TargetMigrationPaths,
    _lock,
    _tree_hashes,
    prepare_target_migration,
    promote_target_migration,
    rollback_target_migration,
)
from bioetl.infrastructure.storage.target_deployment_binding import (
    validate_deployment_binding,
)
from bioetl.infrastructure.storage import target_migration_validation
from iuphar_target_class.stage0.io import sha256_file
from tests.unit.infrastructure.storage.test_target_migration_admission import (
    _gold,
    _old_row,
)
from tests.unit.infrastructure.storage.test_target_migration_dependencies import (
    deployment as make_dependency_fixture,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def rehearsal(tmp_path, monkeypatch):
    # This fixture has typed expected labels, row manifests, all six outputs,
    # actual source proof bytes and receipt closure. No validator is mocked.
    workspace, _, bundle, _ = make_dependency_fixture.__wrapped__(tmp_path)
    # Model a quiescent test process scope. Actual writer recognition/refusal
    # has independent tests; candidate/deployment/loader validation stays real.
    monkeypatch.setattr(
        target_migration_validation.psutil, "process_iter", lambda _: ()
    )
    repository = Path(__file__).resolve().parents[3]
    active = workspace / "configs"
    copytree(repository / "configs", active, ignore=ignore_patterns(".env*", "*.env"))
    occurrence = workspace / "reports/local/rehearsal-occurrence"
    copied = occurrence / "configs"
    copytree(active, copied, ignore=ignore_patterns(".env*", "*.env"))
    config = copied / "entities/chembl/target.yaml"
    document = yaml.safe_load(config.read_bytes())
    fields = tuple(document["hash_policy"]["hash_policy"]["include_fields"])
    profile = bundle / "enrich-profile.json"
    document["pipeline"]["target_classification"] = {
        "mode": "enrich",
        "snapshot_manifest": profile.relative_to(workspace).as_posix(),
        "snapshot_manifest_sha256": sha256_file(profile),
    }
    deployment = occurrence / "deployment.yaml"
    deployment.write_text(yaml.safe_dump(document), encoding="utf-8")
    settings = Settings(_env_file=None, test_mode=True, data_dir=occurrence / "data")
    paths = TargetMigrationPaths(
        workspace,
        settings.silver_path / "chembl/target",
        settings.gold_path / "chembl/target",
        settings.gold_path / "chembl/assay",
        config,
        occurrence / "new-silver",
        occurrence / "new-gold",
        deployment,
        occurrence / "backup",
    )
    rows = [_old_row("CHEMBL1", fields), _old_row("CHEMBL2", fields)]
    write_deltalake(
        paths.silver, pa.Table.from_pylist(rows, schema=CHEMBL_TARGET_SCHEMA)
    )
    write_deltalake(
        paths.gold, coerce_null_types_for_delta(pa.Table.from_pylist([_gold(rows[0])]))
    )
    write_deltalake(paths.assay, pa.table({"target_id": ["CHEMBL1", None]}))
    return paths, occurrence, copied, active, settings, fields, profile


def _bind(case, **kwargs):
    paths, occurrence, copied, active, settings, _, _ = case
    return bind_target_rehearsal(
        paths,
        rehearsal_root=occurrence,
        configs_root=copied,
        settings=settings,
        active_configs_root=active,
        **kwargs,
    )


def test_actual_build_prepare_promote_and_physical_rollback_on_copy(rehearsal):
    paths, occurrence, _, active, _, fields, profile = rehearsal
    original = {
        name: _tree_hashes(getattr(paths, name))
        for name in ("silver", "gold", "assay", "config")
    }
    active_config = active / "entities/chembl/target.yaml"
    active_before = sha256_file(active_config)
    profile_before = {
        path: sha256_file(path) for path in profile.parent.rglob("*") if path.is_file()
    }
    binding = _bind(rehearsal)
    assert binding.role == "rehearsal"
    assert binding.profile_sha256 == sha256_file(profile)
    frozen = occurrence / "frozen.json"
    freeze_target_inputs(paths, legacy_include_fields=fields, output=frozen)
    built = build_target_candidates(
        TargetCandidateBuildRequest(
            paths,
            frozen,
            sha256_file(frozen),
            occurrence / "build",
            fields,
            "synthetic-physical-rehearsal",
            "2026-11-16T00:00:00Z",
            binding,
        )
    )
    assert built["status"] == "complete"
    assert DeltaTable(paths.candidate_silver).to_pyarrow_table().num_rows == 2
    state = prepare_target_migration(
        paths, legacy_include_fields=fields, deployment=binding
    )
    assert state["phase"] == "prepared"
    assert profile.relative_to(paths.workspace).as_posix() in state["dependencies"]
    assert all(
        Path(paths.workspace / p).is_relative_to(occurrence)
        for p in state["dependency_backups"]
    )
    promoted = promote_target_migration(paths, deployment=binding)
    assert promoted["phase"] == "promoted"
    assert "iuphar_class" in DeltaTable(paths.silver).to_pyarrow_table().column_names
    assert (
        yaml.safe_load(paths.config.read_bytes())["pipeline"]["target_classification"][
            "mode"
        ]
        == "enrich"
    )
    assert sha256_file(active_config) == active_before
    assert all(sha256_file(path) == digest for path, digest in profile_before.items())
    rolled_back = rollback_target_migration(paths)
    assert rolled_back["phase"] == "rolled_back"
    for name, hashes in original.items():
        assert _tree_hashes(getattr(paths, name)) == hashes
    assert (paths.backup / "failed-silver").is_dir()
    assert (paths.backup / "failed-config").is_file()
    with _lock(paths.workspace):
        pass
    assert sha256_file(active_config) == active_before


def test_production_binder_cannot_accept_rehearsal_config_root(rehearsal):
    paths, _, copied, _, settings, _, _ = rehearsal
    with pytest.raises(ValueError, match="active config root"):
        bind_target_deployment(paths, settings=settings, configs_root=copied)


@pytest.mark.parametrize(
    "field",
    [
        "config",
        "silver",
        "gold",
        "assay",
        "backup",
        "candidate_config",
        "candidate_silver",
        "candidate_gold",
    ],
)
def test_rehearsal_cannot_mutate_an_active_or_external_resource(rehearsal, field):
    paths, occurrence, copied, active, settings, _, _ = rehearsal
    external = (
        active / "entities/chembl/target.yaml"
        if field == "config"
        else paths.workspace / ("active-" + field)
    )
    changed = replace(paths, **{field: external})
    with pytest.raises(ValueError, match="inside the rehearsal root"):
        bind_target_rehearsal(
            changed,
            rehearsal_root=occurrence,
            configs_root=copied,
            settings=settings,
            active_configs_root=active,
        )
    assert not paths.backup.exists()


def test_old_copy_must_equal_canonical_config_bytes(rehearsal):
    paths, *_ = rehearsal
    paths.config.write_bytes(paths.config.read_bytes() + b"\n# drift\n")
    with pytest.raises(ValueError, match="canonical bytes"):
        _bind(rehearsal)


def test_forged_rehearsal_scope_cannot_reach_canonical_resources(rehearsal):
    paths, _, _, active, _, _, _ = rehearsal
    binding = _bind(rehearsal)
    checked = paths.checked()
    checked["config"] = active / "entities/chembl/target.yaml"
    with pytest.raises(ValueError, match="inside the rehearsal root"):
        validate_deployment_binding(checked, binding)
    forged = replace(binding, rehearsal_root=str(paths.workspace))
    with pytest.raises(ValueError, match="dedicated reports/local"):
        validate_deployment_binding(paths.checked(), forged)


def test_production_binding_document_retains_legacy_shape(rehearsal):
    binding = replace(
        _bind(rehearsal), role="deployment", rehearsal_root="", approved_workspace=""
    )
    assert "role" not in binding.document()
    assert "rehearsal_root" not in binding.document()


@pytest.mark.parametrize("test_mode,inside", [(False, True), (True, False)])
def test_rehearsal_requires_explicit_isolated_settings(rehearsal, test_mode, inside):
    paths, occurrence, copied, active, settings, _, _ = rehearsal
    settings = settings.model_copy(
        update={
            "test_mode": test_mode,
            "data_dir": settings.data_dir
            if inside
            else paths.workspace / "active-data",
        }
    )
    with pytest.raises(ValueError, match="isolated test_mode"):
        bind_target_rehearsal(
            paths,
            rehearsal_root=occurrence,
            configs_root=copied,
            settings=settings,
            active_configs_root=active,
        )


def test_rehearsal_config_may_change_classification_only(rehearsal):
    paths, *_ = rehearsal
    document = yaml.safe_load(paths.candidate_config.read_bytes())
    document["pipeline"]["batch_size"] += 1
    paths.candidate_config.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError, match="only target_classification"):
        _bind(rehearsal)
