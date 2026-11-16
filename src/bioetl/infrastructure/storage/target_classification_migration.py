"""Journaled, paired target-table promotion; no Delta-version-only rollback.

The caller must hold the deployment maintenance window across all old writers.
This module additionally refuses active managed writers and preserves physical
tables/configuration. It never promotes an unvalidated limit-1000 subset.
"""

from __future__ import annotations

import json
import os
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from bioetl.infrastructure.storage.target_migration_validation import (
    validate_target_candidate,
)
from iuphar_target_class.stage0.io import canonical_json_bytes, sha256_file


@dataclass(frozen=True, slots=True)
class TargetMigrationPaths:
    """Explicit approved workspace and disjoint physical table/config paths."""

    workspace: Path
    silver: Path
    gold: Path
    config: Path
    candidate_silver: Path
    candidate_gold: Path
    candidate_config: Path
    backup: Path

    def checked(self) -> dict[str, Path]:
        root = self.workspace.resolve(strict=True)
        paths = {name: getattr(self, name).absolute() for name in (
            "silver", "gold", "config", "candidate_silver", "candidate_gold",
            "candidate_config", "backup")}
        for path in paths.values():
            _check_path(path, root)
        for name, path in paths.items():
            if any(path == other or path.is_relative_to(other)
                   for key, other in paths.items() if key != name):
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
    if path.name == ".env" or path.name.startswith(".env.") or path.name.endswith(".env"):
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
    path = root / ".bioetl-target-migration.lock"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    try:
        yield
    finally:
        path.unlink()


def _save(backup: Path, state: dict) -> None:
    temporary = backup / "journal.tmp"
    temporary.write_bytes(canonical_json_bytes(state))
    temporary.replace(backup / "journal.json")


def _restore_pairs(paths: dict[str, Path], state: dict) -> None:
    """Move original directories back; preserve every displaced candidate."""
    backup = paths["backup"]
    for name in reversed(state["moved"]):
        live = paths[name]
        if live.exists():
            live.rename(backup / ("failed-" + name))
        (backup / ("original-" + name)).rename(live)
    state["phase"] = "rolled_back"
    _save(backup, state)


def prepare_target_migration(
    paths: TargetMigrationPaths, *, legacy_include_fields: tuple[str, ...],
) -> dict:
    """Validate complete cohorts and copy the entire recoverable old bundle."""
    checked = paths.checked()
    with _lock(paths.workspace):
        validation = validate_target_candidate(checked, legacy_include_fields)
        checked["backup"].mkdir(parents=True, exist_ok=False)
        before = {name: _tree_hashes(checked[name]) for name in ("silver", "gold", "config")}
        for name in before:
            source = checked[name]
            target = checked["backup"] / ("copy-" + name)
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copyfile(source, target)
            if _tree_hashes(target) != before[name]:
                raise ValueError("physical migration backup hash mismatch")
        if any(_tree_hashes(checked[name]) != hashes for name, hashes in before.items()):
            raise ValueError("canonical target changed during backup; refuse promotion")
        state = {"artifact": "bioetl_target_migration", "schema_version": 1,
                 "phase": "prepared", "paths": {k: str(v) for k, v in checked.items()},
                 "original_hashes": before, "candidate_hashes": {
                     name: _tree_hashes(checked["candidate_" + name])
                     for name in ("silver", "gold", "config")},
                 "validation": validation, "moved": [], "activated": []}
        _save(checked["backup"], state)
        return state


def promote_target_migration(paths: TargetMigrationPaths) -> dict:
    """Cut over a validated complete bundle, retaining originals for rollback."""
    checked = paths.checked()
    with _lock(paths.workspace):
        state = json.loads((checked["backup"] / "journal.json").read_bytes())
        if state["phase"] != "prepared" or state["paths"] != {k: str(v) for k, v in checked.items()}:
            raise ValueError("migration is not the prepared occurrence")
        for name in ("silver", "gold", "config"):
            if _tree_hashes(checked[name]) != state["original_hashes"][name]:
                raise ValueError("canonical bytes changed since preparation")
            if _tree_hashes(checked["candidate_" + name]) != state["candidate_hashes"][name]:
                raise ValueError("candidate bytes changed since validation")
        state["phase"] = "promoting"
        _save(checked["backup"], state)
        try:
            for name in ("silver", "gold", "config"):
                checked[name].rename(checked["backup"] / ("original-" + name))
                state["moved"].append(name)
                _save(checked["backup"], state)
                checked["candidate_" + name].rename(checked[name])
                state["activated"].append(name)
                _save(checked["backup"], state)
        except OSError:
            _restore_pairs(checked, state)
            raise
        state["phase"] = "promoted"
        _save(checked["backup"], state)
        return state


def rollback_target_migration(paths: TargetMigrationPaths) -> dict:
    """Restore paired physical tables plus original configuration, never clear."""
    checked = paths.checked()
    with _lock(paths.workspace):
        state = json.loads((checked["backup"] / "journal.json").read_bytes())
        if state["phase"] not in {"promoted", "promoting"}:
            raise ValueError("migration has no activated bundle to restore")
        if state["paths"] != {k: str(v) for k, v in checked.items()}:
            raise ValueError("rollback paths differ from the prepared bundle")
        for name in state["moved"]:
            if _tree_hashes(checked["backup"] / ("original-" + name)) != state["original_hashes"][name]:
                raise ValueError("original rollback bytes changed")
        _restore_pairs(checked, state)
        return state
