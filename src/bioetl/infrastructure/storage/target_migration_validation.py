"""Full-cohort checks and managed-writer quiescence for target promotion."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import psutil
import yaml

from bioetl.domain.behavior.identity_service import EntityIdentityGenerator
from bioetl.infrastructure.adapters.iuphar.snapshot_loader import load_profile

_META = frozenset({"entity_id", "content_hash"})


def assert_no_managed_writers() -> None:
    """Refuse promotion while known pipeline/workflow/campaign writers live."""
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        if process.info["pid"] == os.getpid():
            continue
        command = " ".join(process.info.get("cmdline") or ())
        if any(
            marker in command
            for marker in (
                "bioetl workflow run",
                "bioetl run chembl_target",
                "workflow-campaigns" + os.sep,
                "workflow-campaigns/",
                "workflow-campaigns\\",
            )
        ):
            raise RuntimeError(
                f"managed writer is still active: PID {process.info['pid']}"
            )


def _business(row: Mapping[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in row.items()
        if not key.startswith("_") and key not in _META
    }


def _hash_input(row: Mapping[str, object]) -> dict[str, object]:
    record = _business(row)
    if "description" in record:
        record["target_description"] = record.pop("description")
    return record


def _by_id(rows: Sequence[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    indexed: dict[str, Mapping[str, object]] = {}
    for row in rows:
        identity = row.get("target_id")
        if not isinstance(identity, str) or not identity or identity in indexed:
            raise ValueError("target migration needs unique, nonempty target IDs")
        indexed[identity] = row
    if not indexed:
        raise ValueError("empty target cohort cannot replace a canonical table")
    return indexed


def compare_target_rows(
    original: Sequence[Mapping[str, object]],
    candidate: Sequence[Mapping[str, object]],
    legacy_include_fields: tuple[str, ...],
) -> dict[str, int]:
    """Reject subsets, changed old fields, duplicates or legacy-hash drift."""
    if not legacy_include_fields:
        raise ValueError("explicit frozen legacy hash include-policy required")
    old, new = _by_id(original), _by_id(candidate)
    if old.keys() != new.keys():
        raise ValueError("candidate target IDs differ from the full canonical cohort")
    identity = EntityIdentityGenerator(
        content_hash_include_fields=set(legacy_include_fields)
    )
    for key, previous in old.items():
        current = new[key]
        for field, value in _business(previous).items():
            if field not in current or current[field] != value:
                raise ValueError(
                    f"candidate changed legacy business field: {key}/{field}"
                )
        old_hash = identity.compute_content_hash("chembl", _hash_input(previous))
        new_legacy_hash = identity.compute_content_hash("chembl", _hash_input(current))
        if old_hash != previous.get("content_hash") or old_hash != new_legacy_hash:
            raise ValueError("legacy 3.0 hash equivalence failed")
    return {"rows": len(old), "legacy_hashes_verified": len(old)}


def _read_delta(path: Path) -> list[dict[str, object]]:
    from deltalake import DeltaTable

    # Arrow's JSON-compatible row boundary is untyped in the installed stubs.
    return cast(
        "list[dict[str, object]]",
        DeltaTable(str(path)).to_pyarrow_table().to_pylist(),
    )


def validate_target_candidate(
    paths: dict[str, Path],
    legacy_include_fields: tuple[str, ...],
) -> dict[str, object]:
    """Validate admission, strict candidate schemas and both entire cohorts."""
    from bioetl.domain.contracts.gold.chembl_target_classification import (
        ChEMBLTargetGoldSchemaV31,
    )
    from bioetl.domain.schemas.chembl.target import TargetSchemaV31

    config = yaml.safe_load(paths["candidate_config"].read_text(encoding="utf-8"))
    classification = config["pipeline"]["target_classification"]
    if classification["mode"] != "enrich":
        raise ValueError("candidate configuration must select admitted enrich")
    profile_path = Path(classification["snapshot_manifest"])
    if not profile_path.is_absolute():
        # Entity configuration lives at configs/entities/chembl/target.yaml.
        root = paths["config"].resolve().parents[3]
        profile_path = root / profile_path
    profile = load_profile(
        profile_path,
        classification["snapshot_manifest_sha256"],
        require_acceptance=True,
    )
    result: dict[str, object] = {}
    cohorts = {}
    for name, schema in (
        ("silver", TargetSchemaV31),
        ("gold", ChEMBLTargetGoldSchemaV31),
    ):
        old = _read_delta(paths[name])
        new = _read_delta(paths["candidate_" + name])
        import pandas as pd

        schema.validate(pd.DataFrame(new), lazy=True)
        if any(
            row.get("target_class_profile_sha256") != profile.profile_sha256
            for row in new
        ):
            raise ValueError("candidate rows belong to another IUPHAR profile")
        result[name] = compare_target_rows(old, new, legacy_include_fields)
        cohorts[name] = {row["target_id"] for row in new}
    if cohorts["silver"] != cohorts["gold"]:
        raise ValueError("Silver/Gold target cohorts differ")
    assay_targets = {
        row["target_id"]
        for row in _read_delta(paths["assay"])
        if row.get("target_id") is not None
    }
    if assay_targets != cohorts["gold"]:
        raise ValueError("baseline assay/target foreign-key closure failed")
    result["fk_closure"] = "PASS"
    result["profile_sha256"] = profile.profile_sha256
    return result
