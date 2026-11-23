"""Prevent legacy backfill clear from destroying an enriched target table."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS

# Installed by the 3.2.0 contract (RF-006). An empty set means that contract
# is not present: seeing these names must not be inferred from enrich mode.
TARGET_CLASSIFICATION_V32_FIELDS: tuple[str, ...] = ()
_PROFILE_CONTRACT_VERSIONS = {"V30": "3.0.0", "V31": "3.1.0", "V32": "3.2.0"}


def classification_profile_name(fields: frozenset[str]) -> str:
    """Name one physical table contract from its classification columns."""
    required = frozenset(TARGET_CLASSIFICATION_FIELDS)
    present = required.intersection(fields)
    if present and present != required:
        raise ValueError("incomplete target classification schema; recovery required")
    v32 = frozenset(TARGET_CLASSIFICATION_V32_FIELDS)
    if v32:
        v32_present = v32.intersection(fields)
        if v32_present and v32_present != v32:
            raise ValueError(
                "incomplete target classification schema; recovery required"
            )
        if v32_present == v32:
            if present != required:
                raise ValueError(
                    "incomplete target classification schema; recovery required"
                )
            return "V32"
    return "V31" if present else "V30"


def contract_version_for_profile(profile: str) -> str:
    """Return the hash/table contract bound to one physical profile name."""
    try:
        return _PROFILE_CONTRACT_VERSIONS[profile]
    except KeyError as error:
        raise ValueError("unsupported target table profile") from error


def get_target_table_profile(
    *, silver_path: Path, gold_path: Path
) -> Literal["empty", "V30", "V31"]:
    """Inspect both destinations without constructing or mutating writers."""
    profiles = set()
    for path in (silver_path, gold_path):
        fields = _target_table_fields(path)
        if fields is None:
            continue
        named = classification_profile_name(fields)
        if named == "V32":
            raise ValueError(
                "V32 target contract requires an explicit migration profile; "
                "recovery required"
            )
        profiles.add(named)
    if len(profiles) > 1:
        raise ValueError("mixed V30/V31 target destinations; recovery required")
    if "V31" in profiles:
        return "V31"
    return "V30" if profiles else "empty"


def assert_target_table_compatibility(
    *,
    silver_path: Path,
    gold_path: Path,
    mode: str,
    destructive: bool = False,
) -> None:
    """Check both existing tables before the runner can clear either one.

    Empty candidate destinations are allowed. Enrich against V30 requires the
    explicit paired migration; off/shadow against V31 requires a real rollback.
    """
    if mode not in {"off", "shadow", "enrich"}:
        raise ValueError("unknown target classification mode")
    for path in (silver_path, gold_path):
        fields = _target_table_fields(path)
        if fields is not None:
            _assert_target_schema_compatibility(fields, mode, destructive)


def _target_table_fields(path: Path) -> frozenset[str] | None:
    """Return an existing Delta schema; empty candidate destinations are allowed."""
    from deltalake import DeltaTable

    if not path.exists() or not any(path.iterdir()):
        return None
    if not (path / "_delta_log").is_dir():
        raise ValueError("unrecognised target directory; refusing pre-backfill clear")
    return frozenset(field.name for field in DeltaTable(str(path)).schema().fields)


def _assert_target_schema_compatibility(
    fields: frozenset[str], mode: str, destructive: bool
) -> None:
    """Require one coherent contract and preserve existing enriched tables."""
    profile = classification_profile_name(fields)
    if profile == "V32":
        raise ValueError(
            "V32 target contract requires an explicit migration profile; "
            "recovery required"
        )
    present = profile == "V31"
    if mode == "enrich" and not present:
        raise ValueError("V30 target requires complete-cohort migration before enrich")
    if mode in {"off", "shadow"} and present:
        raise ValueError("V31 target requires physical rollback before legacy writes")
    if destructive and present:
        raise ValueError(
            "V31 target requires staged complete-cohort migration before destructive writes"
        )


__all__ = [
    "TARGET_CLASSIFICATION_FIELDS",
    "TARGET_CLASSIFICATION_V32_FIELDS",
    "assert_target_table_compatibility",
    "classification_profile_name",
    "contract_version_for_profile",
    "get_target_table_profile",
]
