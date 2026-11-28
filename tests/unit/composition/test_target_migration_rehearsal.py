"""Actual loader, admitted synthetic V2 bytes and physical Delta rehearsal."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from shutil import copytree, ignore_patterns

import orjson
import pyarrow as pa
import pytest
import yaml
from deltalake import DeltaTable, write_deltalake

from bioetl.composition.bootstrap.cli.metrics import (
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
    # This occurrence starts with a historical V30 config and physical V30 tables.
    active_target = active / "entities/chembl/target.yaml"
    document = yaml.safe_load(active_target.read_bytes())
    document["pipeline"]["target_classification"] = {"mode": "off"}
    active_target.write_text(yaml.safe_dump(document), encoding="utf-8")
    occurrence = workspace / "reports/local/rehearsal-occurrence"
    copied = occurrence / "configs"
    copytree(active, copied, ignore=ignore_patterns(".env*", "*.env"))
    config = copied / "entities/chembl/target.yaml"
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


def _build_rehearsal_candidates(paths, fields, binding, source_profile="V30"):
    output = paths.backup.with_name(f"build-{source_profile.lower()}")
    frozen = output.with_suffix(".json")
    freeze_target_inputs(
        paths,
        legacy_include_fields=fields,
        output=frozen,
        source_profile=source_profile,
    )
    return build_target_candidates(
        TargetCandidateBuildRequest(
            paths,
            frozen,
            sha256_file(frozen),
            output,
            fields,
            "synthetic-physical-rehearsal",
            "2026-11-16T00:00:00Z",
            binding,
            source_profile=source_profile,
        )
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
    built = _build_rehearsal_candidates(paths, fields, binding)
    assert built["status"] == "complete"
    assert DeltaTable(paths.candidate_silver).to_pyarrow_table().num_rows == 2
    state = prepare_target_migration(
        paths, legacy_include_fields=fields, deployment=binding
    )
    assert state["phase"] == "prepared"
    assert state["source_profile"] == "V30"
    assert state["destination_profile"] == "V31"
    assert state["source_contract_version"] == "3.0.0"
    assert state["destination_contract_version"] == "3.1.0"
    assert state["config_contract_version"] == "3.0.0"
    assert state["fk_restoration"]["status"] == "closed"
    assert state["fk_restoration"]["missing_target_ids"] == []
    assert state["table_versions"]["silver"]["profile"] == "V30"
    assert state["table_versions"]["gold"]["profile"] == "V30"
    assert state["table_versions"]["assay"]["version"] == 0
    assert state["candidate_profiles"] == {"silver": "V31", "gold": "V31"}
    assert state["validation"]["profile_sha256"] == sha256_file(profile)
    assert (
        profile.relative_to(paths.workspace).as_posix()
        in state["dependency_schema_versions"]
    )
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


def test_v31_refresh_promotes_and_restores_the_previous_enrich_bundle(rehearsal):
    paths, occurrence, _, active, _, fields, profile = rehearsal
    active_config = active / "entities/chembl/target.yaml"

    initial_binding = _bind(rehearsal)
    _build_rehearsal_candidates(paths, fields, initial_binding)
    prepare_target_migration(
        paths, legacy_include_fields=fields, deployment=initial_binding
    )
    promote_target_migration(paths, deployment=initial_binding)
    active_config.write_bytes(paths.config.read_bytes())
    active_before = sha256_file(active_config)

    original = {
        name: _tree_hashes(getattr(paths, name))
        for name in ("silver", "gold", "assay", "config")
    }
    versions = {
        name: DeltaTable(str(getattr(paths, name))).version()
        for name in ("silver", "gold")
    }
    _, _, refreshed_bundle, _ = make_dependency_fixture.__wrapped__(occurrence)
    refreshed_profile = refreshed_bundle / "enrich-profile.json"
    deployment = yaml.safe_load(paths.config.read_bytes())
    classification = deployment["pipeline"]["target_classification"]
    assert classification["mode"] == "enrich"
    assert classification["snapshot_manifest_sha256"] == sha256_file(profile)
    classification["snapshot_manifest"] = refreshed_profile.relative_to(
        paths.workspace
    ).as_posix()
    classification["snapshot_manifest_sha256"] = sha256_file(refreshed_profile)
    paths.candidate_config.write_text(yaml.safe_dump(deployment), encoding="utf-8")

    paths = replace(paths, backup=occurrence / "refresh-backup")
    binding = _bind((paths, *rehearsal[1:]))
    assert binding.profile_sha256 != initial_binding.profile_sha256
    _build_rehearsal_candidates(paths, fields, binding, source_profile="V31")
    prepared = prepare_target_migration(
        paths, legacy_include_fields=fields, deployment=binding, source_profile="V31"
    )
    assert prepared["phase"] == "prepared"
    assert prepared["source_profile"] == prepared["destination_profile"] == "V31"
    assert prepared["source_contract_version"] == "3.1.0"
    assert prepared["destination_contract_version"] == "3.1.0"
    assert prepared["fk_restoration"]["status"] == "closed"

    promoted = promote_target_migration(
        paths, deployment=binding, source_profile="V31", destination_profile="V31"
    )
    assert promoted["phase"] == "promoted"
    assert sha256_file(paths.config) == binding.deployment_config_sha256
    assert _tree_hashes(paths.assay) == original["assay"]
    for name, version in versions.items():
        table = DeltaTable(str(getattr(paths, name)))
        assert table.version() == version + 1
        assert set(
            table.to_pyarrow_table()["target_class_profile_sha256"].to_pylist()
        ) == {binding.profile_sha256}

    restored = rollback_target_migration(
        paths, source_profile="V31", destination_profile="V31"
    )
    assert restored["phase"] == "rolled_back"
    for name, hashes in original.items():
        assert _tree_hashes(getattr(paths, name)) == hashes
    assert sha256_file(active_config) == active_before


def test_source_version_change_between_phases_blocks_promotion(rehearsal):
    paths, occurrence, _, _, _, fields, _ = rehearsal
    binding = _bind(rehearsal)
    frozen = occurrence / "frozen-version.json"
    freeze_target_inputs(paths, legacy_include_fields=fields, output=frozen)
    build_target_candidates(
        TargetCandidateBuildRequest(
            paths,
            frozen,
            sha256_file(frozen),
            occurrence / "build-version",
            fields,
            "synthetic-version-rehearsal",
            "2026-11-16T00:00:00Z",
            binding,
        )
    )
    prepare_target_migration(paths, legacy_include_fields=fields, deployment=binding)
    current = DeltaTable(paths.silver).to_pyarrow_table()
    write_deltalake(paths.silver, current, mode="append")
    with pytest.raises(ValueError, match="source table version changed"):
        promote_target_migration(paths, deployment=binding)
    assert "iuphar_class" not in DeltaTable(paths.gold).to_pyarrow_table().column_names
    journal = json.loads((paths.backup / "journal.json").read_text(encoding="utf-8"))
    assert journal["phase"] == "prepared"


def test_assay_cohort_change_on_a_full_copy_blocks_promotion(rehearsal):
    paths, occurrence, _, _, _, fields, _ = rehearsal
    binding = _bind(rehearsal)
    frozen = occurrence / "frozen-assay.json"
    freeze_target_inputs(paths, legacy_include_fields=fields, output=frozen)
    build_target_candidates(
        TargetCandidateBuildRequest(
            paths,
            frozen,
            sha256_file(frozen),
            occurrence / "build-assay",
            fields,
            "synthetic-assay-rehearsal",
            "2026-11-16T00:00:00Z",
            binding,
        )
    )
    prepare_target_migration(paths, legacy_include_fields=fields, deployment=binding)
    data_file = next(paths.assay.rglob("*.parquet"))
    data_file.write_bytes(data_file.read_bytes() + b"\0")
    with pytest.raises(
        ValueError, match="assay reference cohort changed|no longer readable"
    ):
        promote_target_migration(paths, deployment=binding)
    mode = yaml.safe_load(paths.config.read_bytes())["pipeline"][
        "target_classification"
    ]["mode"]
    assert mode == "off"


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


def test_rehearsal_workspace_must_match_active_repository(rehearsal):
    paths, occurrence, copied, active, settings, _, _ = rehearsal
    with pytest.raises(ValueError, match="workspace must match"):
        bind_target_rehearsal(
            paths,
            rehearsal_root=occurrence,
            configs_root=copied,
            settings=settings,
            active_configs_root=copied,
        )


def test_rehearsal_rejects_the_active_configs_tree(rehearsal):
    paths, occurrence, _, active, settings, _, _ = rehearsal
    with pytest.raises(ValueError, match="load its copied configs tree"):
        bind_target_rehearsal(
            paths,
            rehearsal_root=occurrence,
            configs_root=active,
            settings=settings,
            active_configs_root=active,
        )


def test_rehearsal_requires_enrich(rehearsal):
    paths, *_ = rehearsal
    document = yaml.safe_load(paths.candidate_config.read_bytes())
    document["pipeline"]["target_classification"] = {"mode": "off"}
    paths.candidate_config.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError, match="must select enrich"):
        _bind(rehearsal)


def test_rehearsal_rejects_missing_admitted_profile(rehearsal, monkeypatch):
    from bioetl.composition.bootstrap.cli import metrics

    monkeypatch.setattr(metrics, "load_target_runtime_profile", lambda *a, **k: None)
    with pytest.raises(ValueError, match="no admitted profile"):
        _bind(rehearsal)


def test_rehearsal_rejects_another_physical_target(rehearsal, monkeypatch):
    from bioetl.composition.bootstrap.cli import metrics

    paths, _, _, _, settings, _, _ = rehearsal
    original = metrics.resolve_target_table_paths

    def different_target(active_settings, config):
        if active_settings is settings:
            return paths.silver.parent / "other", paths.gold
        return original(active_settings, config)

    monkeypatch.setattr(
        metrics,
        "resolve_target_table_paths",
        different_target,
    )
    with pytest.raises(ValueError, match="different physical target"):
        _bind(rehearsal)


def _same_shape(row: dict[str, object], target_id: str) -> dict[str, object]:
    updated = dict(row)
    updated["target_id"] = target_id
    if "entity_id" in updated:
        updated["entity_id"] = "chembl:" + target_id
    if "pref_name" in updated:
        updated["pref_name"] = "Adenosine receptor A2b"
    for field, value in (
        ("component_ids", '["1"]'),
        ("component_types", '["PROTEIN"]'),
        ("component_accessions", '["Q60614"]'),
    ):
        if field in updated:
            updated[field] = value
    return updated


def test_restored_assay_target_closes_migration_without_changing_assay(rehearsal):
    from bioetl.infrastructure.storage.target_fk_restoration import (
        publish_target_fk_restoration,
    )
    from bioetl.infrastructure.storage.target_migration_classification_checks import (
        TargetRecoveryInput,
    )
    from bioetl.infrastructure.storage.target_migration_row_ops import read_delta

    paths, occurrence, _, _, _, fields, _ = rehearsal
    silver_before = _tree_hashes(paths.silver)
    gold_before = _tree_hashes(paths.gold)
    silver_row = next(
        row for row in read_delta(paths.silver) if row["target_id"] == "CHEMBL1"
    )
    gold_row = read_delta(paths.gold)[0]
    restored_silver = _same_shape(silver_row, "CHEMBL2237")
    restored_gold = _same_shape(gold_row, "CHEMBL2237")
    for field in (
        "component_ids",
        "component_types",
        "component_accessions",
        "pref_name",
    ):
        if field in restored_silver and field in restored_gold:
            restored_gold[field] = restored_silver[field]
    source = occurrence / "recovery/CHEMBL2237.json"
    source.parent.mkdir()
    source.write_bytes(
        orjson.dumps(
            {
                "target_id": "CHEMBL2237",
                "silver": restored_silver,
                "gold": restored_gold,
            },
            option=orjson.OPT_SORT_KEYS,
        )
    )
    write_deltalake(
        paths.assay,
        pa.table({"target_id": ["CHEMBL1", None, "CHEMBL2237"]}),
        mode="overwrite",
    )
    assay_gap = _tree_hashes(paths.assay)
    recovery = TargetRecoveryInput(
        "CHEMBL2237",
        "verified_pipeline_output",
        source.resolve().relative_to(paths.workspace.resolve()).as_posix(),
        source,
        sha256_file(source),
        restored_silver,
        restored_gold,
    )
    destination = occurrence / "fk-restoration"
    manifest = publish_target_fk_restoration(
        silver=paths.silver,
        gold=paths.gold,
        assay=paths.assay,
        config=paths.config,
        recoveries=(recovery,),
        destination=destination,
        workspace=paths.workspace,
    )
    assert (
        publish_target_fk_restoration(
            silver=paths.silver,
            gold=paths.gold,
            assay=paths.assay,
            config=paths.config,
            recoveries=(recovery,),
            destination=destination,
            workspace=paths.workspace,
        ).read_bytes()
        == manifest.read_bytes()
    )
    assert _tree_hashes(paths.assay) == assay_gap
    assert _tree_hashes(paths.silver) == silver_before
    assert _tree_hashes(paths.gold) == gold_before
    with pytest.raises(ValueError, match="foreign-key closure"):
        freeze_target_inputs(
            paths,
            legacy_include_fields=fields,
            output=occurrence / "frozen-open.json",
        )
    frozen = occurrence / "frozen-restored.json"
    freeze_target_inputs(
        paths,
        legacy_include_fields=fields,
        output=frozen,
        restoration_manifest=manifest,
    )
    binding = _bind(rehearsal)
    built = build_target_candidates(
        TargetCandidateBuildRequest(
            paths,
            frozen,
            sha256_file(frozen),
            occurrence / "build-restored",
            fields,
            "synthetic-fk-restoration",
            "2026-11-23T00:00:00Z",
            binding,
        )
    )
    assert built["status"] == "complete"
    gold_ids = {
        row["target_id"]
        for row in DeltaTable(paths.candidate_gold).to_pyarrow_table().to_pylist()
    }
    assert gold_ids == {"CHEMBL1", "CHEMBL2237"}
    state = prepare_target_migration(
        paths,
        legacy_include_fields=fields,
        deployment=binding,
        restoration_manifest=manifest,
    )
    assert state["phase"] == "prepared"
    assert _tree_hashes(paths.assay) == assay_gap
    assert any(name.endswith("CHEMBL2237.json") for name in state["dependencies"])
    assert _tree_hashes(paths.gold) == gold_before
    promoted = promote_target_migration(paths, deployment=binding)
    assert promoted["phase"] == "promoted"
    promoted_ids = {
        row["target_id"]
        for row in DeltaTable(paths.gold).to_pyarrow_table().to_pylist()
    }
    assert promoted_ids == {"CHEMBL1", "CHEMBL2237"}
    assert _tree_hashes(paths.assay) == assay_gap


def test_gold_filter_conflict_stays_a_blocker_and_writes_a_decision(tmp_path):
    from bioetl.infrastructure.storage.target_fk_restoration import (
        publish_target_fk_restoration,
    )
    from bioetl.infrastructure.storage.target_migration_classification_checks import (
        TargetRecoveryInput,
        current_target_ids,
    )
    from bioetl.infrastructure.storage.target_migration_row_ops import read_delta

    row = {
        "target_id": "CHEMBL1",
        "target_type": "SINGLE PROTEIN",
        "pref_name": "Known",
        "organism": "Homo sapiens",
        "organism_class": "multicellular",
        "component_accessions": '["P12345"]',
        "component_ids": '["1"]',
        "component_types": '["PROTEIN"]',
    }
    blocked = {
        **row,
        "target_id": "CHEMBL2411",
        "pref_name": "5-HT3 receptor",
        "organism": "Rattus norvegicus",
        "organism_class": "unicellular",
    }
    for name, rows in (
        ("silver", [row]),
        ("gold", [row]),
        ("assay", [{"target_id": "CHEMBL1"}, {"target_id": "CHEMBL2411"}]),
    ):
        write_deltalake(tmp_path / name, pa.Table.from_pylist(rows))
    source = tmp_path / "recovery/CHEMBL2411.json"
    source.parent.mkdir()
    source.write_bytes(
        orjson.dumps(
            {"target_id": "CHEMBL2411", "silver": blocked, "gold": blocked},
            option=orjson.OPT_SORT_KEYS,
        )
    )
    from bioetl.infrastructure.storage.target_classification_migration import (
        _tree_hashes,
    )

    before = {
        name: _tree_hashes(tmp_path / name) for name in ("silver", "gold", "assay")
    }
    destination = tmp_path / "blocked-restoration"
    with pytest.raises(ValueError, match="foreign-key closure"):
        publish_target_fk_restoration(
            silver=tmp_path / "silver",
            gold=tmp_path / "gold",
            assay=tmp_path / "assay",
            config=Path(__file__).resolve().parents[3]
            / "configs/entities/chembl/target.yaml",
            recoveries=(
                TargetRecoveryInput(
                    "CHEMBL2411",
                    "verified_pipeline_output",
                    source.relative_to(tmp_path).as_posix(),
                    source,
                    sha256_file(source),
                    blocked,
                    blocked,
                ),
            ),
            destination=destination,
            workspace=tmp_path,
        )
    decision = destination / "contract-decision.json"
    assert decision.is_file()
    payload = decision.read_bytes()
    assert b"blocked_pending_contract_reconciliation" in payload
    assert b"CHEMBL2411" in payload
    assert b"gold_filter" in payload
    assert not (destination / "gold").exists()
    assert {
        name: _tree_hashes(tmp_path / name) for name in ("silver", "gold", "assay")
    } == before
    assert current_target_ids(read_delta(tmp_path / "gold")) == {"CHEMBL1"}
    with pytest.raises(ValueError, match="foreign-key closure"):
        publish_target_fk_restoration(
            silver=tmp_path / "silver",
            gold=tmp_path / "gold",
            assay=tmp_path / "assay",
            config=Path(__file__).resolve().parents[3]
            / "configs/entities/chembl/target.yaml",
            recoveries=(
                TargetRecoveryInput(
                    "CHEMBL2411",
                    "verified_pipeline_output",
                    source.relative_to(tmp_path).as_posix(),
                    source,
                    sha256_file(source),
                    blocked,
                    blocked,
                ),
            ),
            destination=destination,
            workspace=tmp_path,
        )
    assert decision.read_bytes() == payload


def test_rehearsal_protects_active_destinations_from_overlap(rehearsal):
    from bioetl.composition.bootstrap.cli import metrics

    _, _, _, active, _, _, _ = rehearsal
    with pytest.raises(ValueError, match="overlap active canonical"):
        metrics._protect_active_resources(
            {"config": active / "entities/chembl/target.yaml"}, active
        )
