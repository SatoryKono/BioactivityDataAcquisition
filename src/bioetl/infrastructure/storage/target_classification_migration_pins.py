"""Delta identity pins and the checks that block a drifted promotion."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import cast

import orjson
import pyarrow as pa
import yaml
from deltalake import DeltaTable

from bioetl.infrastructure.storage.target_classification_guard import (
    classification_profile_name,
    contract_version_for_profile,
)
from bioetl.infrastructure.storage.target_classification_migration_state import (
    _INVALID_TARGET_ID,
    TargetMigrationJournal,
    TargetMigrationTransition,
    _id_digest,
    require_rf009_fk_restoration,
)


def _delta_pin(path: Path, *, classify: bool) -> dict[str, object] | None:
    """Read one Delta identity, or None when the directory is not a table."""
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
    """Read current target ids without a native Delta scan.

    ``read_delta_records`` avoids the Windows ``to_pyarrow_table`` hang while
    the migration lock is held.
    """
    from bioetl.infrastructure.storage.delta.table_ops import read_delta_records

    names = {field.name for field in table.schema().fields}
    columns = ["target_id"]
    if "_is_current" in names:
        columns.append("_is_current")
    ids: set[str] = set()
    for row in read_delta_records(table, columns=columns):
        if row.get("_is_current", True) is not True:
            continue
        value = row.get("target_id")
        if value is None:
            continue
        if not isinstance(value, str) or not value:
            raise ValueError(_INVALID_TARGET_ID)
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
    *,
    restored_gold: Path | None = None,
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
    gold = pins["gold"]
    if restored_gold is not None:
        candidate = _delta_pin(restored_gold, classify=False)
        if candidate is None:
            raise ValueError("restored target candidate is unreadable")
        gold = candidate
    gold_ids = gold["target_ids"]
    if not isinstance(assay_ids, set) or not isinstance(gold_ids, set):
        raise ValueError(_INVALID_TARGET_ID)
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
    checked: dict[str, Path],
    state: TargetMigrationJournal,
    *,
    restoration_manifest: Path | None = None,
) -> None:
    recorded = state.get("table_versions") or {}
    if not recorded:
        return
    current = _source_pins(checked)
    if current is None:
        raise ValueError("recorded source versions are no longer readable")
    live = _public_pins(current)
    for name, previous in recorded.items():
        _assert_one_pin(name, live[name], previous)
    if (state.get("fk_restoration") or {}).get("status") == "closed":
        _fk_restoration(
            current,
            restored_gold=checked["candidate_gold"] if restoration_manifest else None,
        )


def _assert_one_pin(
    name: str, observed: Mapping[str, object], previous: object
) -> None:
    if not isinstance(previous, dict):
        raise ValueError("source table version changed since preparation")
    if (
        observed["version"] != previous["version"]
        or observed["table_id"] != previous["table_id"]
    ):
        raise ValueError("source table version changed since preparation")
    if observed["profile"] != previous["profile"]:
        raise ValueError("source table profile changed since preparation")
    if observed["target_id_sha256"] == previous["target_id_sha256"]:
        return
    if name == "assay":
        raise ValueError("assay reference cohort changed since preparation")
    if name == "gold":
        raise ValueError("baseline target cohort changed since preparation")
    raise ValueError("source cohort changed since preparation")


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
    raw = _optional_journal(state)
    recorded = raw.get("dependency_schema_versions")
    if not isinstance(recorded, dict):
        if raw.get("schema_version") == 1:
            return
        raise ValueError("migration journal is missing dependency schema versions")
    versions = {
        str(key): value
        for key, value in recorded.items()
        if isinstance(key, str) and type(value) is int
    }
    if len(versions) != len(recorded):
        raise ValueError("dependency schema version changed since preparation")
    if _dependency_schema_versions(workspace, versions) != versions:
        raise ValueError("dependency schema version changed since preparation")


def _optional_journal(state: TargetMigrationJournal) -> dict[str, object]:
    """Read a loaded journal as a mapping so schema 1 may omit schema 2 keys."""
    return cast("dict[str, object]", state)


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
