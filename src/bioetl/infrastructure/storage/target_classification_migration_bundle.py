"""Workspace path guards, physical copies and journaled pair restoration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from bioetl.infrastructure.control_plane.evidence_location_publish import (
    publish_bytes_if_absent,
)
from bioetl.infrastructure.storage.target_classification_migration_state import (
    TargetMigrationJournal,
)
from bioetl.infrastructure.storage.target_migration_dependencies import (
    verify_target_dependencies,
)
from iuphar_target_class.stage0.io import canonical_json_bytes, sha256_file

_JOURNAL_JSON = "journal.json"


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
