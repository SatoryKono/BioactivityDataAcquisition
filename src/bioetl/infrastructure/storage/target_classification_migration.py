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
from typing import TYPE_CHECKING, NotRequired, TypedDict, cast

if TYPE_CHECKING:
    from deltalake import DeltaTable

import orjson
import pyarrow as pa
import yaml

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

from bioetl.infrastructure.control_plane.evidence_location_publish import (
    publish_bytes_if_absent,
)
from bioetl.infrastructure.storage.target_classification_guard import (
    classification_profile_name,
    contract_version_for_profile,
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
from iuphar_target_class.stage0.io import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)

_JOURNAL_JSON = "journal.json"
_CANONICAL_CUTOVER = "RF-013"
# Physical transitions the driver can execute. 3.2.0 stays declared and
# refused until its field contract is installed and this set is updated.
_EXECUTABLE_TRANSITIONS = frozenset({("V30", "V31")})
_BLOCKED_TRANSITIONS = {
    ("V30", "V32"): (
        "destination contract 3.2.0 is not installed; "
        "refusing to treat it as a V31 promotion"
    ),
    ("V31", "V32"): (
        "destination contract 3.2.0 is not installed; "
        "refusing to treat it as a V31 promotion"
    ),
}


@dataclass(frozen=True, slots=True)
class TargetMigrationTransition:
    """One explicit source/destination pair, never an implicit enrich upgrade."""

    source_profile: str
    destination_profile: str
    source_contract_version: str
    destination_contract_version: str


def resolve_target_migration_transition(
    source_profile: str, destination_profile: str
) -> TargetMigrationTransition:
    """Accept only catalogued executable transitions; reject every other pair."""
    if (source_profile, destination_profile) in _BLOCKED_TRANSITIONS:
        raise ValueError(_BLOCKED_TRANSITIONS[(source_profile, destination_profile)])
    if (source_profile, destination_profile) not in _EXECUTABLE_TRANSITIONS:
        raise ValueError(
            "unsupported target migration transition "
            f"{source_profile} -> {destination_profile}"
        )
    return TargetMigrationTransition(
        source_profile,
        destination_profile,
        contract_version_for_profile(source_profile),
        contract_version_for_profile(destination_profile),
    )


def require_rf009_fk_restoration(
    assay_target_ids: set[str], gold_target_ids: set[str]
) -> dict[str, object]:
    """Block promotion until every current assay target exists in Gold."""
    missing = sorted(assay_target_ids - gold_target_ids)
    if missing:
        raise ValueError(
            "assay/target FK restoration RF-009 is required before promotion "
            f"({len(missing)} missing target ids)"
        )
    return {
        "dependency": "RF-009",
        "artifact": "bioetl_target_fk_repair_candidate",
        "status": "closed",
        "missing_target_ids": [],
        "assay_target_id_sha256": _id_digest(assay_target_ids),
        "gold_target_id_sha256": _id_digest(gold_target_ids),
    }


def _id_digest(ids: set[str]) -> str:
    return sha256_bytes("\n".join(sorted(ids)).encode())


def _assert_canonical_cutover(
    deployment: TargetDeploymentBinding | None, cutover_authority: str
) -> None:
    """Keep canonical deployment promotion behind RF-013."""
    if (
        deployment is not None
        and deployment.role == "deployment"
        and cutover_authority != _CANONICAL_CUTOVER
    ):
        raise ValueError("canonical table promotion is reserved for RF-013")


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
    source_profile: str
    destination_profile: str
    source_contract_version: str
    destination_contract_version: str
    table_versions: dict[str, dict[str, object]]
    candidate_profiles: dict[str, str]
    config_contract_version: str
    destination_config_contract_version: str
    dependency_schema_versions: dict[str, int]
    fk_restoration: dict[str, object]


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


def _delta_pin(path: Path, *, classify: bool) -> dict[str, object] | None:
    """Read one Delta identity, or None when the directory is not a table."""
    from deltalake import DeltaTable
    from deltalake.exceptions import DeltaError

    try:
        table = DeltaTable(str(path))
        fields = frozenset(field.name for field in table.schema().fields)
    except (OSError, DeltaError, RuntimeError, pa.ArrowInvalid):
        return None
    profile = classification_profile_name(fields) if classify else ""
    target_ids: set[str] = set()
    if "target_id" in fields:
        try:
            target_ids = _target_ids(table)
        except (OSError, DeltaError, RuntimeError, pa.ArrowInvalid):
            return None
    return {
        "version": table.version(),
        "table_id": table.metadata().id,
        "profile": profile,
        "contract_version": contract_version_for_profile(profile) if profile else "",
        "target_id_sha256": _id_digest(target_ids) if "target_id" in fields else "",
        "target_ids": target_ids,
    }


def _target_ids(table: DeltaTable) -> set[str]:
    names = {field.name for field in table.schema().fields}
    columns = ["target_id"]
    if "_is_current" in names:
        columns.append("_is_current")
    ids: set[str] = set()
    for row in table.to_pyarrow_table(columns=columns).to_pylist():
        if row.get("_is_current", True) is not True:
            continue
        value = row.get("target_id")
        if value is None:
            continue
        if not isinstance(value, str) or not value:
            raise ValueError(
                "assay/target FK restoration RF-009 found an invalid target id"
            )
        ids.add(value)
    return ids


def _source_pins(checked: dict[str, Path]) -> dict[str, dict[str, object]] | None:
    pins: dict[str, dict[str, object]] = {}
    for name in ("silver", "gold", "assay"):
        pin = _delta_pin(checked[name], classify=name != "assay")
        if pin is None:
            return None
        pins[name] = pin
    if pins["silver"]["profile"] != pins["gold"]["profile"]:
        raise ValueError("mixed V30/V31 target destinations; recovery required")
    return pins


def _public_pins(
    pins: dict[str, dict[str, object]] | None,
) -> dict[str, dict[str, object]]:
    if pins is None:
        return {}
    return {
        name: {key: value for key, value in pin.items() if key != "target_ids"}
        for name, pin in pins.items()
    }


def _assert_source_profiles(
    pins: dict[str, dict[str, object]] | None, transition: TargetMigrationTransition
) -> None:
    if pins is None:
        return
    for name in ("silver", "gold"):
        observed = pins[name]["profile"]
        if observed != transition.source_profile:
            raise ValueError(
                f"source table profile is {observed}, "
                f"plan source_profile is {transition.source_profile}"
            )


def _fk_restoration(
    pins: dict[str, dict[str, object]] | None,
) -> dict[str, object]:
    if pins is None:
        return {
            "dependency": "RF-009",
            "artifact": "bioetl_target_fk_repair_candidate",
            "status": "unreadable",
            "missing_target_ids": [],
            "assay_target_id_sha256": "",
            "gold_target_id_sha256": "",
        }
    assay_ids = pins["assay"]["target_ids"]
    gold_ids = pins["gold"]["target_ids"]
    if not isinstance(assay_ids, set) or not isinstance(gold_ids, set):
        raise ValueError(
            "assay/target FK restoration RF-009 found an invalid target id"
        )
    return require_rf009_fk_restoration(assay_ids, gold_ids)


def _candidate_profiles(
    checked: dict[str, Path], transition: TargetMigrationTransition
) -> dict[str, str]:
    pins = [
        _delta_pin(checked[name], classify=True)
        for name in ("candidate_silver", "candidate_gold")
    ]
    if any(pin is None for pin in pins):
        if any(pin is not None for pin in pins):
            raise ValueError("candidate table version is not readable")
        return {}
    profiles: dict[str, str] = {}
    for name, pin in zip(("silver", "gold"), pins, strict=True):
        if pin is None:
            continue
        observed = str(pin["profile"])
        if observed != transition.destination_profile:
            raise ValueError(
                f"candidate table profile is {observed}, "
                f"plan destination_profile is {transition.destination_profile}"
            )
        profiles[name] = observed
    return profiles


def _active_contract_version(path: Path) -> str:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        return ""
    contracts = document.get("contracts")
    if not isinstance(contracts, dict):
        return ""
    version = contracts.get("active_version")
    return version if isinstance(version, str) else ""


def _dependency_schema_versions(
    workspace: Path, dependencies: Mapping[str, object]
) -> dict[str, int]:
    versions: dict[str, int] = {}
    root = workspace.resolve()
    for relative in dependencies:
        try:
            document = orjson.loads((root / relative).read_bytes())
        except (OSError, orjson.JSONDecodeError):
            continue
        if isinstance(document, dict) and type(document.get("schema_version")) is int:
            versions[relative] = int(document["schema_version"])
    return versions


def _assert_plan_profiles(
    state: TargetMigrationJournal,
    source_profile: str | None,
    destination_profile: str | None,
) -> None:
    if source_profile is None and destination_profile is None:
        return
    if source_profile is None or destination_profile is None:
        raise ValueError("plan profiles must name both source and destination")
    recorded = (
        state.get("source_profile", "V30"),
        state.get("destination_profile", "V31"),
    )
    if (source_profile, destination_profile) != recorded:
        raise ValueError("plan profiles differ from the prepared migration")


def _assert_recorded_versions(
    checked: dict[str, Path], state: TargetMigrationJournal
) -> None:
    recorded = state.get("table_versions") or {}
    if not recorded:
        return
    current = _source_pins(checked)
    if current is None:
        raise ValueError("recorded source versions are no longer readable")
    live = _public_pins(current)
    for name, previous in recorded.items():
        observed = live[name]
        if (
            observed["version"] != previous["version"]
            or observed["table_id"] != previous["table_id"]
        ):
            raise ValueError("source table version changed since preparation")
        if observed["profile"] != previous["profile"]:
            raise ValueError("source table profile changed since preparation")
        if observed["target_id_sha256"] != previous["target_id_sha256"]:
            if name == "assay":
                raise ValueError("assay reference cohort changed since preparation")
            if name == "gold":
                raise ValueError("baseline target cohort changed since preparation")
            raise ValueError("source cohort changed since preparation")
    restoration = state.get("fk_restoration") or {}
    if restoration.get("status") == "closed":
        assay_ids = current["assay"]["target_ids"]
        gold_ids = current["gold"]["target_ids"]
        if not isinstance(assay_ids, set) or not isinstance(gold_ids, set):
            raise ValueError(
                "assay/target FK restoration RF-009 found an invalid target id"
            )
        require_rf009_fk_restoration(assay_ids, gold_ids)


def _assert_recorded_contracts(
    checked: dict[str, Path], state: TargetMigrationJournal, workspace: Path
) -> None:
    if (
        "config_contract_version" in state
        and _active_contract_version(checked["config"])
        != state["config_contract_version"]
    ):
        raise ValueError("config contract version changed since preparation")
    if (
        "destination_config_contract_version" in state
        and _active_contract_version(checked["candidate_config"])
        != state["destination_config_contract_version"]
    ):
        raise ValueError("candidate config contract version changed since preparation")
    recorded = state["dependency_schema_versions"]
    if _dependency_schema_versions(workspace, recorded) != recorded:
        raise ValueError("dependency schema version changed since preparation")


def _assert_recorded_candidates(
    checked: dict[str, Path],
    transition: TargetMigrationTransition,
    state: TargetMigrationJournal,
) -> None:
    recorded = state.get("candidate_profiles") or {}
    if not recorded:
        return
    if _candidate_profiles(checked, transition) != recorded:
        raise ValueError("candidate table profile changed since preparation")


def prepare_target_migration(
    paths: TargetMigrationPaths,
    *,
    legacy_include_fields: tuple[str, ...],
    deployment: TargetDeploymentBinding | None = None,
    source_profile: str = "V30",
    destination_profile: str = "V31",
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
        fk_restoration = _fk_restoration(pins)
        candidate_profiles = _candidate_profiles(checked, transition)
        validation = validate_target_candidate(
            checked, legacy_include_fields, workspace=paths.workspace
        )
        dependencies = collect_target_dependencies(
            workspace=paths.workspace,
            configs=(checked["config"], checked["candidate_config"]),
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
            "destination_config_contract_version": _active_contract_version(
                checked["candidate_config"]
            ),
            "dependency_schema_versions": _dependency_schema_versions(
                paths.workspace, dependencies
            ),
            "fk_restoration": fk_restoration,
        }
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
        _assert_recorded_versions(checked, state)
        _assert_recorded_contracts(checked, state, paths.workspace)
        _assert_recorded_candidates(checked, transition, state)
        verify_target_dependencies(paths.workspace, state["dependencies"])
        verify_target_dependencies(paths.workspace, state["dependency_backups"])
        _verify_prepared_bytes(checked, state)
        validate_target_candidate(
            checked,
            tuple(state["legacy_include_fields"]),
            workspace=paths.workspace,
        )
        if _tree_hashes(checked["assay"]) != state["assay_hashes"]:
            raise ValueError("assay reference cohort changed since preparation")
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
