"""Journaled, paired target-table promotion; no Delta-version-only rollback.

The caller must hold the deployment maintenance window across all old writers.
This module additionally refuses active managed writers and preserves physical
tables/configuration. It never promotes an unvalidated limit-1000 subset.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import NotRequired, TypedDict, cast

import orjson

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

from bioetl.infrastructure.control_plane.evidence_location_publish import (
    publish_bytes_if_absent,
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
from iuphar_target_class.stage0.io import canonical_json_bytes, sha256_file

_JOURNAL_JSON = "journal.json"


class TargetMigrationJournal(TypedDict):
    """Persisted occurrence state used by paired promotion and recovery."""

    artifact: str
    schema_version: int
    phase: str
    paths: dict[str, str]
    original_hashes: dict[str, dict[str, str]]
    candidate_hashes: dict[str, dict[str, str]]
    validation: dict[str, object]
    moved: list[str]
    activated: list[str]
    legacy_include_fields: list[str]
    assay_hashes: dict[str, str]
    restored: NotRequired[list[str]]
    deployment_binding: dict[str, str]
    dependencies: dict[str, str]
    dependency_backups: dict[str, str]
    restored_dependencies: NotRequired[list[str]]
    fk_restoration: NotRequired[dict[str, str]]


@dataclass(frozen=True, slots=True)
class TargetMigrationPaths:
    """Explicit approved workspace and disjoint physical table/config paths."""

    workspace: Path
    silver: Path
    gold: Path
    assay: Path
    config: Path
    candidate_silver: Path
    candidate_gold: Path
    candidate_config: Path
    backup: Path

    def checked(self) -> dict[str, Path]:
        root = self.workspace.resolve(strict=True)
        paths = {
            name: getattr(self, name).absolute()
            for name in (
                "silver",
                "gold",
                "assay",
                "config",
                "candidate_silver",
                "candidate_gold",
                "candidate_config",
                "backup",
            )
        }
        for path in paths.values():
            _check_path(path, root)
        # Canonicalize only after inspecting the caller's path and ancestors.
        # Otherwise lexical '..' aliases can hide a backup nested in a table.
        paths = {name: path.resolve() for name, path in paths.items()}
        for name, path in paths.items():
            if any(
                path == other or path.is_relative_to(other)
                for key, other in paths.items()
                if key != name
            ):
                raise ValueError("migration paths must be disjoint")
        return paths


def _check_path(path: Path, root: Path) -> None:
    if path.resolve() == root or not path.resolve().is_relative_to(root):
        raise ValueError("migration path escapes the approved workspace")
    for part in (path, *path.parents):
        if part == root.parent:
            break
        if part.is_symlink() or part.is_junction():
            raise ValueError("migration refuses symlink/junction paths")
    if (
        path.name == ".env"
        or path.name.startswith(".env.")
        or path.name.endswith(".env")
    ):
        raise ValueError("environment files cannot enter a migration bundle")


def _tree_hashes(path: Path) -> dict[str, str]:
    if path.is_file():
        return {".": sha256_file(path)}
    result = {}
    for item in sorted(path.rglob("*")):
        _check_path(item, path.resolve())
        if item.is_file():
            result[item.relative_to(path).as_posix()] = sha256_file(item)
    return result


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


def _save(backup: Path, state: Mapping[str, object]) -> None:
    temporary = backup / "journal.tmp"
    temporary.write_bytes(canonical_json_bytes(state))
    temporary.replace(backup / _JOURNAL_JSON)


def _restore_pairs(paths: dict[str, Path], state: TargetMigrationJournal) -> None:
    """Move original directories back; preserve every displaced candidate."""
    backup = paths["backup"]
    restored = state.setdefault("restored", [])
    for name in reversed(state["moved"]):
        if name in restored:
            continue
        live = paths[name]
        original = backup / ("original-" + name)
        if not original.exists():
            if (
                not live.exists()
                or _tree_hashes(live) != state["original_hashes"][name]
            ):
                raise ValueError("cannot identify original tables during recovery")
        else:
            if live.exists():
                live.rename(backup / ("failed-" + name))
            original.rename(live)
        restored.append(name)
        _save(backup, state)
    state["phase"] = "rolled_back"
    _save(backup, state)


def _recorded_restoration(
    workspace: Path, state: TargetMigrationJournal
) -> Path | None:
    recorded = state.get("fk_restoration")
    if not isinstance(recorded, dict):
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
    restoration_manifest: Path | None = None,
) -> TargetMigrationJournal:
    """Validate complete cohorts and copy the entire recoverable old bundle."""
    checked = paths.checked()
    validate_deployment_binding(checked, deployment)
    with _lock(paths.workspace):
        validation = validate_target_candidate(
            checked,
            legacy_include_fields,
            workspace=paths.workspace,
            restoration_manifest=restoration_manifest,
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
            "schema_version": 1,
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
        }
        if restoration_manifest is not None:
            relative = restoration_manifest.resolve().relative_to(
                paths.workspace.resolve()
            )
            state["fk_restoration"] = {
                "path": relative.as_posix(),
                "sha256": sha256_file(restoration_manifest),
            }
        _save(checked["backup"], state)
        return state


def promote_target_migration(
    paths: TargetMigrationPaths, *, deployment: TargetDeploymentBinding | None = None
) -> TargetMigrationJournal:
    """Cut over a validated complete bundle, retaining originals for rollback."""
    checked = paths.checked()
    validate_deployment_binding(checked, deployment)
    with _lock(paths.workspace):
        state = cast(
            "TargetMigrationJournal",
            orjson.loads((checked["backup"] / _JOURNAL_JSON).read_bytes()),
        )
        _assert_prepared_identity(checked, state, deployment)
        verify_target_dependencies(paths.workspace, state["dependencies"])
        verify_target_dependencies(paths.workspace, state["dependency_backups"])
        _verify_prepared_bytes(checked, state)
        if _tree_hashes(checked["assay"]) != state["assay_hashes"]:
            raise ValueError("assay reference cohort changed since preparation")
        validate_target_candidate(
            checked,
            tuple(state["legacy_include_fields"]),
            workspace=paths.workspace,
            restoration_manifest=_recorded_restoration(paths.workspace, state),
        )
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


def rollback_target_migration(paths: TargetMigrationPaths) -> TargetMigrationJournal:
    """Restore paired physical tables plus original configuration, never clear."""
    checked = paths.checked()
    with _lock(paths.workspace):
        state = cast(
            "TargetMigrationJournal",
            orjson.loads((checked["backup"] / _JOURNAL_JSON).read_bytes()),
        )
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


def _restore_dependencies(
    paths: TargetMigrationPaths, state: TargetMigrationJournal
) -> None:
    """Restore pinned dependency bytes before reactivating their configuration."""
    restored = state.setdefault("restored_dependencies", [])
    workspace = paths.workspace.resolve(strict=True)
    for relative, digest in state["dependencies"].items():
        destination = workspace / relative
        if destination == paths.config.resolve():
            # The promoted config legitimately differs; its verified original
            # is restored by the journaled pair operation below.
            continue
        source = paths.backup / "dependencies" / relative
        if (
            state["dependency_backups"].get(source.relative_to(workspace).as_posix())
            != digest
        ):
            raise ValueError("dependency backup identity differs from the original")
        verify_target_dependencies(
            workspace, {source.relative_to(workspace).as_posix(): digest}
        )
        if destination.exists():
            verify_target_dependencies(workspace, {relative: digest})
        else:
            # Exclusive publication never overwrites a concurrent replacement.
            if not publish_bytes_if_absent(
                destination, source.read_bytes(), trusted_base=workspace
            ):
                verify_target_dependencies(workspace, {relative: digest})
        if relative not in restored:
            restored.append(relative)
            _save(paths.backup, state)
