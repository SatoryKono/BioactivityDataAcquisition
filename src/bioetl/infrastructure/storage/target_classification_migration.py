"""Journaled, paired target-table promotion; no Delta-version-only rollback.

The caller must hold the deployment maintenance window across all old writers.
This module additionally refuses active managed writers and preserves physical
tables/configuration. It never promotes an unvalidated limit-1000 subset.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

import orjson

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

from bioetl.infrastructure.storage.target_classification_migration_bundle import (
    _JOURNAL_JSON,
    TargetMigrationPaths,
    _restore_dependencies,
    _restore_pairs,
    _save,
    _tree_hashes,
)
from bioetl.infrastructure.storage.target_classification_migration_pins import (
    _active_contract_version,
    _assert_plan_profiles,
    _assert_recorded_candidates,
    _assert_recorded_contracts,
    _assert_recorded_versions,
    _assert_source_profiles,
    _candidate_profiles,
    _dependency_schema_versions,
    _fk_restoration,
    _public_pins,
    _source_pins,
    _target_ids,
)
from bioetl.infrastructure.storage.target_classification_migration_state import (
    TargetMigrationJournal,
    _assert_canonical_cutover,
    migration_status,
    require_rf009_fk_restoration,
    resolve_target_migration_transition,
)
from bioetl.infrastructure.storage.target_deployment_binding import (
    TargetDeploymentBinding,
    validate_deployment_binding,
)
from bioetl.infrastructure.storage.target_migration_dependencies import (
    backup_target_dependencies,
    collect_target_dependencies,
    verify_target_dependencies,
)
from bioetl.infrastructure.storage.target_migration_validation import (
    assert_no_managed_writers,
    validate_target_candidate,
)
from iuphar_target_class.stage0.io import sha256_file

# Re-exported for the existing caller and test surface.
__all__ = [
    "TargetMigrationJournal",
    "TargetMigrationPaths",
    "_lock",
    "_target_ids",
    "_tree_hashes",
    "assert_no_managed_writers",
    "migration_status",
    "prepare_target_migration",
    "promote_target_migration",
    "require_rf009_fk_restoration",
    "resolve_target_migration_transition",
    "rollback_target_migration",
    "sha256_file",
]


@contextmanager
def _lock(root: Path) -> Iterator[None]:
    assert_no_managed_writers()
    path = root.resolve(strict=True) / ".bioetl-target-migration.lock"
    # Keep the inode stable: closing the descriptor releases the kernel lock,
    # including after process termination. A leftover file is not a live owner.
    with path.open("a+b") as handle:
        if not path.stat().st_size:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        if sys.platform == "win32":
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def _recorded_restoration(
    workspace: Path, state: TargetMigrationJournal
) -> Path | None:
    recorded = state.get("fk_restoration")
    if not isinstance(recorded, dict) or "path" not in recorded:
        return None
    manifest = workspace / str(recorded["path"])
    if sha256_file(manifest) != recorded["sha256"]:
        raise ValueError("target FK restoration digest mismatch")
    return manifest


def prepare_target_migration(
    paths: TargetMigrationPaths,
    *,
    legacy_include_fields: tuple[str, ...],
    deployment: TargetDeploymentBinding | None = None,
    source_profile: str = "V30",
    destination_profile: str = "V31",
    restoration_manifest: Path | None = None,
) -> TargetMigrationJournal:
    """Validate complete cohorts and copy the entire recoverable old bundle."""
    transition = resolve_target_migration_transition(
        source_profile, destination_profile
    )
    checked = paths.checked()
    validate_deployment_binding(checked, deployment)
    with _lock(paths.workspace):
        pins = _source_pins(checked)
        _assert_source_profiles(pins, transition)
        candidate_profiles = _candidate_profiles(checked, transition)
        validation = validate_target_candidate(
            checked,
            legacy_include_fields,
            workspace=paths.workspace,
            restoration_manifest=restoration_manifest,
        )
        fk_restoration = _fk_restoration(
            pins,
            restored_gold=checked["candidate_gold"] if restoration_manifest else None,
        )
        dependencies = collect_target_dependencies(
            workspace=paths.workspace,
            configs=(checked["config"], checked["candidate_config"]),
            restoration_manifest=restoration_manifest,
        )
        checked["backup"].mkdir(parents=True, exist_ok=False)
        dependency_backups = backup_target_dependencies(
            workspace=paths.workspace,
            dependencies=dependencies,
            destination=checked["backup"] / "dependencies",
        )
        before = {
            name: _tree_hashes(checked[name]) for name in ("silver", "gold", "config")
        }
        for name in before:
            source = checked[name]
            target = checked["backup"] / ("copy-" + name)
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copyfile(source, target)
            if _tree_hashes(target) != before[name]:
                raise ValueError("physical migration backup hash mismatch")
        if any(
            _tree_hashes(checked[name]) != hashes for name, hashes in before.items()
        ):
            raise ValueError("canonical target changed during backup; refuse promotion")
        state: TargetMigrationJournal = {
            "artifact": "bioetl_target_migration",
            "schema_version": 2,
            "phase": "prepared",
            "paths": {k: str(v) for k, v in checked.items()},
            "original_hashes": before,
            "candidate_hashes": {
                name: _tree_hashes(checked["candidate_" + name])
                for name in ("silver", "gold", "config")
            },
            "validation": validation,
            "moved": [],
            "activated": [],
            "legacy_include_fields": list(legacy_include_fields),
            "assay_hashes": _tree_hashes(checked["assay"]),
            "deployment_binding": deployment.document() if deployment else {},
            "dependencies": dependencies,
            "dependency_backups": dependency_backups,
            "source_profile": transition.source_profile,
            "destination_profile": transition.destination_profile,
            "source_contract_version": transition.source_contract_version,
            "destination_contract_version": transition.destination_contract_version,
            "table_versions": _public_pins(pins),
            "candidate_profiles": candidate_profiles,
            "config_contract_version": _active_contract_version(checked["config"]),
            # On-disk YAML active_version. The effective enrich contract is
            # destination_contract_version, not this declared document version.
            "destination_config_contract_version": _active_contract_version(
                checked["candidate_config"]
            ),
            "dependency_schema_versions": _dependency_schema_versions(
                paths.workspace, dependencies
            ),
            "fk_restoration": fk_restoration,
        }
        if restoration_manifest is not None:
            relative = restoration_manifest.resolve().relative_to(
                paths.workspace.resolve()
            )
            state["fk_restoration"].update(
                path=relative.as_posix(), sha256=sha256_file(restoration_manifest)
            )
        _save(checked["backup"], state)
        return state


def promote_target_migration(
    paths: TargetMigrationPaths,
    *,
    deployment: TargetDeploymentBinding | None = None,
    source_profile: str | None = None,
    destination_profile: str | None = None,
    cutover_authority: str = "",
) -> TargetMigrationJournal:
    """Cut over a validated complete bundle, retaining originals for rollback."""
    _assert_canonical_cutover(deployment, cutover_authority)
    checked = paths.checked()
    validate_deployment_binding(checked, deployment)
    with _lock(paths.workspace):
        state = cast(
            "TargetMigrationJournal",
            orjson.loads((checked["backup"] / _JOURNAL_JSON).read_bytes()),
        )
        _assert_prepared_identity(checked, state, deployment)
        _assert_plan_profiles(state, source_profile, destination_profile)
        transition = resolve_target_migration_transition(
            str(state.get("source_profile", "V30")),
            str(state.get("destination_profile", "V31")),
        )
        restoration_manifest = _recorded_restoration(paths.workspace, state)
        _assert_recorded_versions(
            checked, state, restoration_manifest=restoration_manifest
        )
        _assert_recorded_contracts(checked, state, paths.workspace)
        _assert_recorded_candidates(checked, transition, state)
        verify_target_dependencies(paths.workspace, state["dependencies"])
        verify_target_dependencies(paths.workspace, state["dependency_backups"])
        _verify_prepared_bytes(checked, state)
        if _tree_hashes(checked["assay"]) != state["assay_hashes"]:
            raise ValueError("assay reference cohort changed since preparation")
        validate_target_candidate(
            checked,
            tuple(state["legacy_include_fields"]),
            workspace=paths.workspace,
            restoration_manifest=restoration_manifest,
        )
        from bioetl.infrastructure.storage.target_contract_transition import (
            assert_live_promotion_allowed,
        )
        from bioetl.infrastructure.storage.target_migration_validation import (
            _candidate_table_contract,
        )

        plan = dict(state)
        plan["table_contract"] = _candidate_table_contract(checked)
        assert_live_promotion_allowed(plan)
        state["phase"] = "promoting"
        _save(checked["backup"], state)
        try:
            for name in ("silver", "gold", "config"):
                state["moved"].append(name)
                _save(checked["backup"], state)
                checked[name].rename(checked["backup"] / ("original-" + name))
                checked["candidate_" + name].rename(checked[name])
                state["activated"].append(name)
                _save(checked["backup"], state)
            for name in ("silver", "gold", "config"):
                if _tree_hashes(checked[name]) != state["candidate_hashes"][name]:
                    raise ValueError(
                        "activated target bundle differs from validated bytes"
                    )
        except (OSError, ValueError):
            _restore_pairs(checked, state)
            raise
        state["phase"] = "promoted"
        _save(checked["backup"], state)
        return state


def _assert_prepared_identity(
    checked: dict[str, Path],
    state: TargetMigrationJournal,
    deployment: TargetDeploymentBinding | None,
) -> None:
    if state.get("schema_version") not in {1, 2}:
        raise ValueError("unsupported target migration journal")
    if state["phase"] != "prepared" or state["paths"] != {
        key: str(value) for key, value in checked.items()
    }:
        raise ValueError("migration is not the prepared occurrence")
    if state.get("deployment_binding") != (deployment.document() if deployment else {}):
        raise ValueError("deployment settings/config changed since preparation")


def _verify_prepared_bytes(
    checked: dict[str, Path], state: TargetMigrationJournal
) -> None:
    for name in ("silver", "gold", "config"):
        if _tree_hashes(checked[name]) != state["original_hashes"][name]:
            raise ValueError("canonical bytes changed since preparation")
        if (
            _tree_hashes(checked["candidate_" + name])
            != state["candidate_hashes"][name]
        ):
            raise ValueError("candidate bytes changed since validation")


def rollback_target_migration(
    paths: TargetMigrationPaths,
    *,
    source_profile: str | None = None,
    destination_profile: str | None = None,
) -> TargetMigrationJournal:
    """Restore paired physical tables plus original configuration, never clear."""
    checked = paths.checked()
    with _lock(paths.workspace):
        state = cast(
            "TargetMigrationJournal",
            orjson.loads((checked["backup"] / _JOURNAL_JSON).read_bytes()),
        )
        _assert_plan_profiles(state, source_profile, destination_profile)
        if state["phase"] not in {"promoted", "promoting"}:
            raise ValueError("migration has no activated bundle to restore")
        if state["paths"] != {k: str(v) for k, v in checked.items()}:
            raise ValueError("rollback paths differ from the prepared bundle")
        verify_target_dependencies(paths.workspace, state["dependency_backups"])
        _restore_dependencies(paths, state)
        for name in state["moved"]:
            original = checked["backup"] / ("original-" + name)
            if name in state.get("restored", []) or not original.exists():
                # A retry can follow a completed pair restoration, including a
                # crash before its journal save, or a saved move before rename.
                # Only the verified original bytes at the live path qualify.
                original = checked[name]
            if (
                not original.exists()
                or _tree_hashes(original) != state["original_hashes"][name]
            ):
                raise ValueError("original rollback bytes changed")
        _restore_pairs(checked, state)
        return state
