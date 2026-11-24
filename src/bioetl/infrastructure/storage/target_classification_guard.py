"""Prevent legacy backfill clear from destroying an enriched target table."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from bioetl.domain.config.target_classification import (
    TARGET_CLASSIFICATION_DETAIL_FIELDS,
    TARGET_CLASSIFICATION_FIELDS,
    resolve_physical_table_contract,
)

_TargetProfile = Literal["empty", "V30", "V31", "V32"]
_INCOMPLETE_TARGET_SCHEMA = "incomplete target classification schema; recovery required"

TARGET_CLASSIFICATION_V32_FIELDS = TARGET_CLASSIFICATION_DETAIL_FIELDS
_PROFILE_CONTRACT_VERSIONS = {"V30": "3.0.0", "V31": "3.1.0", "V32": "3.2.0"}
_INCOMPLETE_CLASSIFICATION = (
    "incomplete target classification schema; recovery required"
)


def classification_profile_name(fields: frozenset[str]) -> Literal["V30", "V31", "V32"]:
    """Name one physical table contract from its classification columns."""
    required = frozenset(TARGET_CLASSIFICATION_FIELDS)
    present = required.intersection(fields)
    if present and present != required:
        raise ValueError(_INCOMPLETE_CLASSIFICATION)
    v32 = frozenset(TARGET_CLASSIFICATION_V32_FIELDS)
    if v32:
        v32_present = v32.intersection(fields)
        if v32_present and v32_present != v32:
            raise ValueError(_INCOMPLETE_CLASSIFICATION)
        if v32_present == v32:
            if present != required:
                raise ValueError(_INCOMPLETE_CLASSIFICATION)
            return "V32"
    return "V31" if present else "V30"


def contract_version_for_profile(profile: str) -> str:
    """Return the hash/table contract bound to one physical profile name."""
    try:
        return _PROFILE_CONTRACT_VERSIONS[profile]
    except KeyError as error:
        raise ValueError("unsupported target table profile") from error


def get_target_table_profile(*, silver_path: Path, gold_path: Path) -> _TargetProfile:
    """Inspect both destinations without constructing or mutating writers."""
    profiles: set[str] = set()
    for path in (silver_path, gold_path):
        fields = _target_table_fields(path)
        if fields is None:
            continue
        profiles.add(classification_profile_name(fields))
    if len(profiles) > 1:
        if profiles == {"V30", "V31"}:
            raise ValueError("mixed V30/V31 target destinations; recovery required")
        joined = "/".join(sorted(profiles))
        raise ValueError(f"mixed {joined} target destinations; recovery required")
    if not profiles:
        return "empty"
    found = next(iter(profiles))
    if found == "V30":
        return "V30"
    if found == "V31":
        return "V31"
    if found == "V32":
        return "V32"
    raise ValueError(_INCOMPLETE_TARGET_SCHEMA)


def assert_target_table_compatibility(
    *,
    silver_path: Path,
    gold_path: Path,
    mode: str,
    destructive: bool = False,
    table_contract: str | None = None,
) -> None:
    """Check both existing tables before the runner can clear either one.

    Empty candidate destinations are allowed. Enrich 3.1.0 against V30 requires
    the explicit paired migration. Enrich 3.2.0 does not migrate V30 or V31.
    off/shadow against an enriched table requires a real rollback.
    """
    contract = resolve_physical_table_contract(mode, table_contract)
    for path in (silver_path, gold_path):
        fields = _target_table_fields(path)
        if fields is not None:
            _assert_target_schema_compatibility(fields, contract, destructive)


def _target_table_fields(path: Path) -> frozenset[str] | None:
    """Return an existing Delta schema; empty candidate destinations are allowed."""
    from deltalake import DeltaTable

    if not path.exists() or not any(path.iterdir()):
        return None
    if not (path / "_delta_log").is_dir():
        raise ValueError("unrecognised target directory; refusing pre-backfill clear")
    return frozenset(field.name for field in DeltaTable(str(path)).schema().fields)


def _assert_target_schema_compatibility(
    fields: frozenset[str], table_contract: str, destructive: bool
) -> None:
    """Require one coherent contract and preserve existing enriched tables."""
    profile = classification_profile_name(fields)
    if table_contract == "3.0.0" and profile != "V30":
        raise ValueError(
            f"{profile} target requires physical rollback before legacy writes"
        )
    if table_contract == "3.1.0" and profile == "V30":
        raise ValueError("V30 target requires complete-cohort migration before enrich")
    if table_contract == "3.1.0" and profile == "V32":
        raise ValueError(
            "physical table contract 3.1.0 cannot write an existing V32 target table"
        )
    if table_contract == "3.2.0" and profile in {"V30", "V31"}:
        raise ValueError(
            "physical table contract 3.2.0 requires an empty destination or an existing "
            "V32 table; migration is a later task"
        )
    if destructive and profile == "V31":
        raise ValueError(
            "V31 target requires staged complete-cohort migration before destructive writes"
        )
    if destructive and profile == "V32":
        raise ValueError(
            "V32 target requires staged complete-cohort migration before destructive writes"
        )


__all__ = [
    "TARGET_CLASSIFICATION_FIELDS",
    "TARGET_CLASSIFICATION_V32_FIELDS",
    "assert_target_table_compatibility",
    "classification_profile_name",
    "contract_version_for_profile",
    "get_target_table_profile",
]
